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
CREATE TABLE IF NOT EXISTS suggestions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER NOT NULL, q TEXT NOT NULL, options TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',     -- pending | approved | rejected
  created_at REAL NOT NULL, qid INTEGER
);
CREATE TABLE IF NOT EXISTS feedback(
  id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',     -- pending | done | answered
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER NOT NULL, kind TEXT NOT NULL, ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS channel_snapshots(day TEXT PRIMARY KEY, count INTEGER NOT NULL, ts REAL NOT NULL);
CREATE TABLE IF NOT EXISTS game_reports(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, key TEXT NOT NULL, label TEXT NOT NULL,
  tg_id INTEGER NOT NULL, reason TEXT NOT NULL, created_at REAL NOT NULL, status TEXT NOT NULL DEFAULT 'open',
  UNIQUE(kind, key, tg_id)
);
CREATE TABLE IF NOT EXISTS extra_content(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, data TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS group_chats(
  chat_id INTEGER PRIMARY KEY, title TEXT, lang TEXT NOT NULL DEFAULT 'ar', created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS xp_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER NOT NULL, xp INTEGER NOT NULL, kind TEXT NOT NULL, at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_xp_log_user ON xp_log(tg_id, at);
CREATE INDEX IF NOT EXISTS idx_xp_log_at ON xp_log(at);
CREATE TABLE IF NOT EXISTS achievements(
  tg_id INTEGER NOT NULL, key TEXT NOT NULL, at REAL NOT NULL, PRIMARY KEY(tg_id, key)
);
CREATE TABLE IF NOT EXISTS user_stats(
  tg_id INTEGER NOT NULL, key TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(tg_id, key)
);
CREATE TABLE IF NOT EXISTS teams(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE COLLATE NOCASE, leader INTEGER NOT NULL,
  hidden INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS channel_links(
  chat_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, title TEXT, added_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS group_results(
  id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, tg_id INTEGER NOT NULL, points INTEGER NOT NULL,
  kind TEXT NOT NULL, won INTEGER NOT NULL DEFAULT 0, at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_group_results_chat ON group_results(chat_id, at);
CREATE TABLE IF NOT EXISTS daily_results(
  day INTEGER NOT NULL, mode TEXT NOT NULL, tg_id INTEGER NOT NULL, correct INTEGER NOT NULL, total INTEGER NOT NULL,
  secs REAL NOT NULL, PRIMARY KEY(day, mode, tg_id)
);
CREATE TABLE IF NOT EXISTS duels(
  id INTEGER PRIMARY KEY AUTOINCREMENT, creator INTEGER NOT NULL, opponent INTEGER, creator_sid INTEGER,
  opponent_sid INTEGER, state TEXT NOT NULL DEFAULT 'open', created_at REAL NOT NULL
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

# فهارس تُنشأ بعد الترقية (لأن بعضها على أعمدة أُضيفت لاحقًا)
INDEXES = """
CREATE INDEX IF NOT EXISTS idx_sessions_finished ON sessions(state, mode, finished_at);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_reports_q ON reports(question_id, status);
CREATE INDEX IF NOT EXISTS idx_users_best ON users(best_score);
CREATE INDEX IF NOT EXISTS idx_users_country ON users(country, best_score);
CREATE INDEX IF NOT EXISTS idx_sugg_status ON suggestions(status);
CREATE INDEX IF NOT EXISTS idx_events_user ON events(tg_id, kind);
CREATE INDEX IF NOT EXISTS idx_games_user ON game_sessions(tg_id, finished_at);
"""

# أعمدة أُضيفت لاحقًا: تُضاف تلقائيًا لقواعد البيانات القديمة (ترقية آمنة بلا فقد بيانات)
MIGRATIONS = {
    "questions": {
        "source": "TEXT NOT NULL DEFAULT 'file'", "edited": "INTEGER NOT NULL DEFAULT 0",
        "image": "TEXT", "q_en": "TEXT", "options_en": "TEXT", "img_fail": "INTEGER NOT NULL DEFAULT 0",
    },
    "users": {"lang": "TEXT NOT NULL DEFAULT 'ar'", "best_sudden": "INTEGER NOT NULL DEFAULT 0",
              "blocked": "INTEGER NOT NULL DEFAULT 0", "country": "TEXT", "country_asked": "INTEGER NOT NULL DEFAULT 0",
              "invited_by": "INTEGER", "invite_credited": "INTEGER NOT NULL DEFAULT 0",
              "streak": "INTEGER NOT NULL DEFAULT 0", "best_streak": "INTEGER NOT NULL DEFAULT 0",
              "streak_day": "INTEGER NOT NULL DEFAULT 0", "remind": "INTEGER NOT NULL DEFAULT 0",
              "last_remind_day": "INTEGER NOT NULL DEFAULT 0", "xp": "INTEGER NOT NULL DEFAULT 0",
              "freezes": "INTEGER NOT NULL DEFAULT 0", "team_id": "INTEGER"},
    "duels": {"target": "INTEGER"},
    "sessions": {
        "mode": "TEXT NOT NULL DEFAULT 'full'", "counted": "INTEGER NOT NULL DEFAULT 1",
        "challenge_of": "INTEGER", "duel_id": "INTEGER", "msg_kind": "TEXT NOT NULL DEFAULT 'text'", "category": "TEXT",
    },
}
ADMIN_ID_BASE = 100000   # أسئلة الأدمن تبدأ من هنا حتى لا تتعارض مع أرقام ملف الأسئلة


class DB:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(path, timeout=10)
        self.conn.row_factory = sqlite3.Row
        try:
            self.conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:       # بعض الاستضافات (أقراص الشبكة) لا تدعم WAL
            pass
        self.conn.execute("PRAGMA synchronous=NORMAL")   # أسرع بكثير على الأقراص البطيئة، وآمن مع WAL
        self.conn.execute("PRAGMA busy_timeout=10000")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.executescript(SCHEMA)
        for table, cols in MIGRATIONS.items():
            have = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")}
            for col, ddl in cols.items():
                if col not in have:
                    self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        self.conn.executescript(INDEXES)
        self.conn.commit()
        # كاشات في الذاكرة لما يُقرأ في كل تحديث (فلا نلمس القرص): الإعدادات، المشرفون، اللغة، بنك الأسئلة
        self._settings = {r["key"]: r["value"] for r in self.conn.execute("SELECT key,value FROM settings")}
        self._admins = {r["tg_id"] for r in self.conn.execute("SELECT tg_id FROM admins")}
        self._lang: dict[int, str] = {}
        self._qcache: tuple[float, list[Question]] | None = None
        self._stats_cache: tuple[float, dict] | None = None

    def _invalidate_questions(self) -> None:
        self._qcache = None

    # ── الإعدادات والمشرفون ──────────────────────────────────
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        return self._settings.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value))
        self._settings[key] = value

    def is_admin(self, tg_id: int) -> bool:
        return tg_id in self._admins

    def is_owner(self, tg_id: int) -> bool:
        r = self.conn.execute("SELECT is_owner FROM admins WHERE tg_id=?", (tg_id,)).fetchone()
        return bool(r and r["is_owner"])

    def admin_ids(self) -> list[int]:
        return sorted(self._admins)

    def admin_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM admins").fetchone()["n"]

    def add_admin(self, tg_id: int, owner: bool = False) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO admins(tg_id,is_owner,added_at) VALUES(?,?,?) "
                "ON CONFLICT(tg_id) DO UPDATE SET is_owner=MAX(is_owner, excluded.is_owner)",
                (tg_id, int(owner), time.time()))
        self._admins.add(tg_id)

    def remove_admin(self, tg_id: int) -> bool:
        with self.conn:
            cur = self.conn.execute("DELETE FROM admins WHERE tg_id=? AND is_owner=0", (tg_id,))
        if cur.rowcount > 0:
            self._admins.discard(tg_id)
        return cur.rowcount > 0

    # ── الأسئلة ──────────────────────────────────────────────
    def load_questions(self, path: str) -> int:
        """يحمّل/يحدّث الأسئلة من JSON. يحافظ على إحصائيات asked/correct وعلى ما عدّلته من لوحة الأدمن."""
        return self.upsert_questions(json.loads(Path(path).read_text(encoding="utf-8")))

    def upsert_questions(self, data: list[dict]) -> int:
        self._invalidate_questions()
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
        """نسخة مخزّنة 30 ثانية (إحصائيات الصعوبة تتأخر لحظات فقط)؛ أي تعديل يُبطلها فورًا."""
        if self._qcache and time.time() - self._qcache[0] < 30:
            return list(self._qcache[1])
        rows = self.conn.execute("SELECT * FROM questions WHERE flagged=0").fetchall()
        qs = [self._q(r) for r in rows]
        self._qcache = (time.time(), qs)
        return list(qs)

    def get_question(self, qid: int) -> Question | None:
        r = self.conn.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
        return self._q(r) if r else None

    def question_source(self, qid: int) -> str | None:
        r = self.conn.execute("SELECT source FROM questions WHERE id=?", (qid,)).fetchone()
        return r["source"] if r else None

    def add_question(self, q: str, options: list[str], answer: int, category: str, difficulty: float,
                     image: str | None = None, q_en: str | None = None,
                     options_en: list[str] | None = None, source: str = "admin") -> int:
        self._invalidate_questions()
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
        self._invalidate_questions()
        with self.conn:
            self.conn.execute(f"UPDATE questions SET {', '.join(sets)}, edited=1 WHERE id=?", (*vals, qid))

    def set_question_active(self, qid: int, active: bool) -> None:
        self._invalidate_questions()
        with self.conn:
            self.conn.execute("UPDATE questions SET flagged=?, edited=1 WHERE id=?", (0 if active else 1, qid))

    def delete_question(self, qid: int) -> bool:
        """الحذف النهائي للأسئلة غير القادمة من الملف فقط (أسئلة الملف تُعطَّل لأنها ستعود عند التحديث)."""
        self._invalidate_questions()
        with self.conn:
            cur = self.conn.execute("DELETE FROM questions WHERE id=? AND source!='file'", (qid,))
        return cur.rowcount > 0

    def search_questions(self, term: str, limit: int = 8) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT id,q,flagged,category FROM questions WHERE q LIKE ? OR q_en LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{term}%", f"%{term}%", limit)).fetchall()

    def bump_img_fail(self, qid: int) -> None:
        """صورة فشل تحميلها: بعد 3 مرات يُعطَّل السؤال تلقائيًا."""
        self._invalidate_questions()
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
        self._lang.pop(tg_id, None)
        with self.conn:
            self.conn.execute(
                """INSERT INTO users(tg_id,name,created_at,lang) VALUES(?,?,?,?)
                   ON CONFLICT(tg_id) DO UPDATE SET name=excluded.name, blocked=0""",
                (tg_id, name, time.time(), lang_hint if lang_hint in ("ar", "en") else "ar"))

    # ── الدعوات: تُحسب بعد أن يكمل المدعو أول اختبار كامل ويشترك بالقناة ──
    def set_inviter(self, tg_id: int, inviter: int) -> bool:
        """يسجّل الداعي لمستخدم جديد فقط (لم يُدعَ من قبل ولم يختبر)، ولا يُسمح بدعوة النفس."""
        if tg_id == inviter or not self.get_user(inviter):
            return False
        with self.conn:
            cur = self.conn.execute(
                "UPDATE users SET invited_by=? WHERE tg_id=? AND invited_by IS NULL AND tests_taken=0", (inviter, tg_id))
        return cur.rowcount > 0

    def pending_inviter(self, tg_id: int) -> int | None:
        r = self.conn.execute("SELECT invited_by FROM users WHERE tg_id=? AND invite_credited=0", (tg_id,)).fetchone()
        return r["invited_by"] if r and r["invited_by"] else None

    def credit_invite(self, tg_id: int) -> int | None:
        inv = self.pending_inviter(tg_id)
        if not inv:
            return None
        with self.conn:
            cur = self.conn.execute("UPDATE users SET invite_credited=1 WHERE tg_id=? AND invite_credited=0", (tg_id,))
        return inv if cur.rowcount else None

    def invite_count(self, inviter: int) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM users WHERE invited_by=? AND invite_credited=1",
                                 (inviter,)).fetchone()["n"]

    # ── ألعاب المجموعات ─────────────────────────────────────
    def touch_group(self, chat_id: int, title: str | None) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO group_chats(chat_id,title,created_at) VALUES(?,?,?) "
                "ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title", (chat_id, title, time.time()))

    def group_lang(self, chat_id: int) -> str:
        r = self.conn.execute("SELECT lang FROM group_chats WHERE chat_id=?", (chat_id,)).fetchone()
        return r["lang"] if r else "ar"

    def set_group_lang(self, chat_id: int, lang: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE group_chats SET lang=? WHERE chat_id=?", (lang, chat_id))

    def link_channel(self, chat_id: int, user_id: int, title: str | None) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO channel_links(chat_id,user_id,title,added_at) VALUES(?,?,?,?) "
                "ON CONFLICT(chat_id) DO UPDATE SET user_id=excluded.user_id, title=excluded.title",
                (chat_id, user_id, title, time.time()))

    def channel_owner(self, chat_id: int) -> int | None:
        r = self.conn.execute("SELECT user_id FROM channel_links WHERE chat_id=?", (chat_id,)).fetchone()
        return r["user_id"] if r else None

    def user_channels(self, user_id: int) -> list[tuple[int, str | None]]:
        return [(r["chat_id"], r["title"]) for r in self.conn.execute(
            "SELECT chat_id, title FROM channel_links WHERE user_id=? ORDER BY added_at DESC", (user_id,))]

    def group_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM group_chats").fetchone()["n"]

    def add_group_result(self, chat_id: int, tg_id: int, points: int, kind: str, won: bool) -> None:
        with self.conn:
            self.conn.execute("INSERT INTO group_results(chat_id,tg_id,points,kind,won,at) VALUES(?,?,?,?,?,?)",
                              (chat_id, tg_id, points, kind, int(won), time.time()))

    def group_top(self, chat_id: int, since: float = 0.0, limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT u.name, SUM(r.points) pts, COUNT(*) games, SUM(r.won) wins FROM group_results r
               JOIN users u ON u.tg_id=r.tg_id WHERE r.chat_id=? AND r.at>=?
               AND r.tg_id NOT IN (SELECT tg_id FROM admins)
               GROUP BY r.tg_id ORDER BY pts DESC LIMIT ?""", (chat_id, since, limit)).fetchall()

    # ── التحدي اليومي والسلسلة والتذكير ─────────────────────
    @staticmethod
    def today() -> int:
        """رقم اليوم بتوقيت مكة."""
        return int((time.time() + 3 * 3600) // 86400)

    def played_today(self, tg_id: int, mode: str) -> bool:
        """أي جلسة من هذا النوع بدأت اليوم (حتى لو تُركت) = المحاولة الوحيدة لليوم."""
        return bool(self.conn.execute("SELECT 1 FROM sessions WHERE tg_id=? AND mode=? AND started_at>=?",
                                      (tg_id, mode, day_start())).fetchone())

    def session_time_ms(self, sid: int) -> int:
        return self.conn.execute("SELECT COALESCE(SUM(time_ms),0) m FROM session_questions WHERE session_id=?",
                                 (sid,)).fetchone()["m"]

    def record_daily(self, day: int, mode: str, tg_id: int, correct: int, total: int, secs: float) -> None:
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO daily_results(day,mode,tg_id,correct,total,secs) VALUES(?,?,?,?,?,?)",
                              (day, mode, tg_id, correct, total, secs))

    def daily_result(self, day: int, mode: str, tg_id: int):
        return self.conn.execute("SELECT * FROM daily_results WHERE day=? AND mode=? AND tg_id=?",
                                 (day, mode, tg_id)).fetchone()

    def daily_board(self, day: int, mode: str = "daily", limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT d.tg_id, u.name, d.correct, d.total, d.secs FROM daily_results d JOIN users u ON u.tg_id=d.tg_id
               WHERE d.day=? AND d.mode=? AND d.tg_id NOT IN (SELECT tg_id FROM admins)
               ORDER BY d.correct DESC, d.secs ASC LIMIT ?""", (day, mode, limit)).fetchall()

    def daily_rank(self, day: int, mode: str, tg_id: int) -> int | None:
        for i, r in enumerate(self.daily_board(day, mode, 100000), 1):
            if r["tg_id"] == tg_id:
                return i
        return None

    def daily_pct(self, day: int, mode: str) -> tuple[int, int]:
        """(نسبة الصحيح %, عدد اللاعبين) لسؤال اليوم."""
        r = self.conn.execute("SELECT COUNT(*) n, SUM(correct*1.0/total) ok FROM daily_results WHERE day=? AND mode=?",
                              (day, mode)).fetchone()
        n = r["n"] or 0
        return (round(100 * (r["ok"] or 0) / n) if n else 0), n

    FREEZE_CAP = 3

    def mark_streak(self, tg_id: int, day: int) -> tuple[int, bool]:
        """يسجّل نشاط اليوم: متتالية الأيام. يرجع (السلسلة, هل زادت اليوم).
        فاتك يوم واحد وعندك «تجميد» → يُستهلك وتستمر السلسلة. كل 7 أيام متتالية = تجميد جديد (حتى 3)."""
        u = self.get_user(tg_id)
        if u["streak_day"] == day:
            return u["streak"], False
        used = False
        if u["streak_day"] == day - 1:
            streak = u["streak"] + 1
        elif u["streak_day"] == day - 2 and u["freezes"] > 0 and u["streak"] > 0:
            streak, used = u["streak"] + 1, True
        else:
            streak = 1
        gain = 1 if (streak % 7 == 0 and streak > 0) else 0
        with self.conn:
            self.conn.execute(
                "UPDATE users SET streak=?, streak_day=?, best_streak=MAX(best_streak, ?), "
                "freezes=MIN(?, MAX(0, freezes - ? + ?)) WHERE tg_id=?",
                (streak, day, streak, self.FREEZE_CAP, int(used), gain, tg_id))
        self._last_freeze = (used, gain)
        return streak, True

    def last_freeze_event(self) -> tuple[bool, int]:
        """(هل استُهلك تجميد، كم تجميدًا كُسب) في آخر mark_streak."""
        return getattr(self, "_last_freeze", (False, 0))

    def current_streak(self, tg_id: int, day: int) -> int:
        """السلسلة الفعّالة: حيّة إن لعبت أمس، أو قبل أمس وعندك تجميد يغطي اليوم الفائت."""
        u = self.get_user(tg_id)
        if not u:
            return 0
        if u["streak_day"] >= day - 1 or (u["streak_day"] == day - 2 and u["freezes"] > 0):
            return u["streak"]
        return 0

    def set_remind(self, tg_id: int, on: bool) -> None:
        with self.conn:
            self.conn.execute("UPDATE users SET remind=? WHERE tg_id=?", (int(on), tg_id))

    def remind_targets(self, day: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT tg_id, streak, streak_day, lang FROM users WHERE remind=1 AND blocked=0 AND last_remind_day<?
               AND streak_day<?""", (day, day)).fetchall()

    def mark_reminded(self, tg_id: int, day: int) -> None:
        with self.conn:
            self.conn.execute("UPDATE users SET last_remind_day=? WHERE tg_id=?", (day, tg_id))

    # ── الخبرة والمستويات والإنجازات ────────────────────────
    def add_xp(self, tg_id: int, amount: int, kind: str) -> int:
        with self.conn:
            self.conn.execute("UPDATE users SET xp=xp+? WHERE tg_id=?", (amount, tg_id))
            self.conn.execute("INSERT INTO xp_log(tg_id,xp,kind,at) VALUES(?,?,?,?)", (tg_id, amount, kind, time.time()))
        return self.get_user(tg_id)["xp"]

    def xp_today(self, tg_id: int, prefix: str) -> int:
        return self.conn.execute("SELECT COALESCE(SUM(xp),0) n FROM xp_log WHERE tg_id=? AND kind LIKE ? AND at>=?",
                                 (tg_id, prefix + "%", day_start())).fetchone()["n"]

    def weekly_xp(self, tg_id: int, since: float) -> int:
        return self.conn.execute("SELECT COALESCE(SUM(xp),0) n FROM xp_log WHERE tg_id=? AND at>=?",
                                 (tg_id, since)).fetchone()["n"]

    def bump_stat(self, tg_id: int, key: str, n: int = 1) -> int:
        with self.conn:
            self.conn.execute("INSERT INTO user_stats(tg_id,key,n) VALUES(?,?,?) "
                              "ON CONFLICT(tg_id,key) DO UPDATE SET n=n+excluded.n", (tg_id, key, n))
        return self.stat(tg_id, key)

    def max_stat(self, tg_id: int, key: str, v: int) -> int:
        with self.conn:
            self.conn.execute("INSERT INTO user_stats(tg_id,key,n) VALUES(?,?,?) "
                              "ON CONFLICT(tg_id,key) DO UPDATE SET n=MAX(n,excluded.n)", (tg_id, key, v))
        return self.stat(tg_id, key)

    def stat(self, tg_id: int, key: str) -> int:
        r = self.conn.execute("SELECT n FROM user_stats WHERE tg_id=? AND key=?", (tg_id, key)).fetchone()
        return r["n"] if r else 0

    def unlock(self, tg_id: int, key: str) -> bool:
        with self.conn:
            cur = self.conn.execute("INSERT OR IGNORE INTO achievements(tg_id,key,at) VALUES(?,?,?)", (tg_id, key, time.time()))
        return cur.rowcount > 0

    def achievements_of(self, tg_id: int) -> dict[str, float]:
        return {r["key"]: r["at"] for r in self.conn.execute("SELECT key, at FROM achievements WHERE tg_id=?", (tg_id,))}

    # ── العشائر (فرق) ───────────────────────────────────────
    TEAM_MAX = 30

    def create_team(self, name: str, leader: int) -> int | None:
        u = self.get_user(leader)
        if not u or u["team_id"] or self.is_admin(leader):
            return None
        try:
            with self.conn:
                tid = self.conn.execute("INSERT INTO teams(name,leader,created_at) VALUES(?,?,?)",
                                        (name, leader, time.time())).lastrowid
                self.conn.execute("UPDATE users SET team_id=? WHERE tg_id=?", (tid, leader))
        except sqlite3.IntegrityError:
            return None                                         # الاسم مستخدم
        return tid

    def get_team(self, tid: int):
        return self.conn.execute("SELECT * FROM teams WHERE id=?", (tid,)).fetchone()

    def team_size(self, tid: int) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM users WHERE team_id=?", (tid,)).fetchone()["n"]

    def join_team(self, uid: int, tid: int) -> str:
        t = self.get_team(tid)
        u = self.get_user(uid)
        if not t or t["hidden"] or not u:
            return "gone"
        if self.is_admin(uid):
            return "admin"
        if u["team_id"]:
            return "already" if u["team_id"] == tid else "in_other"
        if self.team_size(tid) >= self.TEAM_MAX:
            return "full"
        with self.conn:
            self.conn.execute("UPDATE users SET team_id=? WHERE tg_id=?", (tid, uid))
        return "ok"

    def leave_team(self, uid: int) -> None:
        u = self.get_user(uid)
        if not u or not u["team_id"]:
            return
        tid = u["team_id"]
        with self.conn:
            self.conn.execute("UPDATE users SET team_id=NULL WHERE tg_id=?", (uid,))
            t = self.get_team(tid)
            if t and t["leader"] == uid:                         # القيادة تنتقل لأعلى عضو خبرة
                nxt = self.conn.execute("SELECT tg_id FROM users WHERE team_id=? ORDER BY xp DESC LIMIT 1", (tid,)).fetchone()
                if nxt:
                    self.conn.execute("UPDATE teams SET leader=? WHERE id=?", (nxt["tg_id"], tid))

    def team_members(self, tid: int, since: float = 0.0, limit: int = 10) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            """SELECT u.tg_id, u.name, u.xp, COALESCE((SELECT SUM(x.xp) FROM xp_log x WHERE x.tg_id=u.tg_id AND x.at>=?),0) AS wxp
               FROM users u WHERE u.team_id=? ORDER BY wxp DESC, u.xp DESC LIMIT ?""", (since, tid, limit))]

    def team_board(self, since: float | None = None, limit: int = 10) -> list[dict]:
        """ترتيب العشائر بمجموع خبرة أعضائها (أسبوعي إن أُعطي since، وإلا كل الأوقات)."""
        if since is None:
            sql = ("SELECT t.id, t.name, COUNT(u.tg_id) members, COALESCE(SUM(u.xp),0) pts FROM teams t JOIN users u ON u.team_id=t.id "
                   "WHERE t.hidden=0 GROUP BY t.id ORDER BY pts DESC, t.id ASC LIMIT ?")
            args = (limit,)
        else:
            sql = ("SELECT t.id, t.name, COUNT(u.tg_id) members, "
                   "COALESCE(SUM((SELECT SUM(x.xp) FROM xp_log x WHERE x.tg_id=u.tg_id AND x.at>=?)),0) pts "
                   "FROM teams t JOIN users u ON u.team_id=t.id WHERE t.hidden=0 GROUP BY t.id ORDER BY pts DESC, t.id ASC LIMIT ?")
            args = (since, limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def team_rank(self, tid: int, since: float | None) -> int | None:
        for i, r in enumerate(self.team_board(since, 100000), 1):
            if r["id"] == tid:
                return i
        return None

    def hide_team(self, tid: int, hidden: bool = True) -> None:
        with self.conn:
            self.conn.execute("UPDATE teams SET hidden=? WHERE id=?", (int(hidden), tid))
            if hidden:
                self.conn.execute("UPDATE users SET team_id=NULL WHERE team_id=?", (tid,))

    # ── مواجهة مع صديق ──────────────────────────────────────
    def create_duel(self, creator: int, target: int | None = None) -> int:
        with self.conn:
            return self.conn.execute("INSERT INTO duels(creator,created_at,target) VALUES(?,?,?)",
                                     (creator, time.time(), target)).lastrowid

    def get_duel(self, did: int):
        return self.conn.execute("SELECT * FROM duels WHERE id=?", (did,)).fetchone()

    def join_duel(self, did: int, tg_id: int) -> bool:
        """أول من يقبل فقط، أو نفس اللاعب إن أعاد المحاولة قبل أن ينتهي."""
        with self.conn:
            cur = self.conn.execute(
                "UPDATE duels SET opponent=? WHERE id=? AND state='open' AND creator!=? AND (opponent IS NULL OR opponent=?)",
                (tg_id, did, tg_id, tg_id))
        return cur.rowcount > 0

    def duel_set_sid(self, did: int, role: str, sid: int) -> None:
        col = "creator_sid" if role == "creator" else "opponent_sid"
        with self.conn:
            self.conn.execute(f"UPDATE duels SET {col}=? WHERE id=?", (sid, did))

    def duel_done(self, did: int) -> None:
        with self.conn:
            self.conn.execute("UPDATE duels SET state='done' WHERE id=?", (did,))

    def get_user(self, tg_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()

    def get_lang(self, tg_id: int) -> str:
        if tg_id not in self._lang:
            r = self.conn.execute("SELECT lang FROM users WHERE tg_id=?", (tg_id,)).fetchone()
            if not r:
                return "ar"
            self._lang[tg_id] = r["lang"]
        return self._lang[tg_id]

    def set_lang(self, tg_id: int, lang: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE users SET lang=? WHERE tg_id=?", (lang, tg_id))
        self._lang[tg_id] = lang

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
                       category: str | None = None, duel_id: int | None = None) -> int:
        now = time.time()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO sessions(tg_id, started_at, mode, challenge_of, category, duel_id) VALUES(?,?,?,?,?,?)",
                (tg_id, now, mode, challenge_of, category, duel_id))
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
            "SELECT name, best_score FROM users WHERE best_score>0 AND tg_id NOT IN (SELECT tg_id FROM admins) "
            "ORDER BY best_score DESC, tests_taken ASC LIMIT ?", (limit,)).fetchall()

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
               AND u.tg_id NOT IN (SELECT tg_id FROM admins)
               GROUP BY u.tg_id ORDER BY score DESC, at ASC LIMIT ?""", (since, limit)).fetchall()

    def weekly_rank(self, tg_id: int, since: float) -> int | None:
        rows = self.weekly_leaderboard(since, 10000)
        for i, r in enumerate(rows, 1):
            if r["tg_id"] == tg_id:
                return i
        return None

    def board(self, kind: str, since: float | None = None, limit: int = 100000) -> list[dict]:
        """لوحة موحّدة: kind = q (الاختبار الكامل) | s (الموت المفاجئ) | tf/song/ord/char/quote؛
        since=None → كل الأوقات (أفضل رقم لكل لاعب)، وإلا أفضل رقم داخل الفترة. الأدمن مستبعد."""
        adm = "NOT IN (SELECT tg_id FROM admins)"
        if since is None:
            if kind == "q":
                sql, args = (f"SELECT tg_id, name, best_score AS score FROM users WHERE best_score>0 AND tg_id {adm} "
                             "ORDER BY best_score DESC, tests_taken ASC, tg_id ASC LIMIT ?"), (limit,)
            elif kind == "s":
                sql, args = (f"SELECT tg_id, name, best_sudden AS score FROM users WHERE best_sudden>0 AND tg_id {adm} "
                             "ORDER BY best_sudden DESC, tg_id ASC LIMIT ?"), (limit,)
            else:
                sql, args = (f"SELECT u.tg_id, u.name, g.best AS score FROM game_scores g JOIN users u ON u.tg_id=g.tg_id "
                             f"WHERE g.kind=? AND g.best>0 AND g.tg_id {adm} ORDER BY g.best DESC, u.tg_id ASC LIMIT ?"), (kind, limit)
        elif kind in ("q", "s"):
            mode = "full" if kind == "q" else "sudden"
            extra = "AND s.counted=1" if kind == "q" else ""
            sql, args = (f"SELECT u.tg_id, u.name, MAX(s.score) AS score FROM sessions s JOIN users u ON u.tg_id=s.tg_id "
                         f"WHERE s.state='finished' AND s.mode=? {extra} AND s.finished_at>=? AND u.tg_id {adm} "
                         "GROUP BY u.tg_id HAVING score>0 ORDER BY score DESC, MIN(s.finished_at) ASC LIMIT ?"), (mode, since, limit)
        else:
            sql, args = (f"SELECT u.tg_id, u.name, MAX(g.score) AS score FROM game_sessions g JOIN users u ON u.tg_id=g.tg_id "
                         f"WHERE g.kind=? AND g.finished_at IS NOT NULL AND g.finished_at>=? AND u.tg_id {adm} "
                         "GROUP BY u.tg_id HAVING score>0 ORDER BY score DESC, MIN(g.finished_at) ASC LIMIT ?"), (kind, since, limit)
        return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def sudden_rank(self, tg_id: int) -> int | None:
        u = self.get_user(tg_id)
        if not u or u["best_sudden"] <= 0:
            return None
        return self.conn.execute("SELECT COUNT(*)+1 rk FROM users WHERE best_sudden>? AND tg_id NOT IN (SELECT tg_id FROM admins)",
                                 (u["best_sudden"],)).fetchone()["rk"]

    def game_rank(self, tg_id: int, kind: str) -> int | None:
        r = self.conn.execute("SELECT best FROM game_scores WHERE tg_id=? AND kind=?", (tg_id, kind)).fetchone()
        if not r or r["best"] <= 0:
            return None
        return self.conn.execute(
            "SELECT COUNT(*)+1 rk FROM game_scores WHERE kind=? AND best>? AND tg_id NOT IN (SELECT tg_id FROM admins)",
            (kind, r["best"])).fetchone()["rk"]

    def sudden_leaderboard(self, limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT name, best_sudden FROM users WHERE best_sudden>0 AND tg_id NOT IN (SELECT tg_id FROM admins) ORDER BY best_sudden DESC LIMIT ?",
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

    # ── اقتراحات الأسئلة من اللاعبين ────────────────────────
    def suggestions_today(self, tg_id: int) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM suggestions WHERE tg_id=? AND created_at>=?",
                                 (tg_id, day_start())).fetchone()["n"]

    def pending_suggestions_of(self, tg_id: int) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM suggestions WHERE tg_id=? AND status='pending'",
                                 (tg_id,)).fetchone()["n"]

    def pending_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM suggestions WHERE status='pending'").fetchone()["n"]

    def text_exists(self, text: str) -> bool:
        """هل السؤال موجود في البنك أو في اقتراحات معلّقة؟ (مقارنة غير حساسة للحالة)"""
        t = text.strip().lower()
        if self.conn.execute("SELECT 1 FROM questions WHERE lower(q)=? OR lower(q_en)=?", (t, t)).fetchone():
            return True
        return self.conn.execute("SELECT 1 FROM suggestions WHERE status='pending' AND lower(q)=?", (t,)).fetchone() is not None

    def add_suggestion(self, tg_id: int, q: str, options: list[str]) -> int:
        """options[0] هو الجواب الصحيح."""
        with self.conn:
            cur = self.conn.execute("INSERT INTO suggestions(tg_id,q,options,created_at) VALUES(?,?,?,?)",
                                    (tg_id, q, json.dumps(options, ensure_ascii=False), time.time()))
        return cur.lastrowid

    # ── الاقتراحات والملاحظات (تطوير، أنمي، مشكلة، ملاحظة) ───────
    def add_feedback(self, tg_id: int, kind: str, text: str) -> int:
        with self.conn:
            return self.conn.execute("INSERT INTO feedback(tg_id,kind,text,created_at) VALUES(?,?,?,?)",
                                     (tg_id, kind, text, time.time())).lastrowid

    def feedback_today(self, tg_id: int) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM feedback WHERE tg_id=? AND created_at>=?",
                                 (tg_id, day_start())).fetchone()["n"]

    def feedback_exists(self, tg_id: int, text: str) -> bool:
        return bool(self.conn.execute("SELECT 1 FROM feedback WHERE tg_id=? AND lower(text)=lower(?)",
                                      (tg_id, text)).fetchone())

    def feedback_counts(self) -> dict[str, int]:
        return {r["kind"]: r["n"] for r in self.conn.execute(
            "SELECT kind, COUNT(*) n FROM feedback WHERE status='pending' GROUP BY kind")}

    def feedback_list(self, kind: str, limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM feedback WHERE kind=? AND status='pending' ORDER BY id LIMIT ?",
                                 (kind, limit)).fetchall()

    def get_feedback(self, fid: int):
        return self.conn.execute("SELECT * FROM feedback WHERE id=?", (fid,)).fetchone()

    def set_feedback_status(self, fid: int, status: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE feedback SET status=? WHERE id=?", (status, fid))

    def pending_suggestions(self, limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM suggestions WHERE status='pending' ORDER BY id LIMIT ?", (limit,)).fetchall()

    def get_suggestion(self, sid: int) -> dict | None:
        r = self.conn.execute("SELECT * FROM suggestions WHERE id=?", (sid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["options"] = json.loads(r["options"])
        return d

    def set_suggestion_status(self, sid: int, status: str, qid: int | None = None) -> None:
        with self.conn:
            self.conn.execute("UPDATE suggestions SET status=?, qid=? WHERE id=?", (status, qid, sid))

    # ── الدول ────────────────────────────────────────────────
    def get_country(self, tg_id: int) -> str | None:
        r = self.conn.execute("SELECT country FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        return r["country"] if r else None

    def set_country(self, tg_id: int, code: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE users SET country=?, country_asked=1 WHERE tg_id=?", (code, tg_id))

    def country_asked(self, tg_id: int) -> bool:
        r = self.conn.execute("SELECT country_asked FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        return bool(r and r["country_asked"])

    def mark_country_asked(self, tg_id: int) -> None:
        with self.conn:
            self.conn.execute("UPDATE users SET country_asked=1 WHERE tg_id=?", (tg_id,))

    def country_players(self, code: str, limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT tg_id, name, best_score FROM users WHERE country=? AND best_score>0 "
            "ORDER BY best_score DESC, tests_taken ASC LIMIT ?", (code, limit)).fetchall()

    def country_rank(self, tg_id: int) -> int | None:
        u = self.get_user(tg_id)
        if not u or not u["country"] or u["best_score"] <= 0:
            return None
        return self.conn.execute("SELECT COUNT(*)+1 rk FROM users WHERE country=? AND best_score>?",
                                 (u["country"], u["best_score"])).fetchone()["rk"]

    def countries_ranking(self, min_players: int = 3, top_n: int = 5) -> list[dict]:
        """ترتيب الدول: متوسط أفضل top_n لاعبين في كل دولة، وتظهر الدولة عند min_players لاعبين على الأقل
        (حتى لا تتصدر دولة بلاعب واحد محظوظ)."""
        by: dict[str, list[float]] = {}
        for r in self.conn.execute("SELECT country, best_score FROM users WHERE country IS NOT NULL AND best_score>0 "
                                   "ORDER BY best_score DESC"):
            by.setdefault(r["country"], []).append(r["best_score"])
        out = []
        for code, scores in by.items():
            if len(scores) >= min_players:
                top = scores[:top_n]
                out.append({"code": code, "score": sum(top) / len(top), "players": len(scores)})
        out.sort(key=lambda x: (-x["score"], -x["players"]))
        return out

    def country_counts(self, limit: int = 6) -> list[tuple[str, int]]:
        return [(r["country"], r["n"]) for r in self.conn.execute(
            "SELECT country, COUNT(*) n FROM users WHERE country IS NOT NULL GROUP BY country ORDER BY n DESC LIMIT ?", (limit,))]

    # ── الرسائل الجماعية ─────────────────────────────────────
    def broadcast_targets(self, lang: str | None = None) -> list[int]:
        sql, args = "SELECT tg_id FROM users WHERE blocked=0", ()
        if lang in ("ar", "en"):
            sql, args = sql + " AND lang=?", (lang,)
        return [r["tg_id"] for r in self.conn.execute(sql, args)]

    def mark_blocked(self, tg_id: int) -> None:
        with self.conn:
            self.conn.execute("UPDATE users SET blocked=1 WHERE tg_id=?", (tg_id,))

    # ── البلاغات ─────────────────────────────────────────────
    def reports_today(self, tg_id: int) -> int:
        """بلاغات اليوم (أسئلة الاختبار + عناصر الألعاب) لحساب الحد اليومي الواحد."""
        a = self.conn.execute("SELECT COUNT(*) n FROM reports WHERE tg_id=? AND created_at>=?", (tg_id, day_start())).fetchone()["n"]
        b = self.conn.execute("SELECT COUNT(*) n FROM game_reports WHERE tg_id=? AND created_at>=?", (tg_id, day_start())).fetchone()["n"]
        return a + b

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

    def session_shown(self, sid: int) -> list[sqlite3.Row]:
        """الأسئلة التي ظهرت فعلًا للاعب في هذه الجلسة (وحدها يحق له الإبلاغ عنها)."""
        return self.conn.execute(
            "SELECT pos, question_id, is_correct FROM session_questions WHERE session_id=? AND sent_at IS NOT NULL ORDER BY pos",
            (sid,)).fetchall()

    # بلاغات الألعاب (عناصرها في data/games.json وليست في جدول الأسئلة)
    def add_game_report(self, kind: str, key: str, label: str, tg_id: int, reason: str, daily_limit: int) -> str:
        if self.conn.execute("SELECT 1 FROM game_reports WHERE kind=? AND key=? AND tg_id=?", (kind, key, tg_id)).fetchone():
            return "dup"
        if self.reports_today(tg_id) >= daily_limit:
            return "limit"
        with self.conn:
            self.conn.execute("INSERT INTO game_reports(kind,key,label,tg_id,reason,created_at) VALUES(?,?,?,?,?,?)",
                              (kind, key, label[:160], tg_id, reason, time.time()))
        return "ok"

    def game_open_count(self, kind: str, key: str) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM game_reports WHERE kind=? AND key=? AND status='open'",
                                 (kind, key)).fetchone()["n"]

    def game_reports_grouped(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT kind, key, MAX(label) AS label, COUNT(*) AS n FROM game_reports WHERE status='open' "
            "GROUP BY kind, key ORDER BY n DESC, MAX(created_at) DESC LIMIT 15").fetchall()

    def game_report_info(self, kind: str, key: str) -> dict | None:
        rows = self.conn.execute("SELECT label, reason FROM game_reports WHERE kind=? AND key=? AND status='open'",
                                 (kind, key)).fetchall()
        if not rows:
            return None
        reasons: dict[str, int] = {}
        for r in rows:
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
        return {"label": rows[0]["label"], "n": len(rows), "reasons": reasons}

    def close_game_reports(self, kind: str, key: str, status: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE game_reports SET status=? WHERE kind=? AND key=? AND status='open'", (status, kind, key))

    # محتوى يضيفه الأدمن من اللوحة (عبارات صح/غلط، أنمي) ويبقى في القاعدة فتحميه النسخ الاحتياطية
    def add_extra(self, kind: str, data: dict) -> int:
        with self.conn:
            cur = self.conn.execute("INSERT INTO extra_content(kind,data,created_at) VALUES(?,?,?)",
                                    (kind, json.dumps(data, ensure_ascii=False), time.time()))
        return cur.lastrowid

    def extras(self, kind: str, after_id: int = 0) -> list[tuple[int, dict]]:
        return [(r["id"], json.loads(r["data"])) for r in self.conn.execute(
            "SELECT id, data FROM extra_content WHERE kind=? AND id>? ORDER BY id", (kind, after_id))]

    def unhide_game_item(self, key: str) -> None:
        self.set_setting("game_hidden", json.dumps(sorted(self.game_hidden() - {key})))

    def game_hidden(self) -> set[str]:
        try:
            return set(json.loads(self.get_setting("game_hidden", "[]") or "[]"))
        except ValueError:
            return set()

    def hide_game_item(self, key: str) -> None:
        self.set_setting("game_hidden", json.dumps(sorted(self.game_hidden() | {key})))

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

    def game_board(self, kind: str, limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT u.name, g.best FROM game_scores g JOIN users u ON u.tg_id=g.tg_id
               WHERE g.kind=? AND g.best>0 AND g.tg_id NOT IN (SELECT tg_id FROM admins)
               ORDER BY g.best DESC, u.tg_id ASC LIMIT ?""", (kind, limit)).fetchall()

    def finish_game(self, gid: int, tg_id: int, kind: str, score: int) -> int:
        with self.conn:
            self.conn.execute("UPDATE game_sessions SET score=?, finished_at=? WHERE id=?", (score, time.time(), gid))
            self.conn.execute(
                "INSERT INTO game_scores(tg_id,kind,best) VALUES(?,?,?) "
                "ON CONFLICT(tg_id,kind) DO UPDATE SET best=MAX(best, excluded.best)", (tg_id, kind, score))
        return self.conn.execute("SELECT best FROM game_scores WHERE tg_id=? AND kind=?", (tg_id, kind)).fetchone()["best"]

    def abort_game(self, gid: int) -> None:
        """إنهاء لعبة بلا تسجيل نتيجة."""
        with self.conn:
            self.conn.execute("UPDATE game_sessions SET finished_at=? WHERE id=? AND finished_at IS NULL", (time.time(), gid))

    def abort_active_games(self, tg_id: int) -> int:
        with self.conn:
            cur = self.conn.execute("UPDATE game_sessions SET finished_at=? WHERE tg_id=? AND finished_at IS NULL",
                                    (time.time(), tg_id))
        return cur.rowcount

    # ── الملف الشخصي ─────────────────────────────────────────
    def user_profile(self, tg_id: int) -> dict | None:
        u = self.get_user(tg_id)
        if not u:
            return None
        tot = self.conn.execute(
            """SELECT COUNT(*) n, COALESCE(SUM(sq.is_correct),0) ok FROM session_questions sq
               JOIN sessions s ON s.id=sq.session_id WHERE s.tg_id=? AND sq.is_correct IS NOT NULL""", (tg_id,)).fetchone()
        cats = [(r["category"], r["acc"], r["n"]) for r in self.conn.execute(
            """SELECT q.category, 1.0*SUM(sq.is_correct)/COUNT(*) acc, COUNT(*) n FROM session_questions sq
               JOIN sessions s ON s.id=sq.session_id JOIN questions q ON q.id=sq.question_id
               WHERE s.tg_id=? AND sq.is_correct IS NOT NULL GROUP BY q.category HAVING COUNT(*)>=5
               ORDER BY acc DESC, n DESC LIMIT 3""", (tg_id,))]
        games = {r["kind"]: r["best"] for r in self.conn.execute(
            "SELECT kind, best FROM game_scores WHERE tg_id=?", (tg_id,))}
        from .timeutil import week_start
        return {"name": u["name"], "best": u["best_score"], "tests": u["tests_taken"], "sudden": u["best_sudden"],
                "rank": self.user_rank(tg_id), "weekly_rank": self.weekly_rank(tg_id, week_start()),
                "answers": tot["n"], "correct": tot["ok"], "cats": cats, "games": games}

    # ── مسار اللاعبين ونمو القناة ───────────────────────────
    def log_event(self, tg_id: int, kind: str) -> None:
        with self.conn:
            self.conn.execute("INSERT INTO events(tg_id,kind,ts) VALUES(?,?,?)", (tg_id, kind, time.time()))

    def has_event(self, tg_id: int, kind: str) -> bool:
        return self.conn.execute("SELECT 1 FROM events WHERE tg_id=? AND kind=? LIMIT 1", (tg_id, kind)).fetchone() is not None

    def save_channel_count(self, count: int, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        day = time.strftime("%Y-%m-%d", time.gmtime(now + 3 * 3600))
        with self.conn:
            self.conn.execute(
                "INSERT INTO channel_snapshots(day,count,ts) VALUES(?,?,?) "
                "ON CONFLICT(day) DO UPDATE SET count=excluded.count, ts=excluded.ts", (day, count, now))

    def channel_growth(self, now: float | None = None) -> dict | None:
        """آخر عدد مشتركين + الفرق مقابل قياس عمره ≥7 و≥30 يومًا (أو أقدم قياس متاح)."""
        now = now if now is not None else time.time()
        last = self.conn.execute("SELECT count, ts FROM channel_snapshots ORDER BY ts DESC LIMIT 1").fetchone()
        if not last:
            return None
        out = {"count": last["count"], "ts": last["ts"]}
        for label, days in (("d7", 7), ("d30", 30)):
            ref = self.conn.execute("SELECT count, ts FROM channel_snapshots WHERE ts<=? ORDER BY ts DESC LIMIT 1",
                                    (now - days * 86400,)).fetchone()
            if not ref:
                ref = self.conn.execute("SELECT count, ts FROM channel_snapshots ORDER BY ts ASC LIMIT 1").fetchone()
            span = max(1, round((last["ts"] - ref["ts"]) / 86400)) if ref["ts"] < last["ts"] else 0
            out[label] = (last["count"] - ref["count"], span)
        return out

    def funnel_stats(self) -> dict:
        one = lambda sql, *a: self.conn.execute(sql, a).fetchone()[0]   # noqa: E731
        week = time.time() - 7 * 86400
        return {
            "started": one("SELECT COUNT(*) FROM users"),
            "with_test": one("SELECT COUNT(*) FROM users WHERE tests_taken>=1"),
            "returning": one("SELECT COUNT(*) FROM users WHERE tests_taken>=2"),
            "prompted": one("SELECT COUNT(DISTINCT tg_id) FROM events WHERE kind='gate_prompt'"),
            "joined": one("SELECT COUNT(DISTINCT tg_id) FROM events WHERE kind='gate_joined'"),
            "prompted_7d": one("SELECT COUNT(DISTINCT tg_id) FROM events WHERE kind='gate_prompt' AND ts>=?", week),
            "joined_7d": one("SELECT COUNT(DISTINCT tg_id) FROM events WHERE kind='gate_joined' AND ts>=?", week),
        }

    # ── إحصائيات الأدمن ─────────────────────────────────────
    def admin_stats(self, max_age: float = 30) -> dict:
        if self._stats_cache and time.time() - self._stats_cache[0] < max_age:
            return self._stats_cache[1]
        data = self._compute_admin_stats()
        self._stats_cache = (time.time(), data)
        return data

    def _compute_admin_stats(self) -> dict:
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
                """SELECT category, 1.0*SUM(correct)/SUM(asked) acc, SUM(asked) n FROM questions
                   WHERE asked>0 GROUP BY category ORDER BY acc""")],
            "hardest": [(r["id"], r["q"], r["pct"], r["asked"]) for r in c.execute(
                """SELECT id,q,ROUND(100.0*correct/asked) pct,asked FROM questions
                   WHERE asked>=10 ORDER BY 1.0*correct/asked ASC LIMIT 5""")],
            "easiest": [(r["id"], r["q"], r["pct"], r["asked"]) for r in c.execute(
                """SELECT id,q,ROUND(100.0*correct/asked) pct,asked FROM questions
                   WHERE asked>=10 ORDER BY 1.0*correct/asked DESC LIMIT 5""")],
            "open_reports": one("SELECT COUNT(DISTINCT question_id) FROM reports WHERE status='open'")
                            + one("SELECT COUNT(*) FROM (SELECT DISTINCT kind, key FROM game_reports WHERE status='open')"),
            "bank_active": one("SELECT COUNT(*) FROM questions WHERE flagged=0"),
            "bank_disabled": one("SELECT COUNT(*) FROM questions WHERE flagged=1"),
            "bank_en": one("SELECT COUNT(*) FROM questions WHERE flagged=0 AND q_en IS NOT NULL"),
            "bank_img": one("SELECT COUNT(*) FROM questions WHERE flagged=0 AND image IS NOT NULL"),
            "pending_suggestions": one("SELECT COUNT(*) FROM suggestions WHERE status='pending'"),
            "blocked_users": one("SELECT COUNT(*) FROM users WHERE blocked=1"),
        }

    def backup_to(self, dest: str) -> None:
        out = sqlite3.connect(dest)
        with out:
            self.conn.backup(out)
        out.close()
