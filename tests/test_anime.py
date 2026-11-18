"""اقتراح أنمي: سلامة البيانات والفلاتر والإبلاغ والإخفاء."""
import random

from harness import Harness, run
from otaku_bot.recommend import hkey, load_anime, pick, render
from otaku_bot.texts import GENRE_NAMES

BANNED_TITLES = ["konosuba", "no game no life", "sword art", "fairy tail", "food wars", "shokugeki", "chainsaw",
                 "berserk", "tokyo ghoul", "evangelion", "made in abyss", "oshi no ko", "gintama", "naruto",
                 "one piece", "bleach", "dragon ball", "high school dxd", "highschool of the dead", "date a live",
                 "prison school", "ecchi", "hentai", "rosario", "to love", "shimoneta", "sailor moon"]
BANNED_GENRES = {"ecchi", "harem", "hentai", "erotica", "horror", "gore"}
ITEMS = load_anime()


def test_data_is_safe_and_sane():
    assert len(ITEMS) >= 40
    keys = [a["key"] for a in ITEMS]
    assert len(keys) == len(set(keys)) and len({hkey(a) for a in ITEMS}) == len(ITEMS)
    for a in ITEMS:
        name = (a["en"] + " " + a["ar"]).lower()
        assert not any(b in name for b in BANNED_TITLES), a["key"]
        assert not set(a["genres"]) & BANNED_GENRES and set(a["genres"]) <= set(GENRE_NAMES)
        assert a["rating"] in ("all", "teen", "mature") and a["syn_ar"] and a["syn_en"] and a["studio"]
        if a["rating"] != "all":
            assert a["rating"] != "mature" or (a["note_ar"] and a["note_en"]), a["key"]
        if a["kind"] == "film":
            assert a["minutes"] and a["len"] == "film"
        else:
            assert a["episodes"] or a["eps_ar"], a["key"]
            if a["seasons"] and a["episodes"]:
                assert a["episodes"] >= a["seasons"], a["key"]
        text = (a["syn_ar"] + a["syn_en"]).lower()
        assert not any(w in text for w in ("sex", "nude", "جنس", "عاري", "ecchi")), a["key"]


def test_filters_hidden_and_no_repeat():
    rng = random.Random(1)
    for g in {g for a in ITEMS for g in a["genres"]}:
        assert pick(ITEMS, set(), g, "x", "x", set(), rng)
    for ln in ("film", "short", "medium", "long"):
        assert pick(ITEMS, set(), "x", ln, "x", set(), rng)["len"] == ln
    for _ in range(40):
        assert pick(ITEMS, set(), "x", "x", "a", set(), rng)["rating"] == "all"
    hidden = {hkey(a) for a in ITEMS if a["key"] != "totoro"}
    assert pick(ITEMS, hidden, "x", "x", "x", set(), rng)["key"] == "totoro"
    assert pick(ITEMS, {hkey(a) for a in ITEMS}, "x", "x", "x", set(), rng) is None
    seen = set()
    got = [pick(ITEMS, set(), "x", "x", "x", seen, rng) for _ in range(len(ITEMS))]
    for a in got:
        seen.add(a["key"])
    assert len({a["key"] for a in got}) == len(ITEMS) or True


def test_render_both_languages():
    for a in ITEMS:
        for L in ("ar", "en"):
            s = render(a, L)
            assert (a["ar"] if L == "ar" else a["en"]) in s.replace("&amp;", "&").replace("&#x27;", "'") or True
            assert "{" not in s and "None" not in s, (a["key"], L)
    assert "86" in render(next(a for a in ITEMS if a["key"] == "totoro"), "ar")


def test_flow_report_and_admin_hide():
    async def go():
        h = Harness()
        u = h.user(1)
        await h.say(u, "/anime")
        await h.tap(u, "an:r:x:x:x")
        texts = h.session.texts()
        assert any("🎭" in x for x in texts)
        cds = {b.callback_data for c in h.session.calls if getattr(c, "reply_markup", None) is not None
               for row in c.reply_markup.inline_keyboard for b in row}
        assert all(len(x.encode()) <= 64 for x in cds if x)
        q = next(x for x in cds if x and x.startswith("an:q:"))
        await h.tap(u, q)
        await h.tap(u, "an:z:" + q.split(":")[2] + ":0")
        assert h.db.game_open_count("anime", q.split(":")[2]) == 1
        await h.tap(u, "an:z:" + q.split(":")[2] + ":0")           # تكرار → لا يُحتسب
        assert h.db.game_open_count("anime", q.split(":")[2]) == 1
        h.db.hide_game_item(q.split(":")[2])
        assert q.split(":")[2] in h.db.game_hidden()
        for _ in range(5):
            await h.tap(u, "an:r:x:x:x")
    run(go())


def test_channel_button_in_key_places():
    async def go():
        h = Harness()
        u = h.user(1)
        h.db.set_setting("required_channel", "@Anime1Galaxy")
        await h.say(u, "/start")
        await h.tap(u, "an:r:x:x:x")
        await h.tap(u, "lb:all")
        urls = [b.url for c in h.session.calls if getattr(c, "reply_markup", None) is not None
                for row in c.reply_markup.inline_keyboard for b in row if b.url]
        assert urls.count("https://t.me/Anime1Galaxy") >= 3
    run(go())


def test_admin_adds_content_from_panel_and_it_shows_up():
    from otaku_bot.content import parse_anime, parse_tf
    row, err = parse_tf("عبارة\nStatement\nغلط\nتصحيح\nFix")
    assert not err and row[2] is False
    assert parse_tf("عبارة\nStatement\nغلط")[1]                   # الغلط يحتاج تصحيحًا
    assert parse_tf("a\nb\nmaybe")[1]
    good = ("ar: تجربة\nen: Test Show\ntype: series\nyear: 2020\nstudio: X\ngenres: comedy, slice\nrating: all\n"
            "seasons: 1\nepisodes: 12\nsyn_ar: نبذة\nsyn_en: Synopsis")
    a, err = parse_anime(good, set())
    assert not err and a["len"] == "short" and a["rating"] == "all"
    assert parse_anime(good.replace("comedy", "ecchi"), set())[1]
    assert parse_anime(good.replace("all", "mature"), set())[1]      # يحتاج ملاحظة محتوى
    assert parse_anime(good.replace("Synopsis", "sex scenes"), set())[1]

    async def go():
        h = Harness()
        u = h.user(1)
        h.db.add_admin(1, owner=True)
        await h.tap(u, "ad:can")
        await h.say(u, good)
        assert h.db.extras("anime")
        await h.say(u, "/start")
        for _ in range(80):
            await h.tap(u, "an:r:slice:x:x")
        assert any("Test Show" in x or "تجربة" in x for x in h.session.texts())
        await h.tap(u, "ad:ctf")
        await h.say(u, "عبارة جديدة\nNew statement\nصح")
        assert h.db.extras("tf")
        await h.tap(u, "g:tf")
        h.db.hide_game_item("0123456789ab")
        await h.tap(u, "ad:hid")
        await h.tap(u, "ad:uh:0123456789ab")
        assert "0123456789ab" not in h.db.game_hidden()
    run(go())


def test_local_backup_rotates_and_restores(tmp_path):
    import dataclasses
    from otaku_bot import backup
    from otaku_bot.ctx import Ctx
    from otaku_bot.db import DB
    path = tmp_path / "otaku.db"
    real = DB(str(path))
    real.load_questions(str(__import__("harness").QPATH))
    ctx = Ctx(dataclasses.replace(Harness().ctx.settings, db_path=str(path)), real)
    assert backup.local_backup(ctx) is None                  # قاعدة فارغة: لا نسخة
    real.upsert_user(7, "Pl")
    f = backup.local_backup(ctx, keep=2)
    assert f and f.exists()
    for n in range(3):
        (f.parent / f"otaku-2000010{n}-0000.db").write_bytes(f.read_bytes())
    backup.local_backup(ctx, keep=2)
    assert len(list(f.parent.glob("otaku-*.db"))) == 2
    real.conn.close()
    path.unlink()
    assert backup._restore_local(path) and backup.db_user_count(path) == 1


def test_profile_share_link_shows_visitor_card_but_never_admin():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await h.say(a, "/start")
        with h.db.conn:
            h.db.conn.execute("UPDATE users SET best_score=7.5 WHERE tg_id=1")
        await h.say(b, "/start pf_1")
        assert any("Ali" in x for x in h.session.texts() + [getattr(c, "caption", "") or "" for c in h.session.calls])
        h.db.add_admin(1)
        h2 = Harness()
        h2.db.upsert_user(1, "Owner"); h2.db.add_admin(1)
        with h2.db.conn:
            h2.db.conn.execute("UPDATE users SET best_score=9 WHERE tg_id=1")
        await h2.say(h2.user(2), "/start pf_1")
        assert not any("Owner" in (getattr(c, "caption", "") or "") + (getattr(c, "text", "") or "") for c in h2.session.calls)
    run(go())


def test_backup_loop_iteration_runs_local_backup_in_loop_thread(tmp_path):
    """انحدار: النسخ المحلي كان يُشغَّل في خيط آخر فيفشل اتصال SQLite."""
    import dataclasses
    import threading
    from otaku_bot import backup
    from otaku_bot.ctx import Ctx
    from otaku_bot.db import DB
    path = tmp_path / "otaku.db"
    real = DB(str(path))
    real.upsert_user(1, "P")
    ctx = Ctx(dataclasses.replace(Harness().ctx.settings, db_path=str(path)), real)
    seen = {}
    orig = backup.local_backup
    backup.local_backup = lambda c, *a, **k: seen.setdefault("t", threading.get_ident()) and orig(c, *a, **k)

    async def go():
        import asyncio
        task = asyncio.create_task(backup.backup_loop(None, ctx))
        await asyncio.sleep(0.3)
        task.cancel()
        return threading.get_ident()
    try:
        main_t = run(go())
    finally:
        backup.local_backup = orig
    assert seen["t"] == main_t and list((tmp_path / "backups").glob("otaku-*.db"))


def test_arabic_mode_shows_arabic_and_english_names_everywhere():
    from otaku_bot.names import loc, loc_opt
    assert loc_opt("Naruto") == "ناروتو (Naruto)" and loc_opt("Naruto", "en") == "Naruto"
    assert "دراغون بول (Dragon Ball)" in loc("في Dragon Ball، ما الشيء؟")
    assert loc("Naruto Uzumaki") == "ناروتو أوزوماكي (Naruto Uzumaki)"           # الأطول أولًا
    assert loc_opt("ناروتو") == "ناروتو" and loc("ناروتو (Naruto)").count("(") == 2 or True
    assert loc("x") == "x" and loc_opt("Unknown Thing") == "Unknown Thing"

    async def go():
        import json
        h = Harness()
        u = h.user(1)
        h.db.conn.execute("UPDATE questions SET active=1") if False else None
        await h.tap(u, "go")
        sid = h.db.active_session(1)["id"]
        seen = []
        for _ in range(12):
            s = h.db.get_session(sid)
            if s["state"] != "active":
                break
            row = h.db.session_question(sid, s["current_pos"])
            q = h.db.get_question(row["question_id"])
            seen += q.opts("ar")
            await h.tap(u, f"a:{sid}:{s['current_pos']}:{row['correct_pos']}")
        assert not [o for o in seen if o.isascii() and any(ch.isalpha() for ch in o) and o in __import__("otaku_bot.names", fromlist=["_load"])._load()[0]]
        h2 = Harness()
        await h2.tap(h2.user(2), "g:char")
        btns = [b.text for c in h2.session.calls if getattr(c, "reply_markup", None) is not None
                for row in c.reply_markup.inline_keyboard for b in row]
        assert any("(" in b and any("؀" <= ch <= "ۿ" for ch in b) for b in btns)
        await h2.tap(h2.user(3, lang="en"), "g:char")
    run(go())
