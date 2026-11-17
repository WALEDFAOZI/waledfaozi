"""طبقة SQLite. اتصال واحد، والعمليات سريعة فلا حاجة لـ async هنا."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .quiz import Answer, Question

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
  option_order TEXT NOT NULL,             -- JSON: ترتيب الخيارات المعروض
  correct_pos INTEGER NOT NULL,
  user_answer INTEGER,                    -- NULL = لم يُجَب، -1 = انتهى الوقت
  is_correct INTEGER,
  sent_at REAL,
  time_ms INTEGER,
  PRIMARY KEY(session_id, pos)
);
CREATE TABLE IF NOT EXISTS user_seen(
  tg_id INTEGER NOT NULL,
  question_id INTEGER NOT NULL,
  seen_at REAL NOT NULL,
  PRIMARY KEY(tg_id, question_id)
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(tg_id, state);
"""


class DB:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    # ── الأسئلة ──────────────────────────────────────────────
    def load_questions(self, path: str) -> int:
        """يحمّل/يحدّث الأسئلة من JSON مع الإبقاء على إحصائيات asked/correct."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        with self.conn:
            for d in data:
                assert len(d["options"]) >= 2 and 0 <= d["answer"] < len(d["options"]), d["id"]
                self.conn.execute(
                    """INSERT INTO questions(id,q,options,answer,category,base_difficulty)
                       VALUES(?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET q=excluded.q, options=excluded.options,
                         answer=excluded.answer, category=excluded.category,
                         base_difficulty=excluded.base_difficulty""",
                    (d["id"], d["q"], json.dumps(d["options"], ensure_ascii=False),
                     d["answer"], d["category"], d["base_difficulty"]),
                )
        return len(data)

    @staticmethod
    def _q(r: sqlite3.Row) -> Question:
        return Question(r["id"], r["q"], json.loads(r["options"]), r["answer"], r["category"],
                        r["base_difficulty"], r["asked"], r["correct"])

    def all_questions(self) -> list[Question]:
        rows = self.conn.execute("SELECT * FROM questions WHERE flagged=0").fetchall()
        return [self._q(r) for r in rows]

    def get_question(self, qid: int) -> Question:
        return self._q(self.conn.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone())

    def seen_map(self, tg_id: int) -> dict[int, float]:
        rows = self.conn.execute(
            "SELECT question_id, seen_at FROM user_seen WHERE tg_id=?", (tg_id,)).fetchall()
        return {r["question_id"]: r["seen_at"] for r in rows}

    # ── المستخدمون ───────────────────────────────────────────
    def upsert_user(self, tg_id: int, name: str) -> None:
        with self.conn:
            self.conn.execute(
                """INSERT INTO users(tg_id,name,created_at) VALUES(?,?,?)
                   ON CONFLICT(tg_id) DO UPDATE SET name=excluded.name""",
                (tg_id, name, time.time()))

    def get_user(self, tg_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()

    # ── الجلسات ──────────────────────────────────────────────
    def active_session(self, tg_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM sessions WHERE tg_id=? AND state='active' ORDER BY id DESC LIMIT 1",
            (tg_id,)).fetchone()

    def get_session(self, sid: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()

    def last_finished_at(self, tg_id: int) -> float | None:
        r = self.conn.execute(
            "SELECT MAX(finished_at) m FROM sessions WHERE tg_id=? AND state='finished'",
            (tg_id,)).fetchone()
        return r["m"]

    def abandon_active(self, tg_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET state='abandoned' WHERE tg_id=? AND state='active'", (tg_id,))

    def create_session(self, tg_id: int, picked: list[tuple[Question, list[int], int]]) -> int:
        """picked: [(سؤال, ترتيب الخيارات, موضع الصحيح)]"""
        now = time.time()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO sessions(tg_id, started_at) VALUES(?,?)", (tg_id, now))
            sid = cur.lastrowid
            for pos, (q, order, cpos) in enumerate(picked):
                self.conn.execute(
                    """INSERT INTO session_questions(session_id,pos,question_id,level,option_order,correct_pos)
                       VALUES(?,?,?,?,?,?)""",
                    (sid, pos, q.id, q.level, json.dumps(order), cpos))
                self.conn.execute(
                    """INSERT INTO user_seen(tg_id,question_id,seen_at) VALUES(?,?,?)
                       ON CONFLICT(tg_id,question_id) DO UPDATE SET seen_at=excluded.seen_at""",
                    (tg_id, q.id, now))
        return sid

    def session_question(self, sid: int, pos: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM session_questions WHERE session_id=? AND pos=?", (sid, pos)).fetchone()

    def mark_sent(self, sid: int, pos: int, message_id: int | None = None) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE session_questions SET sent_at=COALESCE(sent_at, ?) WHERE session_id=? AND pos=?",
                (time.time(), sid, pos))
            if message_id is not None:
                self.conn.execute("UPDATE sessions SET message_id=? WHERE id=?", (message_id, sid))

    def record_answer(self, sid: int, pos: int, choice: int, timed_out: bool = False) -> bool | None:
        """يسجّل الإجابة مرة واحدة فقط. يرجع صحيحة/خاطئة، أو None إن كانت مسجّلة سابقًا."""
        row = self.session_question(sid, pos)
        if row is None or row["user_answer"] is not None:
            return None
        correct = (not timed_out) and choice == row["correct_pos"]
        now = time.time()
        time_ms = int((now - row["sent_at"]) * 1000) if row["sent_at"] else None
        with self.conn:
            self.conn.execute(
                """UPDATE session_questions SET user_answer=?, is_correct=?, time_ms=?
                   WHERE session_id=? AND pos=?""",
                (-1 if timed_out else choice, int(correct), time_ms, sid, pos))
            self.conn.execute(
                "UPDATE questions SET asked=asked+1, correct=correct+? WHERE id=?",
                (int(correct), row["question_id"]))
        return correct

    def advance(self, sid: int, new_pos: int) -> None:
        with self.conn:
            self.conn.execute("UPDATE sessions SET current_pos=? WHERE id=?", (new_pos, sid))

    def session_answers(self, sid: int) -> list[Answer]:
        rows = self.conn.execute(
            """SELECT sq.level, q.category, sq.is_correct FROM session_questions sq
               JOIN questions q ON q.id=sq.question_id
               WHERE sq.session_id=? ORDER BY sq.pos""", (sid,)).fetchall()
        return [Answer(r["level"], r["category"], bool(r["is_correct"])) for r in rows]

    def session_len(self, sid: int) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) n FROM session_questions WHERE session_id=?", (sid,)).fetchone()["n"]

    def finish_session(self, sid: int, tg_id: int, score: float, count_best: bool = True) -> None:
        """count_best=False للنتائج المشبوهة: تُسجَّل لكن لا ترفع أفضل نتيجة في المتصدرين."""
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET state='finished', finished_at=?, score=? WHERE id=?",
                (time.time(), score, sid))
            self.conn.execute(
                """UPDATE users SET tests_taken=tests_taken+1,
                   best_score=MAX(best_score, ?) WHERE tg_id=?""",
                (score if count_best else 0.0, tg_id))

    # ── الإحصائيات ───────────────────────────────────────────
    def percentile(self, score: float) -> float:
        """نسبة اللاعبين (بأفضل نتيجة) الذين تفوّق عليهم هذا التقييم."""
        r = self.conn.execute(
            """SELECT COUNT(*) n, SUM(best_score < ?) below FROM users WHERE tests_taken>0""",
            (score,)).fetchone()
        n, below = r["n"] or 0, r["below"] or 0
        return 100.0 * below / n if n > 1 else 100.0

    def leaderboard(self, limit: int = 10) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT name, best_score, tests_taken FROM users WHERE tests_taken>0
               ORDER BY best_score DESC, tests_taken ASC LIMIT ?""", (limit,)).fetchall()

    def user_rank(self, tg_id: int) -> int | None:
        u = self.get_user(tg_id)
        if not u or not u["tests_taken"]:
            return None
        r = self.conn.execute(
            "SELECT COUNT(*)+1 rk FROM users WHERE tests_taken>0 AND best_score > ?",
            (u["best_score"],)).fetchone()
        return r["rk"]

    def suspicious_questions(self, min_asked: int = 30) -> list[sqlite3.Row]:
        """أسئلة تُجاب قرابة التخمين (≈25%) أو أقل — غالبًا فيها خطأ أو غموض."""
        return self.conn.execute(
            """SELECT id, q, base_difficulty, asked, correct,
                      ROUND(100.0*correct/asked,1) AS pct FROM questions
               WHERE asked>=? AND 1.0*correct/asked <= 0.27 ORDER BY pct""", (min_asked,)).fetchall()

    def last_session_stats(self, tg_id: int):
        return self.conn.execute(
            "SELECT score, finished_at FROM sessions WHERE tg_id=? AND state='finished' "
            "ORDER BY id DESC LIMIT 5", (tg_id,)).fetchall()

    def fast_answer_ratio(self, sid: int, threshold_ms: int = 1000) -> float:
        r = self.conn.execute(
            """SELECT AVG(time_ms IS NOT NULL AND time_ms < ?) f FROM session_questions
               WHERE session_id=? AND user_answer IS NOT NULL""", (threshold_ms, sid)).fetchone()
        return r["f"] or 0.0
