"""الإبلاغ عن الأخطاء متاح لكل سؤال (اختبارات وألعاب)، مع الحماية من الإساءة."""
import asyncio
import json

from harness import Harness, last_menu_call, run
from otaku_bot.games import item_key, load_games


def markup_data(call):
    return {b.callback_data for row in call.reply_markup.inline_keyboard for b in row}


def last_markup(h):
    return [c for c in h.session.calls if getattr(c, "reply_markup", None) is not None][-1]


def test_every_question_screen_in_every_mode_has_a_report_button():
    async def go():
        h = Harness()
        u = h.user(1)
        for start in ("go", "qk", "sd", "ct:characters"):
            await h.tap(u, start)
            sid = h.db.active_session(1)["id"]
            call = [c for c in h.session.calls if getattr(c, "reply_markup", None) is not None and
                    f"a:{sid}:0:0" in markup_data(c)][-1]
            assert f"rq:{sid}:0" in markup_data(call), start
            await h.play(u, limit=1)
            call = [c for c in h.session.calls if getattr(c, "reply_markup", None) is not None and
                    f"a:{sid}:1:0" in markup_data(c)]
            if call:
                assert f"rq:{sid}:1" in markup_data(call[-1])
            await h.say(u, "/stop")
        # شاشة انتهاء الوقت أيضًا
        h2 = Harness(timer=30)
        await h2.tap(h2.user(2), "go")
        sid = h2.db.active_session(2)["id"]
        h2.db.conn.execute("UPDATE session_questions SET sent_at=sent_at-100 WHERE session_id=? AND pos=0", (sid,))
        await h2.tap(h2.user(2), "resume")                    # الوقت منتهٍ: يعرض شاشة انتهاء الوقت
        assert f"rq:{sid}:0" in markup_data(last_markup(h2))
    run(go())


def test_report_during_active_quiz_does_not_disturb_the_quiz():
    async def go():
        h = Harness()
        u = h.user(1)
        await h.tap(u, "go")
        sid = h.db.active_session(1)["id"]
        before = h.db.get_session(sid)
        await h.play(u, limit=3)
        pos = h.db.get_session(sid)["current_pos"]
        await h.tap(u, f"rq:{sid}:{pos}")                                # سبب جديد في رسالة جديدة
        assert "المشكلة" in h.session.texts()[-1] and f"rr:{sid}:{pos}:0" in markup_data(last_markup(h))
        assert {f"rr:{sid}:{pos}:{i}" for i in range(4)} <= markup_data(last_markup(h))
        assert f"rr:{sid}:{pos}:4" not in markup_data(last_markup(h))    # سبب الصورة فقط لأسئلة الصور
        await h.tap(u, f"rr:{sid}:{pos}:1")
        qid = h.db.session_question(sid, pos)["question_id"]
        assert h.db.open_report_count(qid) == 1
        assert any(type(c).__name__ == "DeleteMessage" for c in h.session.calls)   # تنظيف رسالة الأسباب
        s = h.db.get_session(sid)
        assert s["state"] == "active" and s["current_pos"] == pos                   # الاختبار لم يتأثر
        await h.tap(u, f"rq:{sid}:{pos}")
        await h.tap(u, f"rr:{sid}:{pos}:2")                                          # نفس السؤال ثانية = مكرر
        assert h.db.open_report_count(qid) == 1
        await h.play(u, limit=2)                                                      # يكمل الاختبار عاديًا
        assert h.db.get_session(sid)["current_pos"] == pos + 2
    run(go())


def test_cannot_report_unseen_questions_or_other_players_sessions():
    async def go():
        h = Harness()
        a, b = h.user(1), h.user(2)
        await h.tap(a, "go")
        sid = h.db.active_session(1)["id"]
        await h.tap(a, f"rq:{sid}:30")                                    # لم يظهر له بعد
        await h.tap(a, f"rr:{sid}:30:0")
        assert h.db.conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0
        await h.tap(b, f"rq:{sid}:0")                                     # جلسة غيره
        await h.tap(b, f"rr:{sid}:0:0")
        assert h.db.conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0
        await h.tap(a, f"rr:{sid}:0:0")                                   # لنفسه: يقبل
        assert h.db.conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1
        await h.tap(a, f"rr:{sid}:0:9")                                   # سبب غير صالح
        assert h.db.conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1
    run(go())


def test_after_finish_list_has_all_questions_paginated_with_icons():
    async def go():
        h = Harness()
        u = h.user(1)
        await h.tap(u, "go")
        sid = h.db.active_session(1)["id"]
        await h.play(u, correct=True, limit=48)
        await h.play(u, correct=False, limit=2)                           # آخر سؤالين خطأ
        s = h.db.get_session(sid)
        assert s["state"] == "finished"
        btns = [c for c in h.session.calls if getattr(c, "reply_markup", None) is not None]
        assert f"rp:{sid}:0" in markup_data([c for c in btns if "rp:" in str(c.reply_markup)][-1])   # زر الإبلاغ بعد النتيجة
        await h.tap(u, f"rp:{sid}:0")
        page0 = last_markup(h)
        labels = [b.text for row in page0.reply_markup.inline_keyboard for b in row]
        assert sum(1 for x in labels if x.startswith("✅")) == 8 and f"rp:{sid}:1" in markup_data(page0)
        pages = 7
        await h.tap(u, f"rp:{sid}:{pages - 1}")                           # آخر صفحة: سؤالان فقط وكلاهما ❌
        last = last_markup(h)
        lab = [b.text for row in last.reply_markup.inline_keyboard for b in row if b.callback_data and b.callback_data.startswith("rq:")]
        assert len(lab) == 2 and all(x.startswith("❌") for x in lab)
        await h.tap(u, f"rp:{sid}:99")                                    # صفحة خارج النطاق تُقيَّد
        # الإبلاغ عن سؤال أجبته صح (ليس خطأك أنت) مسموح الآن
        await h.tap(u, f"rr:{sid}:0:0")
        assert h.db.conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1
    run(go())


def test_image_reason_only_for_image_questions_and_daily_limit_is_shared():
    async def go():
        h = Harness()
        db = h.db
        h.db.set_setting("reports_per_day", "3")
        u = h.user(1)
        await h.tap(u, "go")
        sid = h.db.active_session(1)["id"]
        qid = db.add_question("من هذه؟", ["A", "B", "C", "D"], 0, "images", 1, image="https://x/1.png", q_en="Who?", options_en=["A", "B", "C", "D"])
        db.conn.execute("UPDATE session_questions SET question_id=? WHERE session_id=? AND pos=0", (qid, sid))
        await h.tap(u, f"rq:{sid}:0")
        assert f"rr:{sid}:0:4" in markup_data(last_markup(h))             # سبب «الصورة غير صحيحة» يظهر
        # الحد اليومي يُحسب مرة واحدة على الأسئلة والألعاب معًا
        await h.tap(u, f"rr:{sid}:0:0")
        await h.play(u, limit=1)
        await h.tap(u, f"rr:{sid}:1:0")
        await h.tap(u, "g:tf")
        gid = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
        await h.tap(u, f"gz:{gid}:0:0")                                    # الثالث: يصل الحد
        assert db.reports_today(1) == 3
        await h.tap(u, "g:song")
        gid2 = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
        await h.tap(u, f"gz:{gid2}:0:0")                                   # الرابع: مرفوض بالحد المشترك
        assert db.reports_today(1) == 3
    run(go())


def test_game_items_can_be_reported_hidden_and_never_drawn_again():
    async def go():
        h = Harness(admin_ids=(5,))
        db = h.db
        db.set_setting("report_threshold", "2")
        data = load_games()
        for kind in ("tf", "ord", "char", "quote"):
            u = h.user(1)
            await h.tap(u, f"g:{kind}")
            gid = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
            assert f"gq:{gid}:0" in markup_data(last_markup(h))            # زر الإبلاغ على كل جولة
            await h.tap(u, f"gq:{gid}:0")
            assert f"gz:{gid}:0:0" in markup_data(last_markup(h))
            await h.tap(u, f"gz:{gid}:0:1")
            assert db.conn.execute("SELECT COUNT(*) FROM game_reports WHERE kind=?", (kind,)).fetchone()[0] == 1
            await h.tap(u, f"gz:{gid}:0:1")                                  # مكرر
            assert db.conn.execute("SELECT COUNT(*) FROM game_reports WHERE kind=?", (kind,)).fetchone()[0] == 1
            await h.tap(u, f"gq:{gid}:9")                                    # جولة لم تظهر بعد
            await h.tap(u, f"gz:{gid}:9:0")
            await h.tap(h.user(2), f"gz:{gid}:0:0")                          # لاعب آخر لا يملك هذه اللعبة
            assert db.conn.execute("SELECT COUNT(*) FROM game_reports WHERE kind=? AND tg_id=2", (kind,)).fetchone()[0] == 0
            await h.tap(u, f"gx:{gid}")
        # بلاغ ثانٍ من لاعب آخر على نفس العنصر → إشعار للمشرف عند العتبة (2)
        u2 = h.user(2)
        await h.tap(u, "g:tf")
        gid = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
        key_text = data["tf"][db.get_game(gid)["state"]["rounds"][0]][0]
        row = db.conn.execute("SELECT key FROM game_reports WHERE kind='tf'").fetchone()
        # نبلّغ باسم لاعب ثانٍ على العنصر نفسه مباشرة عبر القاعدة ثم نتحقق من لوحة الأدمن
        k = row["key"]
        db.add_game_report("tf", k, "x", 2, "r", 10)
        # لوحة الأدمن تعرض بلاغات الألعاب
        await h.tap(h.user(5), "ad:rep")
        assert any("🎮" in b.text for rw in last_markup(h).reply_markup.inline_keyboard for b in rw)
        await h.tap(h.user(5), f"ad:gv:tf:{k}")
        assert "بلاغ على عنصر لعبة" in h.session.texts()[-1] and f"ad:gh:tf:{k}" in markup_data(last_markup(h))
        await h.tap(h.user(5), f"ad:gh:tf:{k}")                              # إخفاء من اللعبة
        assert k in db.game_hidden() and db.game_open_count("tf", k) == 0
        # لا يظهر أبدًا بعد الإخفاء (جرّب سحبًا كثيرًا)
        hidden_text = next(s[0] for s in data["tf"] if item_key(s[0]) == k)
        from otaku_bot.games import new_state
        import random as _r
        for seed in range(60):
            st = new_state("tf", data, _r.Random(seed), db.game_hidden())
            assert all(data["tf"][i][0] != hidden_text for i in st["rounds"])
        # «الترتيب» لا يُخفى (تجاهل فقط)
        await h.tap(h.user(5), "ad:rep")
        o = db.conn.execute("SELECT key FROM game_reports WHERE kind='ord'").fetchone()["key"]
        await h.tap(h.user(5), f"ad:gv:ord:{o}")
        assert f"ad:gh:ord:{o}" not in markup_data(last_markup(h)) and f"ad:gd:ord:{o}" in markup_data(last_markup(h))
        await h.tap(h.user(5), f"ad:gd:ord:{o}")
        assert db.game_open_count("ord", o) == 0
        # غير المشرف لا يستطيع
        await h.tap(h.user(77), f"ad:gh:tf:{k}")
        assert db.game_hidden() == {k}
    run(go())


def test_threshold_notification_for_game_items_and_default_daily_limit():
    async def go():
        h = Harness(admin_ids=(5,))
        db = h.db
        assert h.ctx.reports_per_day() == 10                                 # الافتراضي رُفع ليناسب الإبلاغ عن أي سؤال
        db.set_setting("report_threshold", "2")
        u1, u2 = h.user(1), h.user(2)
        await h.tap(u1, "g:quote")
        g1 = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
        await h.tap(u2, "g:quote")
        g2 = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
        st1, st2 = db.get_game(g1)["state"], db.get_game(g2)["state"]
        st2["rounds"][0] = st1["rounds"][0]                                  # نفس الاقتباس لكلا اللاعبين
        db.save_game(g2, st2)
        admin_msgs = lambda: [c for c in h.session.calls if getattr(c, "chat_id", None) == 5 and "وصل 2 بلاغات" in (getattr(c, "text", "") or "")]   # noqa: E731
        await h.tap(u1, f"gz:{g1}:0:0")
        assert not admin_msgs()                                              # بلاغ واحد: لا إشعار
        await h.tap(u2, f"gz:{g2}:0:2")
        msgs = admin_msgs()
        assert len(msgs) == 1                                                # عند العتبة: إشعار واحد
        key = [b.callback_data for row in msgs[0].reply_markup.inline_keyboard for b in row][0]
        assert key.startswith("ad:gv:quote:")
        await h.tap(h.user(5), key)
        assert "بلاغ على عنصر لعبة" in h.session.texts()[-1]
    run(go())
