"""التحدي اليومي، سؤال اليوم، السلسلة، التذكير الاختياري، والمواجهة مع صديق."""
import asyncio
import time

from harness import Harness, run
from otaku_bot import daily


def qids(h, uid, mode):
    s = h.db.conn.execute("SELECT id FROM sessions WHERE tg_id=? AND mode=? ORDER BY id DESC", (uid, mode)).fetchone()
    return [r["question_id"] for r in h.db.conn.execute(
        "SELECT question_id FROM session_questions WHERE session_id=? ORDER BY pos", (s["id"],))]


def test_daily_same_questions_for_everyone_once_a_day_and_streak():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await h.tap(a, "dy:d")
        await h.play(a)
        await h.tap(b, "dy:d")
        await h.play(b, correct=False)
        assert qids(h, 1, "daily") == qids(h, 2, "daily") and len(qids(h, 1, "daily")) == 5
        day = h.db.today()
        assert h.db.daily_result(day, "daily", 1)["correct"] == 5
        assert h.db.daily_result(day, "daily", 2)["correct"] == 0
        assert [r["tg_id"] for r in h.db.daily_board(day)] == [1, 2]
        assert h.db.current_streak(1, day) == 1
        n = len(h.db.conn.execute("SELECT 1 FROM sessions WHERE tg_id=1").fetchall())
        await h.tap(a, "dy:d")                                   # محاولة ثانية في نفس اليوم
        assert len(h.db.conn.execute("SELECT 1 FROM sessions WHERE tg_id=1").fetchall()) == n
        assert any("ارجع بكرة" in x for x in h.session.texts())
        # لا يتأثر التقييم العام
        assert h.db.get_user(1)["best_score"] == 0 and h.db.get_user(1)["tests_taken"] == 0
    run(go())


def test_question_of_day_counts_streak_even_when_wrong_and_streak_breaks():
    async def go():
        h = Harness()
        u = h.user(1)
        await h.tap(u, "dy:q")
        assert len(qids(h, 1, "dq")) == 1
        await h.play(u, correct=False)
        day = h.db.today()
        assert h.db.get_user(1)["streak"] == 1 and any("السلسلة" in x for x in h.session.texts())
        # أمس + اليوم = 2 ، وبعد غياب يوم تنكسر
        assert h.db.mark_streak(1, day + 1) == (2, True) and h.db.mark_streak(1, day + 1) == (2, False)
        assert h.db.mark_streak(1, day + 3) == (1, True)
        assert h.db.current_streak(1, day + 9) == 0 and h.db.get_user(1)["best_streak"] == 2
    run(go())


def test_admin_hidden_from_daily_board():
    h = Harness()
    h.db.upsert_user(1, "Owner"); h.db.add_admin(1); h.db.upsert_user(2, "Sara")
    d = h.db.today()
    h.db.record_daily(d, "daily", 1, 5, 5, 10); h.db.record_daily(d, "daily", 2, 3, 5, 20)
    assert [r["tg_id"] for r in h.db.daily_board(d)] == [2]


def test_reminder_is_opt_in_once_a_day_and_stops_for_blocked():
    async def go():
        h = Harness()
        u = h.user(1)
        await h.say(u, "/start")
        assert h.db.remind_targets(h.db.today()) == []           # افتراضيًا متوقف
        await h.tap(u, "dy:rm")
        assert h.db.get_user(1)["remind"] == 1
        day = h.db.today()
        assert [r["tg_id"] for r in h.db.remind_targets(day)] == [1]
        h.db.mark_reminded(1, day)
        assert h.db.remind_targets(day) == []                     # مرة واحدة فقط
        await h.tap(u, "dy:off")
        assert h.db.get_user(1)["remind"] == 0
        h.db.set_remind(1, True); h.db.mark_streak(1, day)
        assert h.db.remind_targets(day + 1)[0]["tg_id"] == 1 and h.db.remind_targets(day) == []   # لعب اليوم = لا تذكير
        assert "سلسلتك" in daily.remind_text("ar", 3, day, day + 1) and "جاهز" in daily.remind_text("ar", 0, 0, day)
    run(go())


def test_duel_end_to_end():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await h.say(a, "/start")
        await h.tap(a, "du:new:q")
        await h.tap(a, "du:go:1")
        await h.play(a)                                           # صحّ الكل
        d = h.db.get_duel(1)
        assert d["creator"] == 1 and d["creator_sid"]
        assert any("أرسل الرابط" in x for x in h.session.texts())
        await h.say(b, "/start du_1")
        assert any("يتحداك" in x for x in h.session.texts() + [getattr(c, "caption", "") or "" for c in h.session.calls])
        await h.tap(b, "du:acc:1")
        await h.play(b, correct=False)
        assert h.db.get_duel(1)["state"] == "done"
        res = [x for x in h.session.texts() if "نتيجة المواجهة" in x]
        assert len(res) == 2 and all("فاز Ali" in x for x in res)
        c = h.user(3, "Cy")                                       # ثالث لا يقدر يقبل تحدي منتهي
        await h.say(c, "/start du_1")
        await h.tap(c, "du:acc:1")
        assert h.db.get_duel(1)["opponent"] == 2
        assert h.db.get_user(1)["best_score"] == 0               # لا يمس التقييم العام
    run(go())


def test_daily_questions_deterministic_per_day():
    h = Harness()
    pool = [q for q in h.db.all_questions() if q.q_en]
    assert [q.id for q in daily.daily_questions(pool, 100, "daily")] == [q.id for q in daily.daily_questions(pool[::-1], 100, "daily")]
    assert [q.id for q in daily.daily_questions(pool, 100, "daily")] != [q.id for q in daily.daily_questions(pool, 101, "daily")]


def test_reminder_loop_sends_once_and_respects_block():
    async def go():
        h = Harness()
        daily.REMIND_HOUR = 0
        try:
            h.db.upsert_user(1, "A"); h.db.upsert_user(2, "B")
            h.db.set_remind(1, True); h.db.set_remind(2, True)
            task = asyncio.create_task(daily.reminder_loop(h.bot, h.ctx))
            await asyncio.sleep(0.5)
            task.cancel()
        finally:
            daily.REMIND_HOUR = 18
        sent = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id in (1, 2)]
        assert len(sent) == 2 and h.db.remind_targets(h.db.today()) == []
    run(go())


def test_rankings_choose_period_then_game_type_and_hide_admin():
    async def go():
        h = Harness()
        u = h.user(1, "Ali")
        h.db.upsert_user(1, "Ali"); h.db.upsert_user(2, "Bob"); h.db.upsert_user(9, "Owner"); h.db.add_admin(9)
        with h.db.conn:
            h.db.conn.execute("INSERT INTO game_scores(tg_id,kind,best) VALUES(1,'tf',8),(2,'tf',6),(9,'tf',10),(1,'song',5)")
            h.db.conn.execute("INSERT INTO game_sessions(tg_id,kind,state,score,started_at,finished_at) VALUES(1,'tf','x',7,1,?),(9,'tf','x',9,1,?),(2,'tf','x',3,1,?)",
                              (time.time(), time.time(), time.time()))
        d = h.db.today()
        h.db.record_daily(d, "daily", 1, 4, 5, 20); h.db.record_daily(d, "daily", 9, 5, 5, 10)

        def cbs():
            return {b.callback_data for c in h.session.calls if getattr(c, "reply_markup", None) is not None
                    for row in c.reply_markup.inline_keyboard for b in row}

        def last_text():
            return [getattr(c, "text", "") or "" for c in h.session.calls if type(c).__name__ in ("EditMessageText", "SendMessage")][-1]
        await h.tap(u, "lb:menu")                                    # 1) اختيار المدة فقط
        assert {"lb:P:a", "lb:P:w", "lb:P:d"} <= cbs() and "lb:B:a:tf" not in cbs()
        await h.tap(u, "lb:P:a")                                     # 2) أنواع الألعاب داخل المدة
        assert {"lb:B:a:q", "lb:B:a:s", "lb:B:a:tf", "lb:B:a:char"} <= cbs() and "lb:B:a:dc" not in cbs() and "lb:B:a:song" not in cbs()   # لعبة «من الأغنية» أُلغيت
        await h.tap(u, "lb:B:a:tf")                                  # 3) اللوحة
        assert "Ali" in last_text() and "Bob" in last_text() and "Owner" not in last_text()
        await h.tap(u, "lb:B:d:tf")                                  # اليوم: من لعب اليوم فقط
        assert "Ali" in last_text() and "Owner" not in last_text()
        await h.tap(u, "lb:P:d")
        assert "lb:B:d:dc" in cbs()
        await h.tap(u, "lb:B:d:dc")
        assert "Ali" in last_text() and "Owner" not in last_text()
    run(go())
