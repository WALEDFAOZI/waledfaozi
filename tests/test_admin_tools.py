"""أدوات الأدمن الجديدة: بحث المستخدمين، المنع من الألعاب، تشغيل/إيقاف الألعاب."""
from harness import Harness, run
from otaku_bot import arcade as A


def test_user_search_profile_ban_and_game_switch():
    async def go():
        A.queue["xo"].clear(); A.user_match.clear()
        h = Harness()
        h.db.add_admin(5, owner=True)
        o = h.user(5, "Owner")
        target = h.user(41, "Sara")
        for u in (target,):
            h.db.upsert_user(u.id, u.first_name)
        # بحث بالاسم ثم فتح الملف
        await h.tap(o, "ad:us")
        await h.say(o, "Sara")
        assert "ad:uv:41" in str(h.session.calls[-1].reply_markup)
        await h.tap(o, "ad:uv:41")
        assert "Sara" in h.session.texts()[-1] and "🎲 الألعاب: ✅ مسموح" in h.session.texts()[-1]
        # منع من الألعاب: لا يدخل الطابور
        await h.tap(o, "ad:ub:41:1")
        assert h.db.game_banned(41)
        await h.tap(target, "ar:q:xo")
        assert not A.queue["xo"]
        await h.tap(o, "ad:ub:41:0")
        assert not h.db.game_banned(41)
        # إيقاف لعبة من الألعاب المتاحة
        await h.tap(o, "ad:gt:arcade")
        assert h.db.game_on("arcade") is False
        await h.tap(target, "ar:q:xo")
        assert not A.queue["xo"]
        await h.tap(o, "ad:gt:arcade")                        # إعادة التشغيل
        assert h.db.game_on("arcade") is True
        await h.tap(target, "ar:q:xo")
        assert A.queue["xo"] == [41]
        A.queue["xo"].clear()
    run(go())
