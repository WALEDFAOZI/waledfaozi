"""الدعوات: تُحسب مرة واحدة بعد أول اختبار كامل للمدعو، ولا تُحسب للنفس."""
from harness import Harness, run


def test_invite_credited_after_first_full_test_once():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        inviter, friend = h.user(1), h.user(2)
        await h.say(inviter, "/start")
        await h.say(friend, "/start inv_1")
        assert h.db.get_user(2)["invited_by"] == 1 and h.db.invite_count(1) == 0
        await h.tap(friend, "go")
        await h.play(friend)
        assert h.db.invite_count(1) == 1
        assert any("أكمل أول اختبار" in x for x in h.session.texts())
        await h.tap(friend, "go")
        await h.play(friend)
        assert h.db.invite_count(1) == 1                       # لا تتكرر
        await h.tap(inviter, "iv")
        assert any("🌱" in x for x in h.session.texts())
    run(go())


def test_no_self_invite_and_old_users_not_attachable():
    async def go():
        h = Harness()
        a, b = h.user(1), h.user(2)
        await h.say(a, "/start inv_1")
        assert h.db.get_user(1)["invited_by"] is None
        await h.say(b, "/start")
        await h.say(b, "/start inv_1")                          # مستخدم قديم لا يُربط
        assert h.db.get_user(2)["invited_by"] is None
        await h.say(h.user(3), "/start inv_999")               # داعٍ غير موجود
        assert h.db.get_user(3)["invited_by"] is None
    run(go())


def test_leaving_channel_mid_quiz_blocks_every_button_until_back():
    async def go():
        h = Harness(channel="@Anime1Galaxy")
        h.session.member = True
        u = h.user(5)
        await h.say(u, "/start")
        await h.tap(u, "go")
        sid = h.db.active_session(5)["id"]
        row = h.db.session_question(sid, 0)
        await h.tap(u, f"a:{sid}:0:{row['correct_pos']}")
        assert h.db.session_question(sid, 0)["user_answer"] is not None
        h.session.member = False                         # غادر القناة
        import otaku_bot.bot as b
        h.ctx.subscribed.__closure__                      # مجرد تأكيد أنها مضبوطة
        for k in list(range(0)):
            pass
        # نبطل ذاكرة التحقق المؤقتة (30 ثانية) لمحاكاة مرور الوقت
        cell = [c.cell_contents for c in h.ctx.subscribed.__closure__ if isinstance(c.cell_contents, dict)]
        for d in cell:
            d.clear()
        before = h.db.session_question(sid, 1)["user_answer"]
        await h.tap(u, f"a:{sid}:1:0")
        assert h.db.session_question(sid, 1)["user_answer"] == before          # لم تُسجَّل الإجابة
        assert any("مشتركًا" in x or "اشترك" in x for x in h.session.texts())
        await h.tap(u, "m:games")                        # أي زر آخر أيضًا محجوب
        assert not any("ألعاب أخرى" in x for x in h.session.texts()[-1:])
        h.session.member = True
        for d in cell:
            d.clear()
        await h.tap(u, "chk")
        await h.tap(u, f"a:{sid}:1:0")
        assert h.db.session_question(sid, 1)["user_answer"] is not None
    run(go())
