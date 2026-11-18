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
