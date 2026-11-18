"""تقييم حسب الدولة (بالأزرار فقط، بدون موقع جغرافي)."""
from harness import Harness, last_menu_call, run
from otaku_bot import countries
from otaku_bot.texts import T


def cbs(call):
    return {b.callback_data for row in call.reply_markup.inline_keyboard for b in row}


def seed(h, rows):
    """rows: [(uid, name, country, best)]"""
    for uid, name, country, best in rows:
        h.db.upsert_user(uid, name)
        if country:
            h.db.set_country(uid, country)
        h.db.conn.execute("UPDATE users SET best_score=?, tests_taken=1 WHERE tg_id=?", (best, uid))


def test_pick_country_by_buttons_and_change():
    async def go():
        h = Harness()
        u = h.user(1, "Sara")
        await h.say(u, "/country")
        picker = last_menu_call(h)
        data = cbs(picker)
        assert {"cp:SA", "cp:EG", "cp:JP", "cp:XX", "cn:skip"} <= data and not any("loc" in d for d in data)
        assert max(len(r) for r in picker.reply_markup.inline_keyboard) == 3          # 3 أعمدة
        await h.tap(u, "cp:SA")
        assert h.db.get_country(1) == "SA"
        assert "السعودية" in h.session.texts()[-1] and {"cn:top", "cn:rank", "cn:set"} <= cbs(last_menu_call(h))
        await h.tap(u, "cn:set")
        await h.tap(u, "cp:EG")                                                         # تغيير
        assert h.db.get_country(1) == "EG"
        await h.tap(u, "cp:ZZ")                                                         # رمز غير موجود يُتجاهل
        assert h.db.get_country(1) == "EG"
        await h.tap(u, "cp:XX")
        assert h.db.get_country(1) == "XX" and "أخرى" in h.session.texts()[-1]
    run(go())


def test_country_leaderboard_and_countries_ranking():
    async def go():
        h = Harness()
        seed(h, [(1, "A1", "SA", 9.0), (2, "A2", "SA", 8.0), (3, "A3", "SA", 7.0), (4, "A4", "SA", 6.0),
                 (5, "E1", "EG", 9.5), (6, "E2", "EG", 5.0), (7, "E3", "EG", 5.0),
                 (8, "J1", "JP", 10.0), (9, "J2", "JP", 10.0),                      # يابانيان فقط: تحت الحد الأدنى
                 (10, "N1", None, 9.9)])
        db = h.db
        assert [r["name"] for r in db.country_players("SA")] == ["A1", "A2", "A3", "A4"]
        assert db.country_rank(3) == 3 and db.country_rank(10) is None
        board = db.countries_ranking(3, 5)
        assert [x["code"] for x in board] == ["SA", "EG"]                              # JP مستبعدة (لاعبان فقط)
        assert board[0]["score"] == 7.5 and board[0]["players"] == 4 and round(board[1]["score"], 2) == 6.5
        u = h.user(3, "A3")
        await h.tap(u, "cn:top")
        txt = h.session.texts()[-1]
        assert "السعودية" in txt and "A1" in txt and "ترتيبك في بلدك: #3" in txt.replace("<b>", "").replace("</b>", "")
        assert "E1" not in txt                                                           # لاعبو دولة أخرى لا يظهرون
        await h.tap(u, "cn:rank")
        txt = h.session.texts()[-1].replace("<b>", "").replace("</b>", "")
        assert txt.index("السعودية") < txt.index("مصر") and "اليابان" not in txt
        assert "السعودية: #1 بين الدول" in txt
        # بلا دولة: يعرض الاختيار
        await h.tap(h.user(10, "N1"), "cn:top")
        assert "cp:SA" in cbs(last_menu_call(h))
        # بالإنجليزية
        await h.tap(u, "lg:en")
        await h.tap(u, "cn:rank")
        assert "Countries ranking" in h.session.texts()[-1] and "Saudi Arabia" in h.session.texts()[-1]
    run(go())


def test_first_test_asks_country_once_and_skip_works():
    async def go():
        h = Harness()
        u = h.user(1, "Sara")
        await h.tap(u, "qk")
        await h.play(u)
        assert not any("cp:SA" in str(getattr(c, "reply_markup", "")) for c in h.session.calls)   # السريع لا يسأل
        await h.tap(u, "go")
        await h.play(u)
        asks = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.reply_markup is not None and "cp:SA" in str(c.reply_markup)]
        assert len(asks) == 1 and "من أي بلد" in asks[0].text
        await h.tap(u, "cn:skip")
        assert h.db.country_asked(1) and any(type(c).__name__ == "DeleteMessage" for c in h.session.calls)
        await h.tap(u, "go"); await h.play(u)                                                      # لا يسأل ثانية
        assert len([c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.reply_markup is not None and "cp:SA" in str(c.reply_markup)]) == 1
        # لاعب عنده دولة لا يُسأل
        h2 = Harness()
        v = h2.user(2, "Khalid")
        h2.db.upsert_user(2, "Khalid"); h2.db.set_country(2, "EG")
        await h2.tap(v, "go"); await h2.play(v)
        assert not any("cp:SA" in str(getattr(c, "reply_markup", "")) for c in h2.session.calls)
    run(go())


def test_profile_admin_stats_and_menus_mention_country():
    async def go():
        h = Harness(admin_ids=(5,))
        u = h.user(1, "Sara")
        await h.tap(u, "go"); await h.play(u)
        await h.tap(u, "cp:KW")
        h.db.conn.execute("UPDATE users SET best_score=8.0 WHERE tg_id=1")
        await h.tap(u, "pf")
        cap = [c for c in h.session.calls if type(c).__name__ == "SendPhoto" and c.caption and "ملف" in c.caption][-1].caption
        assert "الكويت" in cap and "ترتيبك فيه" in cap
        await h.tap(h.user(5), "ad:stats")
        assert "أكثر الدول" in h.session.texts()[-1] and "الكويت" in h.session.texts()[-1]
        await h.say(u, "/start")
        assert "cn:menu" in cbs(last_menu_call(h))
        await h.say(u, "/top")
        assert {"cn:top", "cn:rank"} <= cbs(last_menu_call(h))
    run(go())


def test_location_messages_are_ignored_not_stored():
    async def go():
        h = Harness()
        n = len(h.session.calls)
        await h.location(h.user(1), 24.71, 46.67)           # لا معالج للموقع: لا رد ولا تخزين
        assert len(h.session.calls) == n
        dump = "\n".join(h.db.conn.iterdump())
        assert "24.71" not in dump and "46.67" not in dump
    run(go())


def test_country_texts_parity_and_names():
    for k in T["ar"]:
        if k.startswith(("cn_", "prof_country")):
            assert k in T["en"], k
    assert all("loc" not in k for k in T["ar"] if k.startswith("cn_"))
    assert countries.label("SA", "en") == "🇸🇦 Saudi Arabia" and countries.label("XX", "ar") == "🌍 أخرى"
    assert len(countries.COUNTRIES) >= 28 and all(len(v) == 2 for v in countries.COUNTRIES.values())
