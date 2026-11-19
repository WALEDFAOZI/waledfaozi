"""الاقتراحات والملاحظات: أنواع، حدود، ومراجعة الأدمن والرد."""
from harness import Harness, run


def cbs(h):
    return {b.callback_data for c in h.session.calls if getattr(c, "reply_markup", None) is not None
            for row in c.reply_markup.inline_keyboard for b in row}


def test_feedback_types_menu_submit_limits_and_admin_review_and_reply():
    async def go():
        h = Harness()
        u, o = h.user(1, "Ali"), h.user(5, "Boss")
        h.db.upsert_user(5, "Boss"); h.db.add_admin(5, owner=True)
        await h.tap(u, "sg")
        assert {"sg:f:feat", "sg:q", "sg:f:anime", "sg:f:bug", "sg:f:note"} <= cbs(h)
        # اقتراح لتطوير البوت
        await h.tap(u, "sg:f:feat")
        await h.say(u, "قصير")                                          # أقل من 10 أحرف
        assert h.db.feedback_counts() == {} and any("10 إلى 1000" in x for x in h.session.texts())
        await h.say(u, "أضيفوا لعبة تخمين الأوبننغ بالصوت")
        assert h.db.feedback_counts() == {"feat": 1}
        await h.tap(u, "sg:f:feat")
        await h.say(u, "أضيفوا لعبة تخمين الأوبننغ بالصوت")             # مكرر
        assert h.db.feedback_counts() == {"feat": 1} and any("نفس الرسالة" in x for x in h.session.texts())
        for kind, text in (("anime", "أرشح لكم أنمي Violet Evergarden لأنه جميل"), ("bug", "زر الترتيب يعلق عندما أضغط عليه"),
                           ("note", "شكرًا على البوت الرائع جدًا")):
            await h.tap(u, "sg")
            await h.tap(u, f"sg:f:{kind}")
            await h.say(u, text)
        assert h.db.feedback_counts() == {"feat": 1, "anime": 1, "bug": 1, "note": 1}
        await h.tap(u, "sg:f:note")
        await h.say(u, "ملاحظة خامسة للحد اليومي هنا")
        await h.tap(u, "sg:f:note")
        await h.say(u, "ملاحظة سادسة تتجاوز الحد اليومي")
        assert sum(h.db.feedback_counts().values()) == 5 and any("اليومي" in x for x in h.session.texts())
        # الأدمن: العدّاد في الرئيسية ثم النوع ثم الرسالة
        await h.say(o, "/admin")
        assert "الاقتراحات والملاحظات (5)" in str([c.reply_markup for c in h.session.calls if getattr(c, "chat_id", None) == 5][-1])
        await h.tap(o, "ad:fb")
        assert {"ad:fk:feat", "ad:fk:anime", "ad:fk:bug", "ad:fk:note", "ad:sg"} <= cbs(h)
        await h.tap(o, "ad:fk:bug")
        fid = h.db.feedback_list("bug")[0]["id"]
        await h.tap(o, f"ad:fv:{fid}")
        assert "زر الترتيب يعلق" in h.session.texts()[-1]
        await h.tap(o, f"ad:fr:{fid}")
        await h.say(o, "شكرًا، أصلحنا المشكلة")
        assert any("رد من الإدارة" in (getattr(c, "text", "") or "") and "أصلحنا" in c.text and c.chat_id == 1 for c in h.session.calls)
        assert "Boss" not in " ".join((getattr(c, "text", "") or "") for c in h.session.calls if getattr(c, "chat_id", None) == 1)
        assert h.db.get_feedback(fid)["status"] == "answered" and "bug" not in h.db.feedback_counts()
        # تمت
        fid2 = h.db.feedback_list("note")[0]["id"]
        await h.tap(o, f"ad:fd:{fid2}")
        assert h.db.get_feedback(fid2)["status"] == "done"
    run(go())


def test_old_suggest_command_still_asks_for_a_question_and_menu_label():
    async def go():
        h = Harness()
        u = h.user(1)
        await h.say(u, "/suggest")
        assert any("اقترح سؤالًا" in x or "5 أسطر" in x for x in h.session.texts())
        await h.say(u, "/start")
        from harness import last_menu_call
        labels = [b.text for row in last_menu_call(h).reply_markup.inline_keyboard for b in row]
        assert "💬 الاقتراحات والملاحظات" in labels
    run(go())
