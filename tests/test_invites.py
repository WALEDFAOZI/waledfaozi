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
