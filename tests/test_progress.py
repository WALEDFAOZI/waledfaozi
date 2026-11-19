"""الخبرة والمستويات والإنجازات، تجميد السلسلة، الثأر، والعشائر."""
from harness import Harness, last_menu_call, run
from otaku_bot import progress


def cbs(h):
    return {b.callback_data for c in h.session.calls if getattr(c, "reply_markup", None) is not None
            for row in c.reply_markup.inline_keyboard for b in row}


def texts_to(h, uid):
    return [(getattr(c, "text", None) or getattr(c, "caption", None) or "") for c in h.session.calls
            if getattr(c, "chat_id", None) == uid]


def test_levels_xp_achievements_and_practice_cap():
    assert progress.level_of(0) == 1 and progress.level_of(50) == 2 and progress.level_of(200) == 3 and progress.level_of(4050) == 10
    assert progress.rank_of(1, "ar").startswith("مبتدئ") and progress.rank_of(30, "en").startswith("King")
    h = Harness()
    h.db.upsert_user(1, "Ali")
    s = progress.record(h.db, 1, "full", score=8.0, correct=30)
    assert s.xp >= 120 and h.db.stat(1, "tests") == 1
    keys = set(h.db.achievements_of(1))
    assert {"t1", "s5", "s7"} <= keys and "s9" not in keys             # إنجازات الاختبار الأول والتقييم
    assert s.level_up and any(a[1] == "أول اختبار كامل" for a in s.achs)
    again = progress.record(h.db, 1, "full", score=8.0, correct=30)
    assert not again.achs                                                 # لا يتكرر الإنجاز
    # سقف التدريب اليومي
    total = 0
    for _ in range(40):
        total += progress.record(h.db, 1, "quick", score=10, correct=10).xp
    assert h.db.xp_today(1, "practice") <= progress.PRACTICE_DAILY_CAP
    assert "🥇" not in progress.ach_list(h.db, 1, "ar") and "✅" in progress.ach_list(h.db, 1, "ar")


def test_full_test_shows_xp_profile_level_and_achievements_screen():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        u = h.user(1, "Ali")
        await h.tap(u, "go")
        await h.play(u)
        assert any("XP" in x for x in texts_to(h, 1))
        assert any("أول اختبار" in x for x in texts_to(h, 1))              # إشعار الإنجاز
        await h.tap(u, "pf")
        prof = [c for c in h.session.calls if type(c).__name__ in ("SendPhoto", "SendMessage") and "المستوى" in ((getattr(c, "caption", None) or getattr(c, "text", None) or ""))]
        assert prof and "pg:me" in cbs(h) and "tm:m" in cbs(h)
        await h.tap(u, "pg:me")
        assert "إنجازاتي" in h.session.texts()[-1] and "✅" in h.session.texts()[-1]
    run(go())


def test_streak_freeze_saves_a_missed_day_and_is_earned_every_week():
    h = Harness()
    h.db.upsert_user(1, "A")
    d = 20000
    for i in range(7):
        h.db.mark_streak(1, d + i)
    assert h.db.get_user(1)["streak"] == 7 and h.db.get_user(1)["freezes"] == 1       # أسبوع = تجميد
    assert h.db.current_streak(1, d + 8) == 7                                          # فاتك يوم: التجميد يحميها للعرض
    streak, grew = h.db.mark_streak(1, d + 8)
    assert (streak, grew) == (8, True) and h.db.last_freeze_event()[0] and h.db.get_user(1)["freezes"] == 0
    assert h.db.current_streak(1, d + 11) == 0                                         # يومان فائتان بلا تجميد: تنكسر
    streak, _ = h.db.mark_streak(1, d + 11)
    assert streak == 1
    h.db.upsert_user(2, "B")
    for i in range(21):
        h.db.mark_streak(2, d + i)
    assert h.db.get_user(2)["freezes"] == 3                                            # 3 أسابيع = 3 تجميدات
    for i in range(21, 35):
        h.db.mark_streak(2, d + i)
    assert h.db.get_user(2)["freezes"] == 3                                            # حدّ أقصى 3


def test_duel_rematch_invites_previous_opponent_after_creator_finishes():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await h.say(a, "/start"); await h.say(b, "/start")
        await h.tap(a, "du:new:q")
        await h.tap(a, "du:go:1")
        await h.play(a)
        await h.say(b, "/start du_1")
        await h.tap(b, "du:acc:1")
        await h.play(b, correct=False)
        assert "du:re:1" in cbs(h) and "du:re:2" in cbs(h)                  # كلٌّ يرى زر الثأر ضد الآخر
        assert h.db.stat(1, "duel_wins") == 1
        await h.tap(b, "du:re:1")                                              # بوب يطلب ثأرًا من علي
        d = h.db.get_duel(2)
        assert d["creator"] == 2 and d["target"] == 1
        inv = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == 1 and "ثأرًا" in (c.text or "")]
        assert inv and "du:acc:2" in {b.callback_data for row in inv[-1].reply_markup.inline_keyboard for b in row}   # الدعوة فورًا
    run(go())


def test_clans_create_join_leave_rank_and_admin_hidden():
    async def go():
        h = Harness()
        a, b, c3 = h.user(1, "Ali"), h.user(2, "Bob"), h.user(3, "Cy")
        for u in (a, b, c3):
            await h.say(u, "/start")
        h.db.upsert_user(9, "Owner"); h.db.add_admin(9, owner=True)
        await h.tap(a, "tm:m")
        assert {"tm:new", "tm:list"} <= cbs(h)
        await h.tap(a, "tm:new")
        await h.say(a, "ab")                                                     # قصير
        assert h.db.get_user(1)["team_id"] is None
        await h.say(a, "http://x.com")                                           # روابط ممنوعة
        assert h.db.get_user(1)["team_id"] is None
        await h.say(a, "نمور الأنمي")
        tid = h.db.get_user(1)["team_id"]
        assert tid and h.db.get_team(tid)["leader"] == 1
        await h.tap(b, "tm:new")
        await h.say(b, "نمور الأنمي")                                            # الاسم مستخدم
        assert h.db.get_user(2)["team_id"] is None
        await h.say(b, "/start tm_%d" % tid)                                     # رابط الدعوة
        assert any("دُعيت" in (getattr(c, "caption", None) or getattr(c, "text", None) or "") for c in h.session.calls)
        await h.tap(b, f"tm:j:{tid}")
        assert h.db.get_user(2)["team_id"] == tid and h.db.team_size(tid) == 2
        await h.tap(c3, f"tm:j:{tid}")
        await h.tap(h.user(9, "Owner"), f"tm:j:{tid}")                           # الأدمن لا ينضم
        assert h.db.get_user(9)["team_id"] is None
        # الخبرة تحدد الترتيب
        progress.record(h.db, 1, "full", score=9.0, correct=40)
        progress.record(h.db, 2, "full", score=5.0, correct=20)
        board = h.db.team_board(0.0)
        assert board[0]["id"] == tid and board[0]["pts"] > 0 and board[0]["members"] == 3
        await h.tap(a, "lb:T:w")
        assert "نمور الأنمي" in h.session.texts()[-1]
        # القائد يغادر فتنتقل القيادة لأعلى خبرة
        h.db.leave_team(1)
        assert h.db.get_user(1)["team_id"] is None and h.db.get_team(tid)["leader"] in (2, 3)
        # امتلاء العشيرة
        for i in range(10, 10 + h.db.TEAM_MAX):
            h.db.upsert_user(i, f"P{i}")
            h.db.join_team(i, tid)
        assert h.db.team_size(tid) == h.db.TEAM_MAX and h.db.join_team(1, tid) == "full"
        # الأدمن يخفي العشيرة ويُخرج أعضاءها
        await h.tap(h.user(9, "Owner"), f"ad:tmh:{tid}")
        assert h.db.get_user(2)["team_id"] is None and h.db.team_board(None) == []
        assert h.db.join_team(1, tid) == "gone"
    run(go())


def test_duel_share_link_comes_before_questions_and_friend_can_play_first():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await h.say(a, "/start"); await h.say(b, "/start")
        await h.tap(a, "du:new:q")
        calls = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == 1]
        share = calls[-1]
        urls = [x.url for row in share.reply_markup.inline_keyboard for x in row if x.url]
        assert urls and "t.me/share/url" in urls[0] and "start%3Ddu_1" in urls[0]     # الرابط أولًا
        assert "du:go:1" in {x.callback_data for row in share.reply_markup.inline_keyboard for x in row}
        assert not any(any((x.callback_data or "").startswith("a:") for row in c.reply_markup.inline_keyboard for x in row)
                       for c in calls if getattr(c, "reply_markup", None) is not None)   # لم يظهر أي سؤال بعد
        # الصديق يقبل ويلعب قبل أن يبدأ المضيف
        await h.say(b, "/start du_1")
        assert any("يتحداك" in (getattr(c, "caption", None) or getattr(c, "text", None) or "") for c in h.session.calls)
        await h.tap(b, "du:acc:1")
        await h.play(b, correct=False)
        assert any("ننتظر المضيف" in x for x in texts_to(h, 2))
        assert not any("نتيجة المواجهة" in x for x in texts_to(h, 1) + texts_to(h, 2))
        await h.tap(a, "du:go:1")                                              # الآن يلعب المضيف
        assert any(any((x.callback_data or "").startswith("a:") for row in c.reply_markup.inline_keyboard for x in row)
                   for c in h.session.calls if type(c).__name__ in ("SendMessage", "EditMessageText") and c.chat_id == 1
                   and getattr(c, "reply_markup", None) is not None)
        await h.play(a)
        for uid in (1, 2):
            assert any("نتيجة المواجهة" in x for x in texts_to(h, uid))            # النتيجة للطرفين عند انتهاء الثاني
        assert h.db.get_duel(1)["state"] == "done" and h.db.stat(1, "duel_wins") == 1
        await h.tap(b, "du:go:1")                                                # ليس مضيفًا: مرفوض
    run(go())
