"""إحصائيات الأدمن: مقسّمة إلى أقسام، وفيها عدد القنوات والمجموعات."""
from harness import Harness, run


def test_stats_menu_sections_and_chat_counts():
    async def go():
        h = Harness()
        h.db.add_admin(5, owner=True)
        o = h.user(5, "Owner")
        h.db.touch_group(-1001, "Group A")
        h.db.touch_group(-1002, "Group B")
        h.db.touch_group(-1003, "Channel C")
        h.db.link_channel(-1003, 5, "Channel C")               # القناة مسجّلة في الجدولين
        assert h.db.chat_counts() == {"channels": 1, "groups": 2}
        await h.tap(o, "ad:stats")
        assert "اختر القسم" in h.session.texts()[-1]
        await h.tap(o, "ad:sx:users")
        last = h.session.texts()[-1]
        assert "القنوات: <b>1</b>" in last and "المجموعات: <b>2</b>" in last
        await h.tap(o, "ad:sx:tests")
        assert "الاختبارات" in h.session.texts()[-1]
        await h.tap(o, "ad:sx:now")
        assert "التفاعل الآن" in h.session.texts()[-1]
    run(go())
