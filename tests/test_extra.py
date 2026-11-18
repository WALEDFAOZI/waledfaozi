import json
import random
import sqlite3
import time
from collections import Counter
from pathlib import Path

from harness import QPATH, Harness, run
from otaku_bot import anilist
from otaku_bot.db import DB
from otaku_bot.games import load_games, new_state, order_correct, order_rounds, song_rounds
from otaku_bot.quiz import pick_questions

OLD_SCHEMA = """
CREATE TABLE questions(id INTEGER PRIMARY KEY, q TEXT NOT NULL, options TEXT NOT NULL, answer INTEGER NOT NULL,
  category TEXT NOT NULL, base_difficulty REAL NOT NULL, asked INTEGER NOT NULL DEFAULT 0,
  correct INTEGER NOT NULL DEFAULT 0, flagged INTEGER NOT NULL DEFAULT 0);
CREATE TABLE users(tg_id INTEGER PRIMARY KEY, name TEXT, best_score REAL NOT NULL DEFAULT 0,
  tests_taken INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL);
CREATE TABLE sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER NOT NULL, started_at REAL NOT NULL,
  finished_at REAL, score REAL, state TEXT NOT NULL DEFAULT 'active', current_pos INTEGER NOT NULL DEFAULT 0, message_id INTEGER);
CREATE TABLE session_questions(session_id INTEGER NOT NULL, pos INTEGER NOT NULL, question_id INTEGER NOT NULL,
  level INTEGER NOT NULL, option_order TEXT NOT NULL, correct_pos INTEGER NOT NULL, user_answer INTEGER,
  is_correct INTEGER, sent_at REAL, time_ms INTEGER, PRIMARY KEY(session_id, pos));
CREATE TABLE user_seen(tg_id INTEGER NOT NULL, question_id INTEGER NOT NULL, seen_at REAL NOT NULL, PRIMARY KEY(tg_id, question_id));
"""


def test_old_database_is_upgraded_without_losing_data(tmp_path):
    path = str(tmp_path / "old.db")
    c = sqlite3.connect(path)
    c.executescript(OLD_SCHEMA)
    c.execute("INSERT INTO questions(id,q,options,answer,category,base_difficulty,asked,correct) VALUES(1,'س','[\"a\",\"b\",\"c\",\"d\"]',0,'anime',3,40,10)")
    c.execute("INSERT INTO users(tg_id,name,best_score,tests_taken,created_at) VALUES(7,'Old',8.5,3,1)")
    c.execute("INSERT INTO sessions(tg_id,started_at,finished_at,score,state) VALUES(7,1,2,8.5,'finished')")
    c.commit()
    c.close()
    db = DB(path)
    db.load_questions(QPATH)                 # ملف الأسئلة الجديد يحدّث ولا يمسح الإحصائيات
    q = db.get_question(1)
    assert (q.asked, q.correct) == (40, 10)
    assert q.q_en and q.options_en
    u = db.get_user(7)
    assert u["best_score"] == 8.5 and u["lang"] == "ar" and u["best_sudden"] == 0
    s = db.conn.execute("SELECT mode, counted FROM sessions").fetchone()
    assert s["mode"] == "full" and s["counted"] == 1      # الجلسات القديمة تُحسب كاملة
    # وتشتغل ميزات الأسبوع على بيانات قديمة
    assert db.leaderboard()[0]["name"] == "Old"
    DB(path)                                               # فتح ثانٍ لا يكرّر الترقية ولا يفشل


def test_english_bank_is_complete_and_consistent():
    data = json.loads(Path(QPATH).read_text(encoding="utf-8"))
    assert all(d.get("q_en") and len(d["options_en"]) == 4 for d in data)
    for d in data:
        assert len(set(d["options_en"])) == 4
        assert 0 <= d["answer"] < 4
        # الجواب الصحيح في الإنجليزي في نفس الموضع، ولا يحوي حروفًا عربية
        assert not any("؀" <= ch <= "ۿ" for ch in d["q_en"] + "".join(d["options_en"])), d["id"]


def test_pick_is_category_diverse_within_level():
    db = DB(":memory:")
    db.load_questions(QPATH)
    qs = db.all_questions()
    worst = 0
    for seed in range(30):
        picked = pick_questions(qs, {}, random.Random(seed))
        for lv in range(1, 11):
            cats = Counter(q.category for q in picked if q.level == lv)
            worst = max(worst, max(cats.values()))
    assert worst <= 3          # لا يطغى تصنيف واحد (حد 2 مع استثناء نادر عند ضيق المستوى)


# ── الصور ───────────────────────────────────────────────
def fake_anilist_post(n_pages=5):
    chars, cid = [], 1
    for page in range(n_pages):
        page_chars = []
        for k in range(50):
            media = f"Show {cid // 6}"
            page_chars.append({"id": cid, "name": {"full": f"Hero Number{cid} Smith"},
                               "image": {"large": f"https://s4.anilist.co/c/{cid}.png"}, "favourites": 1000 - cid,
                               "media": {"nodes": [{"id": 1, "title": {"romaji": media, "english": None}}]}})
            cid += 1
        chars.append(page_chars)

    async def post(url, payload):
        return {"data": {"Page": {"characters": chars[payload["variables"]["page"] - 1]}}}
    return post


def test_anilist_questions_are_wellformed(monkeypatch):
    async def nosleep(_):
        return None
    monkeypatch.setattr(anilist.asyncio, "sleep", nosleep)
    qs, src = run(anilist.fetch_image_questions(limit=200, post=fake_anilist_post()))
    assert src == "AniList" and len(qs) >= 100
    ids = [q["id"] for q in qs]
    assert len(set(ids)) == len(ids) and all(i >= anilist.ANILIST_BASE for i in ids)
    for q in qs:
        assert len(set(q["options"])) == 4 and 0 <= q["answer"] < 4
        assert q["options"][q["answer"]].startswith("Hero Number")
        assert q["image"].startswith("https://") and q["category"] == "images"
        assert 1 <= q["base_difficulty"] <= 8
    # الاسم الصحيح يطابق صورة نفس الشخصية (نفس رقم الشخصية)
    by_id = {q["id"] - anilist.ANILIST_BASE: q for q in qs}
    for cid, q in by_id.items():
        assert q["image"].endswith(f"/{cid}.png")
        assert q["options"][q["answer"]] == f"Hero Number{cid} Smith"
    # الأشهر أسهل
    assert by_id[1]["base_difficulty"] <= by_id[max(by_id)]["base_difficulty"]


def test_jikan_fallback_and_name_cleanup(monkeypatch):
    async def nosleep(_):
        return None
    monkeypatch.setattr(anilist.asyncio, "sleep", nosleep)

    async def bad_post(url, payload):
        raise OSError("anilist blocked")

    async def get(url):
        page = int(url.rsplit("=", 1)[1])
        return {"data": [{"mal_id": page * 100 + i, "name": f"Name{page * 100 + i}, First{i}x",
                          "images": {"jpg": {"image_url": f"https://cdn.myanimelist.net/{page * 100 + i}.jpg"}}}
                         for i in range(25)]}
    qs, src = run(anilist.fetch_image_questions(post=bad_post, get=get))
    assert src == "Jikan"
    assert qs[0]["options"][qs[0]["answer"]].startswith("First")      # «Last, First» → «First Last»
    assert all(q["id"] >= anilist.JIKAN_BASE for q in qs)


def test_admin_image_fetch_then_category_mode_and_default_image_filtered(monkeypatch):
    async def go():
        import otaku_bot.admin as adm
        async def nosleep(_):
            return None
        monkeypatch.setattr(anilist.asyncio, "sleep", nosleep)
        h = Harness()
        h.db.add_admin(5, owner=True)
        owner = h.user(5)
        monkeypatch.setattr(adm, "fetch_post", fake_anilist_post())
        await h.tap(owner, "ad:img:go")
        assert any("سؤال صورة" in x for x in h.session.texts())
        assert h.db.category_counts()["images"] >= 100
        u = h.user(9)
        await h.tap(u, "ct:images")
        sid = h.db.active_session(9)["id"]
        assert h.db.get_session(sid)["mode"] == "category"
        assert any(type(c).__name__ == "SendPhoto" for c in h.session.calls)
    run(go())
    assert anilist._ok("Good Name", "https://x/y.png")
    assert not anilist._ok("Bad", "https://s4.anilist.co/file/anilistcdn/character/large/default.jpg")
    assert not anilist._ok("Bad", "http://insecure/x.png")


# ── الألعاب (المنطق الصافي) ─────────────────────────────
def test_game_rounds_are_valid():
    data = load_games()
    rng = random.Random(1)
    for _ in range(30):
        for rd in song_rounds(data, rng, 10):
            assert len(set(rd["options"])) == 4
            right = rd["options"][rd["answer"]]
            assert any(a == right for _, a in data["songs"])
        for rd in order_rounds(data, rng, 8):
            years = [it["year"] for it in rd["items"]]
            assert len(rd["items"]) == 4 and len(set(years)) == 4
            ordered = [years[i] for i in order_correct(rd)]
            assert ordered == sorted(years)
    st = new_state("tf", data, rng)
    assert len(st["rounds"]) == 10 and len(set(st["rounds"])) == 10
    # صح/غلط: كل عبارة فيها نسختان وشرح للخطأ
    for ar, en, ans, ex_ar, ex_en in data["tf"]:
        assert ar and en and isinstance(ans, bool)
        if not ans:
            assert ex_ar and ex_en
    assert 40 <= sum(1 for s in data["tf"] if s[2]) + sum(1 for s in data["tf"] if not s[2]) <= 60


def test_stats_and_settings_values_flow():
    h = Harness()
    db = h.db
    db.upsert_user(1, "A")
    sid = db.create_session(1, [(q, [0, 1, 2, 3], q.answer) for q in db.all_questions()[:50]])
    for pos in range(50):
        db.record_answer(sid, pos, 0)
    db.finish_session(sid, 1, 5.0)
    s = db.admin_stats()
    assert s["users"] == 1 and s["finished_total"] == 1 and s["avg_score"] == 5.0
    assert s["bank_en"] == s["bank_active"] == len(json.loads(Path(QPATH).read_text(encoding="utf-8")))
    assert db.get_setting("x", "d") == "d"
    db.set_setting("x", "1")
    assert db.get_setting("x") == "1"
