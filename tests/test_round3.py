"""إيقاف/إلغاء أي اختبار، التقييم العام، الملف الشخصي، قياس نمو القناة."""
import time

from harness import Harness, run, last_menu_call
from otaku_bot import growth


def cb_data(h, n=-1):
    c = [x for x in h.session.calls if getattr(x, "reply_markup", None) is not None][n]
    return {b.callback_data for row in c.reply_markup.inline_keyboard for b in row}


# ── إيقاف/إلغاء ─────────────────────────────────────────
def test_stop_needs_confirmation_then_cancels_any_mode_and_is_not_counted():
    async def go():
        h = Harness(cooldown=30)
        u = h.user(1)
        for start in ("go", "qk", "sd", "ct:characters"):
            await h.tap(u, start)
            sid = h.db.active_session(1)["id"]
            await h.play(u, limit=2)
            await h.tap(u, f"stop:{sid}")                       # يطلب تأكيدًا
            assert "تلغي الاختبار" in h.session.texts()[-1]
            assert h.db.get_session(sid)["state"] == "active"   # لم يُلغَ بعد
            assert f"sty:{sid}" in cb_data(h) and f"stn:{sid}" in cb_data(h)
            await h.tap(u, f"stn:{sid}")                         # لا، أكمل
            assert h.db.get_session(sid)["state"] == "active"
            assert "السؤال 3" in h.session.texts()[-1] or "Question 3" in h.session.texts()[-1]
            await h.tap(u, f"stop:{sid}")
            await h.tap(u, f"sty:{sid}")                         # نعم، ألغِ
            s = h.db.get_session(sid)
            assert s["state"] == "abandoned" and s["score"] is None
            # أزرار السؤال القديم لم تعد تعمل
            row = h.db.session_question(sid, s["current_pos"])
            before = len(h.session.calls)
            await h.tap(u, f"a:{sid}:{s['current_pos']}:{row['correct_pos']}")
            assert h.db.session_question(sid, s["current_pos"])["user_answer"] is None
        u_row = h.db.get_user(1)
        assert u_row["tests_taken"] == 0 and u_row["best_score"] == 0 and h.db.last_finished_at(1) is None
        await h.tap(u, "go")                                     # الإلغاء لا يفعّل فترة الانتظار
        assert h.db.active_session(1) is not None
    run(go())


def test_stop_buttons_are_owner_only():
    async def go():
        h = Harness()
        a, b = h.user(1), h.user(2)
        await h.tap(a, "go")
        sid = h.db.active_session(1)["id"]
        await h.tap(b, f"stop:{sid}")
        await h.tap(b, f"sty:{sid}")
        assert h.db.get_session(sid)["state"] == "active"
    run(go())


def test_stop_command_cancels_quiz_game_and_pending_input():
    async def go():
        h = Harness()
        u = h.user(1)
        await h.say(u, "/stop")
        assert "ما عندك شيء" in h.session.texts()[-1]
        await h.tap(u, "go")
        await h.tap(u, "g:tf")
        await h.tap(u, "sg")                                       # يبدأ إدخال اقتراح
        sid = h.db.active_session(1)["id"]
        gid = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
        await h.say(u, "/stop")
        txt = h.session.texts()[-1]
        assert "الاختبار" in txt and "اللعبة" in txt and "الإدخال" in txt
        assert h.db.get_session(sid)["state"] == "abandoned"
        assert h.db.get_game(gid)["finished_at"] is not None
        assert h.db.active_session(1) is None
        n = len(h.session.calls)
        await h.say(u, "كلام عادي")                                # لم يعد في وضع الاقتراح
        assert len(h.session.calls) == n
        await h.tap(u, "go")
        await h.say(u, "/cancel")                                  # /cancel نفس /stop
        assert h.db.active_session(1) is None
    run(go())


def test_admin_cancel_also_stops_quiz():
    async def go():
        h = Harness()
        h.db.add_admin(5, owner=True)
        o = h.user(5)
        await h.tap(o, "go")
        await h.tap(o, "ad:find")
        await h.say(o, "/cancel")
        assert h.db.active_session(5) is None
        n = len(h.session.calls)
        await h.say(o, "999")
        assert len(h.session.calls) == n
    run(go())


def test_game_stop_button_ends_without_score():
    async def go():
        h = Harness()
        u = h.user(1)
        for kind in ("tf", "song", "ord", "char", "quote"):
            await h.tap(u, f"g:{kind}")
            gid = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
            assert f"gx:{gid}" in cb_data(h)
            await h.tap(u, f"gx:{gid}")
            g = h.db.get_game(gid)
            assert g["finished_at"] is not None and g["score"] is None
            assert "وقفنا اللعبة" in h.session.texts()[-1]
            await h.tap(u, f"gt:{gid}:1")                          # زر قديم
            await h.tap(u, f"gs:{gid}:0")
        assert h.db.conn.execute("SELECT COUNT(*) FROM game_scores").fetchone()[0] == 0
        await h.tap(h.user(2), f"gx:{gid}")                        # غير صاحبها
    run(go())


# ── التقييم العام (أفضل 10) ─────────────────────────────
def test_general_rating_top10_is_separate_from_weekly():
    async def go():
        from otaku_bot.timeutil import week_start
        h = Harness()
        db = h.db
        for i in range(1, 13):
            db.upsert_user(i, f"P{i}")
            sid = db.create_session(i, [(q, [0, 1, 2, 3], q.answer) for q in db.all_questions()[:50]])
            db.finish_session(sid, i, float(i) / 1.5)               # P12 الأعلى = 8.0
            when = time.time() if i <= 4 else week_start() - 86400   # الأربعة الأوائل فقط هذا الأسبوع
            db.conn.execute("UPDATE sessions SET finished_at=? WHERE id=?", (when, sid))
        u = h.user(99)
        await h.say(u, "/top")
        txt = h.session.texts()[-1]
        assert "العام" in txt and "الاختبار" in txt
        lines = [l for l in txt.splitlines() if "P" in l and "—" in l]
        assert len(lines) == 10 and "P12" in lines[0] and "P3" in lines[-1] and "P2 " not in txt
        await h.say(u, "/weekly")
        wk = h.session.texts()[-1]
        assert "الأسبوعي" in wk
        wk_lines = [l for l in wk.splitlines() if "P" in l and "—" in l]
        assert len(wk_lines) == 4 and "P4" in wk_lines[0]            # الأسبوعي لا يضم القدامى
        assert {"lb:B:a:q", "lb:B:w:q", "lb:B:d:q", "lb:menu", "lb:P:w"} <= cb_data(h)
        await h.say(u, "/start")
        menu = last_menu_call(h)
        labels = [b.text for row in menu.reply_markup.inline_keyboard for b in row]
        assert any("الترتيب" in x for x in labels) and not any("تقييم الأسبوع" in x for x in labels)   # زر واحد في القائمة
        tabs = {b.text for row in last_menu_call(h).reply_markup.inline_keyboard for b in row}
        await h.tap(u, "lb:all")
        tabs = [b.text for c in h.session.calls if getattr(c, "reply_markup", None) is not None
                for row in c.reply_markup.inline_keyboard for b in row]
        assert any("العام" in x for x in tabs) and any("الأسبوع" in x for x in tabs)
        await h.tap(u, "lg:en")
        await h.say(u, "/top")
        assert "Overall" in h.session.texts()[-1] and "Test" in h.session.texts()[-1]
    run(go())


# ── الملف الشخصي ────────────────────────────────────────
def test_profile_card_for_player_and_fallback(monkeypatch):
    async def go():
        h = Harness()
        u = h.user(1, "Waled")
        await h.say(u, "/profile")
        assert "ما أخذت أي اختبار" in h.session.texts()[-1]
        await h.tap(u, "go")
        await h.play(u, correct=True)
        h.db.conn.execute("UPDATE users SET best_score=8.7, best_sudden=9 WHERE tg_id=1")
        await h.tap(u, "pf")
        photos = [c for c in h.session.calls if type(c).__name__ == "SendPhoto" and c.caption and "ملف" in c.caption]
        cap = photos[-1].caption.replace("<b>", "").replace("</b>", "")
        assert photos and "أفضل تقييم: 8.7/10" in cap and "ترتيبك العام: #1" in cap
        assert "دقتك الكلية: 100%" in cap and "أقوى تصنيفاتك" in cap
        assert any("share/url" in (b.url or "") for row in photos[-1].reply_markup.inline_keyboard for b in row)
        prof = h.db.user_profile(1)
        assert prof["answers"] == 50 and prof["correct"] == 50 and 1 <= len(prof["cats"]) <= 3
        # بالإنجليزية
        await h.tap(u, "lg:en")
        await h.say(u, "/profile")
        ph = [c for c in h.session.calls if type(c).__name__ == "SendPhoto"][-1]
        assert "profile" in ph.caption.lower() and "Best score" in ph.caption.replace("<b>", "").replace("</b>", "")
        # إذا تعذّرت البطاقة: يرسل نصًا فقط
        from otaku_bot import card
        monkeypatch.setattr(card, "make_profile_card", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no font")))
        n_photos = sum(1 for c in h.session.calls if type(c).__name__ == "SendPhoto")
        await h.say(u, "/profile")
        assert sum(1 for c in h.session.calls if type(c).__name__ == "SendPhoto") == n_photos
        assert "Best score" in h.session.texts()[-1].replace("<b>", "").replace("</b>", "")
    run(go())


def test_profile_card_renders_png_both_languages():
    from otaku_bot import card
    p = {"name": "Test", "best": 9.7, "tests": 3, "sudden": 0, "rank": 1, "weekly_rank": None, "answers": 100, "correct": 90,
         "cats": [("anime", 0.9, 10)], "games": {}}
    for lg in ("ar", "en"):
        assert card.make_profile_card(p, "King of Otaku 👑", lg)[:2] == b"\xff\xd8"


# ── قياس نمو القناة ─────────────────────────────────────
def test_channel_funnel_counts_prompted_then_joined_once():
    async def go():
        h = Harness(channel="@Anime1Galaxy")
        h.session.member = False
        a, b = h.user(1), h.user(2)
        await h.tap(a, "go")
        await h.tap(a, "go")                                       # يُعدّ مرة واحدة
        await h.tap(b, "go")
        f = h.db.funnel_stats()
        assert f["prompted"] == 2 and f["joined"] == 0
        h.session.member = True
        await h.tap(a, "chk")
        await h.tap(a, "chk")                                      # لا يتكرر
        await h.tap(b, "go")                                       # اشترك ثم ضغط «ابدأ» مباشرة
        f = h.db.funnel_stats()
        assert f["joined"] == 2 and f["prompted_7d"] == 2 and f["joined_7d"] == 2
        # مشترك أصلًا لم يُطلب منه شيء فلا يُحسب «جاء عبر البوت»
        c = h.user(3)
        await h.tap(c, "go")
        assert h.db.funnel_stats()["prompted"] == 2 and h.db.funnel_stats()["joined"] == 2
        # المشرف لا يُحسب
        h.db.add_admin(9, owner=True)
        await h.tap(h.user(9), "go")
        assert h.db.funnel_stats()["prompted"] == 2
    run(go())


def test_channel_growth_snapshots_deltas_and_admin_stats_text():
    async def go():
        h = Harness(channel="@Anime1Galaxy", admin_ids=(5,))
        db, now = h.db, time.time()
        for days, n in ((40, 100), (10, 150), (3, 170)):
            db.save_channel_count(n, now - days * 86400)
        h.session.channel_count = 200
        assert await growth.refresh_count(h.bot, h.ctx, max_age=0) == 200
        g = db.channel_growth()
        assert g["count"] == 200 and g["d7"][0] == 50 and g["d30"][0] == 100
        # كاش: لا يستدعي تليجرام ثانية قبل انتهاء المدة
        h.session.channel_count = 999
        assert await growth.refresh_count(h.bot, h.ctx, max_age=3600) == 200
        # الفشل لا يكسر شيئًا
        h.session.count_error = True
        assert await growth.refresh_count(h.bot, h.ctx, max_age=0) is None
        h.session.count_error = False
        # مسار + أرقام في لوحة الأدمن
        db.upsert_user(11, "x")
        await h.tap(h.user(5), "ad:stats")
        txt = h.session.texts()[-1]
        assert "نمو القناة" in txt and "200" in txt and "+50" in txt and "مسار اللاعبين" in txt
        # بلا قناة: لا قسم للنمو لكن يبقى المسار
        h2 = Harness(channel="", admin_ids=(5,))
        await h2.tap(h2.user(5), "ad:stats")
        t2 = h2.session.texts()[-1]
        assert "مسار اللاعبين" in t2 and "نمو القناة" not in t2
    run(go())


def test_menu_has_profile_button_and_help_mentions_stop():
    async def go():
        h = Harness()
        await h.say(h.user(1), "/start")
        assert {"pf", "st", "sg", "lg:toggle"} <= cb_data(h) and "m:more" not in cb_data(h)
        await h.say(h.user(1), "/help")
        assert "/stop" in h.session.texts()[-1] and "/profile" in h.session.texts()[-1]
    run(go())
