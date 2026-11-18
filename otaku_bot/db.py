"""طبقة SQLite. اتصال واحد، والعمليات سريعة فلا حاجة لـ async هنا."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .quiz import Answer, Question
from .timeutil import day_start

SCHEMA = """
CREATE TABLE IF NOT EXISTS questions(
  id INTEGER PRIMARY KEY,
  q TEXT NOT NULL,
  options TEXT NOT NULL,
  answer INTEGER NOT NULL,
  category TEXT NOT NULL,
  base_difficulty REAL NOT NULL,
  asked INTEGER NOT NULL DEFAULT 0,
  correct INTEGER NOT NULL DEFAULT 0,
  flagged INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS users(
  tg_id INTEGER PRIMARY KEY,
  name TEXT,
  best_score REAL NOT NULL DEFAULT 0,
  tests_taken INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_id INTEGER NOT NULL,
  started_at REAL NOT NULL,
  finished_at REAL,
  score REAL,
  state TEXT NOT NULL DEFAULT 'active',   -- active | finished | abandoned
  current_pos INTEGER NOT NULL DEFAULT 0,
  message_id INTEGER
);
CREATE TABLE IF NOT EXISTS session_questions(
  session_id INTEGER NOT NULL,
  pos INTEGER NOT NULL,
  question_id INTEGER NOT NULL,
  level INTEGER NOT NULL,
  option_order TEXT NOT NULL,
  correct_pos INTEGER NOT NULL,
  user_answer INTEGER,                    -- NULL لم يُجَب، -1 انتهى الوقت، -2 تُخطّي (صورة معطوبة)
  is_correct INTEGER,
  sent_at REAL,
  time_ms INTEGER,
  PRIMARY KEY(session_id, pos)
);
CREATE TABLE IF NOT EXISTS user_seen(
  tg_id INTEGER NOT NULL, question_id INTEGER NOT NULL, seen_at REAL NOT NULL,
  PRIMARY KEY(tg_id, question_id)
);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS admins(tg_id INTEGER PRIMARY KEY, is_owner INTEGER NOT NULL DEFAULT 0, added_at REAL);
CREATE TABLE IF NOT EXISTS reports(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question_id INTEGER NOT NULL, tg_id INTEGER NOT NULL, reason TEXT NOT NULL,
  created_at REAL NOT NULL, status TEXT NOT NULL DEFAULT 'open',
  UNIQUE(question_id, tg_id)
);
CREATE TABLE IF NOT EXISTS game_sessions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER NOT NULL, kind TEXT NOT NULL,
  state TEXT NOT NULL, score INTEGER, started_at REAL NOT NULL, finished_at REAL
);
CREATE TABLE IF NOT EXISTS game_scores(
  tg_id INTEGER NOT NULL, kind TEXT NOT NULL, best INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(tg_id, kind)
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(tg_id, state);
"""

# أعمدة أُضيفت لاحقًا: تُضاف تلقائيًا لقواعد البيانات القديمة (ترقية آمنة بلا فقد بيانات)
MIGRATIONS = {
    "questions": {
        "source": "TEXT NOT NULL DEFAULT 'file'", "edited": "INTEGER NOT NULL DEFAULT 0",
        "image": "TEXT", "q_en": "TEXT", "options_en": "TEXT", "img_fail": "INTEGER NOT NULL DEFAULT 0",
    },
    "users": {"lang": "TEXT NOT NULL DEFAULT 'ar'", "best_sudden": "INTEGER NOT NULL DEFAULT 0"},
    "sessions": {
        "mode": "TEXT NOT NULL DEFAULT 'full'", "counted": "INTEGER NOT NULL DEFAULT 1",
        "challenge_of": "INTEGER", "msg_kind": "TEXT NOT NULL DEFAULT 'text'", "category": "TEXT",
    },
}
ADMIN_ID_BASE = 100000   # أسئلة الأدمن تبدأ من هنا حتى لا تتعارض مع أرقام ملف الأسئلة


class DB:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        for table, cols in MIGRATIONS.items():
            have = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")}
            for col, ddl in cols.items():
                if col not in have:
                    self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        self.conn.commit()

    # ── الإعدادات والمشرفون ──────────────────────────────────
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        r = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

    def set_setting(self, key: str, value: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value))

    def is_admin(self, tg_id: int) -> bool:
        return self.conn.execute("SELECT 1 FROM admins WHERE tg_id=?", (tg_id,)).fetchone() is not None

    def is_owner(self, tg_id: int) -> bool:
        r = self.conn.execute("SELECT is_owner FROM admins WHERE tg_id=?", (tg_id,)).fetchone()
        return bool(r and r["is_owner"])

    def admin_ids(self) -> list[int]:
        return [r["tg_id"] for r in self.conn.execute("SELECT tg_id FROM admins")]

    def admin_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM admins").fetchone()["n"]

    def add_admin(self, tg_id: int, owner: bool = False) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO admins(tg_id,is_owner,added_at) VALUES(?,?,?) "
                "ON CONFLICT(tg_id) DO UPDATE SET is_owner=MAX(is_owner, excluded.is_owner)",
                (tg_id, int(owner), time.time()))

    def remove_admin(self, tg_id: int) -> bool:
        with self.conn:
            cur = self.conn.execute("DELETE FROM admins WHERE tg_id=? AND is_owner=0", (tg_id,))
        return cur.rowcount > 0

    # ── الأسئلة ──────────────────────────────────────────────
    def load_questions(self, path: str) -> int:
        """يحمّل/يحدّث الأسئلة من JSON. يحافظ على إحصائيات asked/correct وعلى ما عدّلته من لوحة الأدمن."""
        return self.upsert_questions(json.loads(Path(path).read_text(encoding="utf-8")))

    def upsert_questions(self, data: list[dict]) -> int:
        with self.conn:
            for d in data:
                assert len(d["options"]) >= 2 and 0 <= d["answer"] < len(d["options"]), d["id"]
                self.conn.execute(
                    """INSERT INTO questions(id,q,options,answer,category,base_difficulty,source,image,q_en,options_en)
                       VALUES(?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET q=excluded.q, options=excluded.options,
                         answer=excluded.answer, category=excluded.category,
                         base_difficulty=excluded.base_difficulty, image=excluded.image,
                         q_en=excluded.q_en, options_en=excluded.options_en
                       WHERE questions.edited=0""",
                    (d["id"], d["q"], json.dumps(d["options"], ensure_ascii=False), d["answer"],
                     d["category"], d["base_difficulty"], d.get("source", "file"), d.get("image"),
                     d.get("q_en"), json.dumps(d["options_en"], ensure_ascii=False) if d.get("options_en") else None))
        return len(data)

    @staticmethod
    def _q(r: sqlite3.Row) -> Question:
        return Question(r["id"], r["q"], json.loads(r["options"]), r["answer"], r["category"],
                        r["base_difficulty"], r["asked"], r["correct"], r["image"], r["q_en"],
                        json.loads(r["options_en"]) if r["options_en"] else None, not r["flagged"])

    def all_questions(self) -> list[Question]:
        rows = self.conn.execute("SELECT * FROM questions WHERE flagged=0").fetchall()
        return [self._q(r) for r in rows]

    def get_question(self, qid: int) -> Question | None:
        r = self.conn.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
        return self._q(r) if r else None

    def question_source(self, qid: int) -> str | None:
        r = self.conn.execute("SELECT source FROM questions WHERE id=?", (qid,)).fetchone()
        return r["source"] if r else None

    def add_question(self, q: str, options: list[str], answer: int, category: str, difficulty: float,
                     image: str | None = None, q_en: str | None = None,
                     options_en: list[str] | None = None, source: str = "admin") -> int:
        with self.conn:
            mx = self.conn.execute("SELECT MAX(id) m FROM questions WHERE id>=? AND id<?",
                                   (ADMIN_ID_BASE, 100_000_000)).fetchone()["m"]
            qid = max(ADMIN_ID_BASE, (mx or ADMIN_ID_BASE) + 1) if mx else ADMIN_ID_BASE
            self.conn.execute(
                """INSERT INTO questions(id,q,options,answer,category,base_difficulty,source,edited,image,q_en,options_en)
                   VALUES(?,?,?,?,?,?,?,1,?,?,?)""",
                (qid, q, json.dumps(options, ensure_ascii=False), answer, category, difficulty, source,
                 image, q_en, json.dumps(options_en, ensure_ascii=False) if options_en else None))
        return qid

    def update_question(self, qid: int, **fields) -> None:
        allowed = {"q", "options", "answer", "category", "base_difficulty", "image", "q_en", "options_en"}
        sets, vals = [], []
        for k, v in fields.items():
            assert k in allowed, k
            if k in ("options", "options_en") and v is not None:
                v = json.dumps(v, ensure_ascii=False)
            sets.append(f"{k}=?")
            vals.append(v)
        if not sets:
            return
        with self.conn:
            self.conn.execute(f"UPDATE questions SET {', '.join(sets)}, edited=1 WHERE id=?", (*vals, qid))

    def set_question_active(self, qid: int, active: bool) -> None:
        with self.conn:
            self.conn.execute("UPDATE questions SET flagged=?, edited=1 WHERE id=?", (0 if active else 1, qid))

    def delete_question(self, qid: int) -> bool:
        """الحذف النهائي للأسئلة غير القادمة من الملف فقط (أسئلة الملف تُعطَّل لأنها ستعود عند التحديث)."""
        with self.conn:
            cur = self.conn.execute("DELETE FROM questions WHERE id=? AND source!='file'", (qid,))
        return cur.rowcount > 0

    def search_questions(self, term: str, limit: int = 8) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT id,q,flagged,category FROM questions WHERE q LIKE ? OR q_en LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{term}%", f"%{term}%", limit)).fetchall()

    def bump_img_fail(self, qid: int) -> None:
        """صورة فشل تحميلها: بعد 3 مرات يُعطَّل السؤال تلقائيًا."""
        with self.conn:
            self.conn.execute("UPDATE questions SET img_fail=img_fail+1 WHERE id=?", (qid,))
            self.conn.execute("UPDATE questions SET flagged=1 WHERE id=? AND img_fail>=3", (qid,))

    def category_counts(self, lang: str = "ar") -> dict[str, int]:
        cond = "AND q_en IS NOT NULL" if lang == "en" else ""
        rows = self.conn.execute(
            f"SELECT category, COUNT(*) n FROM questions WHERE flagged=0 {cond} GROUP BY category").fetchall()
        return {r["category"]: r["n"] for r in rows}

    def seen_map(self, tg_id: int) -> dict[int, float]:
        rows = self.conn.execute("SELECT question_id, seen_at FROM user_seen WHERE tg_id=?", (tg_id,)).fetchall()
        return {r["question_id"]: r["seen_at"] for r in rows}

    # ── المستخدمون ───────────────────────────────────────────
    def upsert_user(self, tg_id: int, name: str, lang_hint: str | None = None) -> None:
        with self.conn:
            self.conn.execute(
                """INSERT INTO users(tg_id,name,created_at,lang) VALUES(?,?,?,?)
                   ON CONFLICT(tg_id) DO UPDATE SET name=excluded.name""",
                (tg_id, name, time.time(), lang_hint if lang_hint in ("ar", "en") else "ar"))

    def get_user(self, tg_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()

    def get_lang(self, tg_id: int) -> str:
        r = self.conn.execute("SELECT lang FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        return r["lang"] if r else "ar"

    def set_lang(self, tg_id: int, lang: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE users SET lang=? WHERE tg_id=?", (lang, tg_id))

    # ── الجلسات ──────────────────────────────────────────────
    def active_session(self, tg_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM sessions WHERE tg_id=? AND state='active' ORDER BY id DESC LIMIT 1", (tg_id,)).fetchone()

    def get_session(self, sid: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()

    def last_finished_at(self, tg_id: int) -> float | None:
        r = self.conn.execute(
            "SELECT MAX(finished_at) m FROM sessions WHERE tg_id=? AND state='finished' AND mode='full'",
            (tg_id,)).fetchone()
        return r["m"]

    def abandon_active(self, tg_id: int) -> None:
        with self.conn:
            self.conn.execute("UPDATE sessions SET state='abandoned' WHERE tg_id=? AND state='active'", (tg_id,))

    def create_session(self, tg_id: int, picked: list[tuple[Question, list[int], int]],
                       mode: str = "full", challenge_of: int | None = None,
                       category: str | None = None) -> int:
        now = time.time()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO sessions(tg_id, started_at, mode, challenge_of, category) VALUES(?,?,?,?,?)",
                (tg_id, now, mode, challenge_of, category))
            sid = cur.lastrowid
            for pos, (q, order, cpos) in enumerate(picked):
                self.conn.execute(
                    """INSERT INTO session_questions(session_id,pos,question_id,level,option_order,correct_pos)
                       VALUES(?,?,?,?,?,?)""", (sid, pos, q.id, q.level, json.dumps(order), cpos))
                self.conn.execute(
                    """INSERT INTO user_seen(tg_id,question_id,seen_at) VALUES(?,?,?)
                       ON CONFLICT(tg_id,question_id) DO UPDATE SET seen_at=excluded.seen_at""",
                    (tg_id, q.id, now))
        return sid

    def session_questions_ordered(self, sid: int) -> list[Question]:
        rows = self.conn.execute(
            "SELECT question_id FROM session_questions WHERE session_id=? ORDER BY pos", (sid,)).fetchall()
        return [q for q in (self.get_question(r["question_id"]) for r in rows) if q]

    def challenge_session(self, tg_id: int, challenger_sid: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM sessions WHERE tg_id=? AND challenge_of=? ORDER BY id DESC LIMIT 1",
            (tg_id, challenger_sid)).fetchone()

    def session_question(self, sid: int, pos: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM session_questions WHERE session_id=? AND pos=?", (sid, pos)).fetchone()

    def set_message(self, sid: int, message_id: int, kind: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE sessions SET message_id=?, msg_kind=? WHERE id=?", (message_id, kind, sid))

    def mark_sent(self, sid: int, pos: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE session_questions SET sent_at=COALESCE(sent_at, ?) WHERE session_id=? AND pos=?",
                (time.time(), sid, pos))

    def record_answer(self, sid: int, pos: int, choice: int, timed_out: bool = False) -> bool | None:
        """يسجّل الإجابة مرة واحدة فقط. يرجع صحيحة/خاطئة، أو None إن كانت مسجّلة سابقًا."""
        row = self.session_question(sid, pos)
        if row is None or row["user_answer"] is not None:
            return None
        correct = (not timed_out) and choice == row["correct_pos"]
        time_ms = int((time.time() - row["sent_at"]) * 1000) if row["sent_at"] else None
        with self.conn:
            self.conn.execute(
                "UPDATE session_questions SET user_answer=?, is_correct=?, time_ms=? WHERE session_id=? AND pos=?",
                (-1 if timed_out else choice, int(correct), time_ms, sid, pos))
            self.conn.execute("UPDATE questions SET asked=asked+1, correct=correct+? WHERE id=?",
                              (int(correct), row["question_id"]))
        return correct

    def skip_question(self, sid: int, pos: int) -> None:
        """سؤال لا يمكن عرضه (صورة معطوبة): يُتخطّى دون احتساب لا له ولا عليه."""
        with self.conn:
            self.conn.execute(
                "UPDATE session_questions SET user_answer=-2, is_correct=NULL WHERE session_id=? AND pos=?",
                (sid, pos))

    def advance(self, sid: int, new_pos: int) -> None:
        with self.conn:
            self.conn.execute("UPDATE sessions SET current_pos=? WHERE id=?", (new_pos, sid))

    def session_len(self, sid: int) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM session_questions WHERE session_id=?", (sid,)).fetchone()["n"]

    def session_answers(self, sid: int) -> list[Answer]:
        rows = self.conn.execute(
            """SELECT sq.level, q.category, sq.is_correct FROM session_questions sq
               JOIN questions q ON q.id=sq.question_id
               WHERE sq.session_id=? AND sq.is_correct IS NOT NULL ORDER BY sq.pos""", (sid,)).fetchall()
        return [Answer(r["level"], r["category"], bool(r["is_correct"])) for r in rows]

    def session_wrong(self, sid: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT pos, question_id FROM session_questions WHERE session_id=? AND is_correct=0 ORDER BY pos",
            (sid,)).fetchall()

    def finish_session(self, sid: int, tg_id: int, score: float, mode: str = "full",
                       counted: bool = True) -> None:
        """mode=full فقط يرفع أفضل نتيجة وعدد الاختبارات. counted=False للنتائج المشبوهة."""
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET state='finished', finished_at=?, score=?, counted=? WHERE id=?",
                (time.time(), score, int(counted), sid))
            if mode == "full":
                self.conn.execute(
                    "UPDATE users SET tests_taken=tests_taken+1, best_score=MAX(best_score, ?) WHERE tg_id=?",
                    (score if counted else 0.0, tg_id))

    def set_best_sudden(self, tg_id: int, n: int) -> int:
        with self.conn:
            self.conn.execute("UPDATE users SET best_sudden=MAX(best_sudden, ?) WHERE tg_id=?", (n, tg_id))
        return self.get_user(tg_id)["best_sudden"]

    # ── المتصدرون والإحصائيات ───────────────────────────────
    def percentile(self, score: float) -> float:
        r = self.conn.execute("SELECT COUNT(*) n, SUM(best_score < ?) below FROM users WHERE best_score>0",
                              (score,)).fetchone()
        n, below = r["n"] or 0, r["below"] or 0
        return 100.0 * below / n if n > 1 else 100.0

    def leaderboard(self, limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT name, best_score FROM users WHERE best_score>0 ORDER BY best_score DESC, tests_taken ASC LIMIT ?",
            (limit,)).fetchall()

    def user_rank(self, tg_id: int) -> int | None:
        u = self.get_user(tg_id)
        if not u or u["best_score"] <= 0:
            return None
        return self.conn.execute("SELECT COUNT(*)+1 rk FROM users WHERE best_score > ?", (u["best_score"],)).fetchone()["rk"]

    def weekly_leaderboard(self, since: float, limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT u.tg_id, u.name, MAX(s.score) AS score, MIN(s.finished_at) AS at
               FROM sessions s JOIN users u ON u.tg_id=s.tg_id
               WHERE s.state='finished' AND s.mode='full' AND s.counted=1 AND s.finished_at>=?
               GROUP BY u.tg_id ORDER BY score DESC, at ASC LIMIT ?""", (since, limit)).fetchall()

    def weekly_rank(self, tg_id: int, since: float) -> int | None:
        rows = self.weekly_leaderboard(since, 10000)
        for i, r in enumerate(rows, 1):
            if r["tg_id"] == tg_id:
                return i
        return None

    def sudden_leaderboard(self, limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT name, best_sudden FROM users WHERE best_sudden>0 ORDER BY best_sudden DESC LIMIT ?",
            (limit,)).fetchall()

    def last_session_stats(self, tg_id: int):
        return self.conn.execute(
            "SELECT score FROM sessions WHERE tg_id=? AND state='finished' AND mode='full' ORDER BY id DESC LIMIT 5",
            (tg_id,)).fetchall()

    def fast_answer_ratio(self, sid: int, threshold_ms: int = 1000) -> float:
        r = self.conn.execute(
            """SELECT AVG(time_ms IS NOT NULL AND time_ms < ?) f FROM session_questions
               WHERE session_id=? AND user_answer IS NOT NULL AND user_answer>=0""", (threshold_ms, sid)).fetchone()
        return r["f"] or 0.0

    def suspicious_questions(self, min_asked: int = 30) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT id, q, base_difficulty, asked, correct, ROUND(100.0*correct/asked,1) AS pct
               FROM questions WHERE asked>=? AND 1.0*correct/asked <= 0.27 ORDER BY pct""", (min_asked,)).fetchall()

    # ── البلاغات ─────────────────────────────────────────────
    def reports_today(self, tg_id: int) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM reports WHERE tg_id=? AND created_at>=?",
                                 (tg_id, day_start())).fetchone()["n"]

    def add_report(self, qid: int, tg_id: int, reason: str, daily_limit: int) -> str:
        """'ok' | 'dup' | 'limit' — بلاغ واحد لكل مستخدم لكل سؤال، وحد يومي لكل مستخدم."""
        if self.conn.execute("SELECT 1 FROM reports WHERE question_id=? AND tg_id=?", (qid, tg_id)).fetchone():
            return "dup"
        if self.reports_today(tg_id) >= daily_limit:
            return "limit"
        with self.conn:
            self.conn.execute("INSERT INTO reports(question_id,tg_id,reason,created_at) VALUES(?,?,?,?)",
                              (qid, tg_id, reason, time.time()))
        return "ok"

    def open_report_count(self, qid: int) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM reports WHERE question_id=? AND status='open'",
                                 (qid,)).fetchone()["n"]

    def open_reports_grouped(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT r.question_id AS qid, COUNT(*) AS n, q.q AS q FROM reports r
               JOIN questions q ON q.id=r.question_id WHERE r.status='open'
               GROUP BY r.question_id ORDER BY n DESC, MAX(r.created_at) DESC LIMIT 15""").fetchall()

    def report_reasons(self, qid: int) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT reason, COUNT(*) n FROM reports WHERE question_id=? AND status='open' GROUP BY reason",
            (qid,)).fetchall()
        return {r["reason"]: r["n"] for r in rows}

    def close_reports(self, qid: int, status: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE reports SET status=? WHERE question_id=? AND status='open'", (status, qid))

    # ── الألعاب ──────────────────────────────────────────────
    def new_game(self, tg_id: int, kind: str, state: dict) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO game_sessions(tg_id,kind,state,started_at) VALUES(?,?,?,?)",
                (tg_id, kind, json.dumps(state, ensure_ascii=False), time.time()))
        return cur.lastrowid

    def get_game(self, gid: int):
        r = self.conn.execute("SELECT * FROM game_sessions WHERE id=?", (gid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["state"] = json.loads(r["state"])
        return d

    def save_game(self, gid: int, state: dict) -> None:
        with self.conn:
            self.conn.execute("UPDATE game_sessions SET state=? WHERE id=?",
                              (json.dumps(state, ensure_ascii=False), gid))

    def finish_game(self, gid: int, tg_id: int, kind: str, score: int) -> int:
        with self.conn:
            self.conn.execute("UPDATE game_sessions SET score=?, finished_at=? WHERE id=?", (score, time.time(), gid))
            self.conn.execute(
                "INSERT INTO game_scores(tg_id,kind,best) VALUES(?,?,?) "
                "ON CONFLICT(tg_id,kind) DO UPDATE SET best=MAX(best, excluded.best)", (tg_id, kind, score))
        return self.conn.execute("SELECT best FROM game_scores WHERE tg_id=? AND kind=?", (tg_id, kind)).fetchone()["best"]

    # ── إحصائيات الأدمن ─────────────────────────────────────
    def admin_stats(self) -> dict:
        c = self.conn
        one = lambda sql, *a: c.execute(sql, a).fetchone()[0]   # noqa: E731
        now, today, week = time.time(), day_start(), time.time() - 7 * 86400
        return {
            "users": one("SELECT COUNT(*) FROM users"),
            "new_today": one("SELECT COUNT(*) FROM users WHERE created_at>=?", today),
            "new_7d": one("SELECT COUNT(*) FROM users WHERE created_at>=?", week),
            "active_today": one("SELECT COUNT(DISTINCT tg_id) FROM sessions WHERE started_at>=?", today),
            "active_7d": one("SELECT COUNT(DISTINCT tg_id) FROM sessions WHERE started_at>=?", week),
            "finished_total": one("SELECT COUNT(*) FROM sessions WHERE state='finished'"),
            "finished_today": one("SELECT COUNT(*) FROM sessions WHERE state='finished' AND finished_at>=?", today),
            "finished_7d": one("SELECT COUNT(*) FROM sessions WHERE state='finished' AND finished_at>=?", week),
            "started_7d": one("SELECT COUNT(*) FROM sessions WHERE started_at>=?", week),
            "avg_score": one("SELECT AVG(score) FROM sessions WHERE state='finished' AND mode='full' AND counted=1"),
            "returning": one("SELECT COUNT(*) FROM users WHERE tests_taken>=2"),
            "modes": {r["mode"]: r["n"] for r in c.execute(
                "SELECT mode, COUNT(*) n FROM sessions WHERE state='finished' GROUP BY mode")},
            "cat_acc": [(r["category"], r["acc"], r["n"]) for r in c.execute(
                """SELECT q.category, AVG(sq.is_correct) acc, COUNT(*) n FROM session_questions sq
                   JOIN questions q ON q.id=sq.question_id WHERE sq.is_correct IS NOT NULL
                   GROUP BY q.category ORDER BY acc""")],
            "hardest": [(r["id"], r["q"], r["pct"], r["asked"]) for r in c.execute(
                """SELECT id,q,ROUND(100.0*correct/asked) pct,asked FROM questions
                   WHERE asked>=10 ORDER BY 1.0*correct/asked ASC LIMIT 5""")],
            "easiest": [(r["id"], r["q"], r["pct"], r["asked"]) for r in c.execute(
                """SELECT id,q,ROUND(100.0*correct/asked) pct,asked FROM questions
                   WHERE asked>=10 ORDER BY 1.0*correct/asked DESC LIMIT 5""")],
            "open_reports": one("SELECT COUNT(DISTINCT question_id) FROM reports WHERE status='open'"),
            "bank_active": one("SELECT COUNT(*) FROM questions WHERE flagged=0"),
            "bank_disabled": one("SELECT COUNT(*) FROM questions WHERE flagged=1"),
            "bank_en": one("SELECT COUNT(*) FROM questions WHERE flagged=0 AND q_en IS NOT NULL"),
            "bank_img": one("SELECT COUNT(*) FROM questions WHERE flagged=0 AND image IS NOT NULL"),
        }

    def backup_to(self, dest: str) -> None:
        out = sqlite3.connect(dest)
        with out:
            self.conn.backup(out)
        out.close()
