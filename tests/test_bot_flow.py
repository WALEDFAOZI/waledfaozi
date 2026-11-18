"""اختبارات تكاملية للبوت كاملًا بدون تليجرام ولا توكن."""
import time
from dataclasses import replace

from aiogram.methods import SendPhoto

from harness import Harness, run, last_menu_call


def test_full_quiz_flow_and_result():
    async def go():
        h = Harness()
        u = h.user(1, "Waled")
        await h.say(u, "/start")
        await h.tap(u, "go")
        sid = await h.play(u)
        s = h.db.get_session(sid)
        assert s["state"] == "finished" and s["score"] == 10.0 and s["mode"] == "full"
        # كل الإجابات في أقل من ثانية = مشبوهة: لا ترفع أفضل نتيجة
        assert h.db.get_user(1)["best_score"] == 0
        kinds = [type(c).__name__ for c in h.session.calls]
        assert "SendPhoto" in kinds or kinds.count("SendMessage") >= 2
        assert kinds.count("AnswerCallbackQuery") == 51
    run(go())


def test_security_owner_only_and_single_answer():
    async def go():
        h = Harness()
        a, b = h.user(1), h.user(2)
        await h.tap(a, "go")
        sid = h.db.active_session(1)["id"]
        row = h.db.session_question(sid, 0)
        await h.tap(b, f"a:{sid}:0:{row['correct_pos']}")       # لص
        assert h.db.session_question(sid, 0)["user_answer"] is None
        await h.tap(a, f"a:{sid}:0:{row['correct_pos']}")
        assert h.db.session_question(sid, 0)["is_correct"] == 1
        await h.tap(a, f"a:{sid}:0:0")                           # زر قديم
        assert h.db.get_session(sid)["current_pos"] == 1
    run(go())


def test_forced_subscription_gate_and_fail_closed_and_diag():
    async def go():
        h = Harness(channel="@Anime1Galaxy")
        u = h.user(1)
        h.session.member = False
        await h.tap(u, "go")
        assert h.db.active_session(1) is None and "اشترك" in h.session.texts()[-1]
        await h.tap(u, "chk")
        assert h.db.active_session(1) is None
        h.session.member = True
        await h.tap(u, "chk")
        await h.tap(u, "go")
        assert h.db.active_session(1) is not None
        # تعذّر التحقق => يرفض ولا يفتح الباب
        h2 = Harness(channel="@Anime1Galaxy")
        h2.session.member = None
        await h2.tap(h2.user(1), "go")
        assert h2.db.active_session(1) is None and "تعذّر" in h2.session.texts()[-1]
        await h2.say(h2.user(1), "/diag")
        assert "لا يرى القناة" in h2.session.texts()[-1]
    run(go())


def test_quick_category_and_sudden_modes():
    async def go():
        h = Harness()
        u = h.user(1)
        await h.tap(u, "qk")
        sid = await h.play(u)
        s = h.db.get_session(sid)
        assert s["mode"] == "quick" and h.db.session_len(sid) == 10
        levels = [h.db.session_question(sid, p)["level"] for p in range(10)]
        assert levels == sorted(levels)
        assert h.db.get_user(1)["tests_taken"] == 0 and h.db.get_user(1)["best_score"] == 0   # لا تدخل المتصدرين
        assert "لا تدخل المتصدرين" in "\n".join(h.session.texts())

        await h.tap(u, "ct:characters")
        sid = await h.play(u)
        assert h.db.get_session(sid)["mode"] == "category" and h.db.session_len(sid) == 10
        cats = {h.db.get_question(h.db.session_question(sid, p)["question_id"]).category for p in range(10)}
        assert cats == {"characters"}

        # الموت المفاجئ: 3 صح ثم غلط
        await h.tap(u, "sd")
        sid = h.db.active_session(1)["id"]
        await h.play(u, correct=True, limit=3)
        await h.play(u, correct=False, limit=1)
        s = h.db.get_session(sid)
        assert s["state"] == "finished" and s["mode"] == "sudden"
        assert h.db.get_user(1)["best_sudden"] == 3
        assert h.db.sudden_leaderboard()[0]["best_sudden"] == 3
    run(go())


def test_cooldown_only_for_full_tests():
    async def go():
        h = Harness(cooldown=30)
        u = h.user(1)
        await h.tap(u, "go")
        await h.play(u)
        await h.tap(u, "go")
        assert h.db.active_session(1) is None and "دقيقة" in h.session.texts()[-1]
        await h.tap(u, "qk")                       # السريع غير مقيَّد
        assert h.db.active_session(1) is not None
    run(go())


def test_challenge_same_questions_and_comparison_dm():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await h.tap(a, "go")
        sid_a = await h.play(a, correct=True)
        await h.say(b, f"/start ch_{sid_a}")
        assert "تحداك" in h.session.texts()[-1]
        await h.tap(b, f"cc:{sid_a}")
        sid_b = h.db.active_session(2)["id"]
        qa = [q.id for q in h.db.session_questions_ordered(sid_a)]
        qb = [q.id for q in h.db.session_questions_ordered(sid_b)]
        assert qa == qb                                            # نفس الأسئلة بنفس الترتيب
        assert h.db.get_session(sid_b)["challenge_of"] == sid_a
        await h.play(b, correct=False)
        dm = [c for c in h.session.calls if getattr(c, "chat_id", None) == 1 and "قبل تحداك" in (getattr(c, "text", "") or "")]
        assert dm and "فزت" in dm[0].text
        assert "النتيجة مقابل" in "\n".join(h.session.texts())
        # لا يمكن قبول التحدي مرتين ولا تحدّي نفسك
        await h.tap(b, f"cc:{sid_a}")
        assert "سبق وخضت" in h.session.texts()[-1]
        await h.tap(a, f"cc:{sid_a}")
        assert "تحديك أنت" in h.session.texts()[-1]
    run(go())


def test_weekly_leaderboard_resets():
    from otaku_bot.timeutil import week_start
    h = Harness()
    db = h.db
    for uid, name, score, when in [(1, "A", 8.0, time.time()), (2, "B", 9.5, time.time()),
                                   (3, "Old", 10.0, week_start() - 86400)]:
        db.upsert_user(uid, name)
        sid = db.create_session(uid, [(q, [0, 1, 2, 3], q.answer) for q in db.all_questions()[:50]])
        db.finish_session(sid, uid, score)
        db.conn.execute("UPDATE sessions SET finished_at=? WHERE id=?", (when, sid))
    rows = db.weekly_leaderboard(week_start())
    assert [r["name"] for r in rows] == ["B", "A"]          # القديم خارج الأسبوع
    assert db.weekly_rank(1, week_start()) == 2


def test_reports_are_limited_and_reach_admin_only_at_threshold():
    async def go():
        h = Harness(admin_ids=(777,))
        h.db.set_setting("report_threshold", "2")
        users = [h.user(i) for i in (1, 2, 3)]
        sid_of = {}
        qid = None
        for u in users:
            await h.tap(u, "qk")
            sid = await h.play(u, correct=False)
            sid_of[u.id] = sid
        # سؤال مشترك: نبلغ عن أول سؤال أخطأ فيه كل مستخدم (قد يختلف) -> نجعلها نفس السؤال بتعديل الجلسات
        q = h.db.get_question(h.db.session_question(sid_of[1], 0)["question_id"])
        for u in users:
            h.db.conn.execute("UPDATE session_questions SET question_id=? WHERE session_id=? AND pos=0", (q.id, sid_of[u.id]))
        await h.tap(users[0], f"rr:{sid_of[1]}:0:0")
        assert h.db.open_report_count(q.id) == 1
        assert not [c for c in h.session.calls if getattr(c, "chat_id", None) == 777]   # لا إشعار قبل العتبة
        await h.tap(users[0], f"rr:{sid_of[1]}:0:1")                                    # تكرار نفس المستخدم
        assert h.db.open_report_count(q.id) == 1
        await h.tap(users[1], f"rr:{sid_of[2]}:0:0")
        assert h.db.open_report_count(q.id) == 2
        assert [c for c in h.session.calls if getattr(c, "chat_id", None) == 777]       # وصل المشرف عند العتبة
        # الحد اليومي
        h.db.set_setting("reports_per_day", "1")
        await h.tap(users[2], f"rr:{sid_of[3]}:0:0")
        await h.tap(users[2], f"rr:{sid_of[3]}:1:0")
        assert h.db.reports_today(3) == 1
        # لا يُبلَّغ إلا عن أسئلة أخطأ فيها نفسه
        await h.tap(users[0], f"rr:{sid_of[2]}:0:0")        # جلسة غيره
        assert h.db.reports_today(1) == 1
    run(go())


def test_english_language_flow():
    async def go():
        h = Harness()
        u = h.user(1, "Sam", lang="en")
        await h.say(u, "/start")
        assert h.db.get_lang(1) == "en" and "welcome aboard" in h.session.texts()[-1] and "Sam" in h.session.texts()[-1]
        await h.tap(u, "qk")
        txt = h.session.texts()[-1]
        assert "Question 1/10" in txt
        sid = h.db.active_session(1)["id"]
        q = h.db.get_question(h.db.session_question(sid, 0)["question_id"])
        assert q.q_en and q.q_en in txt.replace("&amp;", "&").replace("&lt;", "<")
        await h.tap(u, "lg:ar")
        assert h.db.get_lang(1) == "ar"
    run(go())


def test_image_questions_photo_flow_and_broken_image_skipped():
    async def go():
        h = Harness()
        db = h.db
        h.session.bad_photos = {"https://bad/2.png"}
        u = h.user(1)
        await h.tap(u, "go")
        sid = h.db.active_session(1)["id"]
        # أضف أسئلة الصور بعد سحب الجلسة حتى لا تقع عشوائيًا في مواضع أخرى
        db.add_question("من هذه؟", ["A", "B", "C", "D"], 0, "images", 1, image="https://good/1.png", q_en="Who?", options_en=["A", "B", "C", "D"])
        db.add_question("من هذه؟", ["E", "F", "G", "H"], 1, "images", 1, image="https://bad/2.png", q_en="Who?", options_en=["E", "F", "G", "H"])
        # اجبر الجلسة: السؤال 0 صورة سليمة، 1 صورة معطوبة
        qs = [q for q in db.all_questions() if q.image]
        good = next(q for q in qs if "good" in q.image)
        bad = next(q for q in qs if "bad" in q.image)
        for pos, q in ((0, good), (1, bad)):
            db.conn.execute("UPDATE session_questions SET question_id=?, option_order='[0,1,2,3]', correct_pos=? WHERE session_id=? AND pos=?",
                            (q.id, q.answer, sid, pos))
        db.conn.execute("UPDATE sessions SET current_pos=0, message_id=0 WHERE id=?", (sid,))
        h.session.calls.clear()
        from otaku_bot.bot import build_router  # noqa: F401
        # أعد عرض السؤال 0 عبر الاستئناف
        await h.tap(u, "resume")
        assert any(isinstance(c, SendPhoto) and c.photo == "https://good/1.png" for c in h.session.calls)
        await h.tap(u, f"a:{sid}:0:{good.answer}")             # يجيب ثم ينتقل للمعطوبة
        row1 = db.session_question(sid, 1)
        assert row1["user_answer"] == -2 and row1["is_correct"] is None     # تُخطّيت بلا احتساب
        assert db.get_session(sid)["current_pos"] == 2
        assert db.get_question(bad.id).asked == 0
        assert db.conn.execute("SELECT img_fail FROM questions WHERE id=?", (bad.id,)).fetchone()[0] == 1
        # الإجابات المحتسبة لا تشمل المتخطّاة
        assert len(db.session_answers(sid)) == 1
    run(go())


def test_games_flows():
    async def go():
        h = Harness()
        u = h.user(1)
        await h.say(u, "/games")
        assert "ألعاب" in h.session.texts()[-1]
        # صح/غلط: نجيب دائمًا بالصحيح
        from otaku_bot.games import load_games
        data = load_games()
        await h.tap(u, "g:tf")
        gid = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
        for _ in range(10):
            g = h.db.get_game(gid)
            s = data["tf"][g["state"]["rounds"][g["state"]["pos"]]]
            await h.tap(u, f"gt:{gid}:{int(s[2])}")
        g = h.db.get_game(gid)
        assert g["state"]["score"] == 10 and g["finished_at"]
        # أغنية
        await h.tap(u, "g:song")
        gid = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
        for _ in range(10):
            g = h.db.get_game(gid)
            rd = g["state"]["rounds"][g["state"]["pos"]]
            await h.tap(u, f"gs:{gid}:{rd['answer']}")
        assert h.db.get_game(gid)["state"]["score"] == 10
        # ترتيب
        from otaku_bot.games import order_correct
        await h.tap(u, "g:ord")
        gid = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
        for _ in range(8):
            g = h.db.get_game(gid)
            rd = g["state"]["rounds"][g["state"]["pos"]]
            for i in order_correct(rd):
                await h.tap(u, f"go:{gid}:{i}")
        g = h.db.get_game(gid)
        assert g["state"]["score"] == 8
        assert h.db.finish_game  # يحفظ أفضل نتيجة
        best = h.db.conn.execute("SELECT best FROM game_scores WHERE kind='ord'").fetchone()[0]
        assert best == 8
        # غيرك لا يلعب جولتك
        await h.tap(h.user(2), f"gt:{gid}:1")
    run(go())


def test_admin_claim_panel_add_edit_settings_stats_backup():
    async def go():
        h = Harness()
        h.ctx.claim_code = "abc123"
        owner, rando = h.user(5, "Owner"), h.user(6, "Rando")
        await h.say(rando, "/admin")
        assert not h.session.sent_to(6)                      # غير مشرف: لا يرى اللوحة
        await h.say(rando, "/claim wrong")
        assert not h.db.is_admin(6)
        await h.say(owner, "/claim abc123")
        assert h.db.is_owner(5) and h.ctx.claim_code is None
        await h.say(rando, "/claim abc123")                  # الكود لمرة واحدة
        assert not h.db.is_admin(6)
        await h.say(owner, "/admin")
        assert "لوحة التحكم" in h.session.texts()[-1]

        # إضافة سؤال بصورة عبر المعالج
        before = len(h.db.all_questions())
        await h.tap(owner, "ad:add")
        await h.photo(owner, "PHOTO123", caption="من هذه الشخصية؟")
        await h.say(owner, "نارuto\nساسكي\nساكورا\nكاكاشي")
        await h.tap(owner, "ad:aa:0")
        await h.tap(owner, "ad:ad:3")
        await h.tap(owner, "ad:ac:images")
        await h.tap(owner, "ad:ae:skip")
        added = [q for q in h.db.all_questions() if q.id >= 100000]
        assert len(h.db.all_questions()) == before + 1 and added[0].image == "tg:PHOTO123"
        assert added[0].category == "images" and added[0].base_difficulty == 3
        qid = added[0].id

        # تعديل نص + تعطيل + حذف
        await h.tap(owner, f"ad:e:{qid}:q")
        await h.say(owner, "نص معدّل")
        assert h.db.get_question(qid).q == "نص معدّل"
        await h.tap(owner, f"ad:t:{qid}")
        assert not h.db.get_question(qid).active
        await h.tap(owner, f"ad:x:{qid}")
        assert h.db.get_question(qid) is None

        # تعديل سؤال من الملف يبقى بعد إعادة التحميل (edited)
        await h.tap(owner, "ad:e:1:q")
        await h.say(owner, "معدّل من الأدمن")
        h.db.load_questions(__import__("harness").QPATH)
        assert h.db.get_question(1).q == "معدّل من الأدمن"
        await h.tap(owner, "ad:x:1")                          # أسئلة الملف لا تُحذف
        assert h.db.get_question(1) is not None

        # إعدادات
        await h.tap(owner, "ad:st:45")
        await h.tap(owner, "ad:cd:10")
        assert h.ctx.timer() == 45 and h.ctx.cooldown() == 10
        await h.tap(owner, "ad:ch")
        await h.say(owner, "@MyChannel")
        assert h.ctx.channel() == "@MyChannel"
        await h.tap(owner, "ad:ch")
        await h.say(owner, "تعطيل")
        assert h.ctx.channel() == ""

        # مشرفون
        await h.tap(owner, "ad:addadm")
        await h.say(owner, "6")
        assert h.db.is_admin(6) and not h.db.is_owner(6)
        await h.tap(h.user(6), "ad:adm")                      # غير المالك لا يدير المشرفين
        await h.tap(h.user(6), "ad:addadm")
        await h.say(h.user(6), "99")
        assert not h.db.is_admin(99)
        await h.tap(owner, "ad:rm:6")
        assert not h.db.is_admin(6)

        # إحصائيات ونسخة احتياطية
        await h.tap(owner, "ad:stats")
        assert "إحصائيات البوت" in h.session.texts()[-1]
        await h.tap(owner, "ad:bak")
        assert any(type(c).__name__ == "SendDocument" for c in h.session.calls)
    run(go())


def test_admin_fetch_images_ok_and_failure_messages():
    async def go():
        import otaku_bot.admin as adm
        h = Harness()
        h.db.add_admin(5, owner=True)
        owner = h.user(5)

        async def fail(*a, **k):
            raise OSError("blocked")
        old = (adm.fetch_post, adm.fetch_get)
        adm.fetch_post = adm.fetch_get = fail
        try:
            await h.tap(owner, "ad:img:go")
        finally:
            adm.fetch_post, adm.fetch_get = old
        assert any("فشل الجلب" in x for x in h.session.texts())
    run(go())


def test_start_menu_shows_all_player_buttons_and_each_works():
    async def go():
        h = Harness()
        u = h.user(1, "Waled")
        await h.say(u, "/start")
        start_call = last_menu_call(h)
        data = {b.callback_data for row in start_call.reply_markup.inline_keyboard for b in row}
        for must in ("go", "qk", "cats", "m:games", "an:m", "lb:all", "lb:week", "pf", "iv", "m:more"):
            assert must in data, must
        await h.tap(u, "m:games")
        gd = {b.callback_data for row in last_menu_call(h).reply_markup.inline_keyboard for b in row}
        assert {"sd", "g:tf", "g:song", "g:ord", "g:char", "g:quote"} <= gd
        await h.tap(u, "m:more")
        md = {b.callback_data for row in last_menu_call(h).reply_markup.inline_keyboard for b in row}
        assert {"st", "sg", "lg:toggle"} <= md
        # كل زر يشتغل فعلًا
        for cb in ("noop", "st", "lb:all", "lb:week", "lb:sd", "cats", "g:tf", "g:song", "g:ord", "menu"):
            before = len(h.session.calls)
            await h.tap(u, cb)
            assert len(h.session.calls) > before, cb
        await h.tap(u, "qk")
        assert h.db.active_session(1) is not None
        # بعد وجود أسئلة صور تظهر لها خانة في القائمة
        for i in range(12):
            h.db.add_question(f"من؟{i}", ["a", "b", "c", "d"], 0, "images", 1, image=f"https://x/{i}.png",
                              q_en="Who?", options_en=["a", "b", "c", "d"])
        await h.say(h.user(2, "B"), "/start")
        await h.tap(h.user(2, "B"), "m:games")
        c2 = last_menu_call(h)
        assert "ct:images" in {b.callback_data for row in c2.reply_markup.inline_keyboard for b in row}
    run(go())
