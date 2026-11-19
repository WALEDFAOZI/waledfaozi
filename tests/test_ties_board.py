"""الشكل الموحّد للترتيب، إخفاء الاسم من الترتيب، وتحدّي التعادل مع مهلة 5 ساعات."""
import asyncio
import time

from harness import Harness, last_menu_call, run
from otaku_bot import board, ties


def cbs(h):
    return {b.callback_data for c in h.session.calls if getattr(c, "reply_markup", None) is not None
            for row in c.reply_markup.inline_keyboard for b in row}


def sent_to(h, uid):
    return [c for c in h.session.calls if type(c).__name__ in ("SendMessage", "EditMessageText") and c.chat_id == uid]


def test_board_rows_are_uniform_for_arabic_and_english_names():
    pairs = [("ناروتو أوزوماكي الطويل جدًا", "9.5/10"), ("Naruto Uzumaki the long one", "8.0/10"), ("Ali", "7.0/10"), ("", "1")]
    text = board.render("T", pairs, "empty", "footer")
    lines = [x for x in text.splitlines() if "·" in x]
    assert len(lines) == 4
    assert lines[0].startswith("🥇") and lines[1].startswith("🥈") and lines[2].startswith("🥉") and lines[3].startswith("<b>4.</b>")
    assert all(board.FSI in x and board.PDI in x for x in lines)           # كل اسم معزول باتجاهه
    assert "…" in text and "Naruto Uzumaki the long one" not in text      # الطويل مقصوص
    assert text.count(board.RULE) == 2 and text.endswith("footer")
    assert board.render("T", [], "EMPTY").count("EMPTY") == 1


def test_hiding_removes_you_from_every_board_and_showing_restores():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        h.db.upsert_user(1, "Ali"); h.db.upsert_user(2, "Bob")
        with h.db.conn:
            h.db.conn.execute("UPDATE users SET best_score=9, best_sudden=7 WHERE tg_id=1")
            h.db.conn.execute("UPDATE users SET best_score=5, best_sudden=3 WHERE tg_id=2")
        await h.tap(a, "lb:menu")
        assert "lb:hide" in cbs(h)
        await h.tap(a, "lb:hide")                                           # يخفي نفسه
        assert h.db.is_lb_hidden(1)
        assert "Ali" not in " ".join(board_names(h.db))
        await h.tap(b, "lb:B:a:q")
        last = [c for c in sent_to(h, 2) if "·" in (getattr(c, "text", "") or "")][-1].text
        assert "Ali" not in last and "Bob" in last
        await h.tap(a, "lb:B:a:q")
        assert any("مخفي" in (x or "") for x in h.session.texts())
        await h.tap(a, "lb:hide")                                           # يظهر من جديد
        assert not h.db.is_lb_hidden(1)
        assert "Ali" in " ".join(board_names(h.db))
        assert h.db.user_rank(1) == 1
    run(go())


def board_names(db):
    return [r["name"] for r in db.leaderboard(10)] + [r["name"] for r in db.sudden_leaderboard(10)]


def test_tie_challenge_flow_invite_cooldown_and_rules():
    async def go():
        h = Harness()
        a, b, c3 = h.user(1, "Ali"), h.user(2, "Bob"), h.user(3, "Cy")
        for u in (a, b, c3):
            h.db.upsert_user(u.id, u.first_name)
        with h.db.conn:
            h.db.conn.execute("UPDATE users SET best_score=8.0 WHERE tg_id IN (1,2)")
            h.db.conn.execute("UPDATE users SET best_score=6.0 WHERE tg_id=3")
        assert [r["tg_id"] for r in h.db.ties_of(1)] == [2]                  # يظهر فقط صاحب نفس التقييم
        await h.tap(a, "lb:B:a:q")
        assert "tt:2" in cbs(h) and "tt:3" not in cbs(h)
        await h.tap(a, "tt:3")                                                # تقييم مختلف: مرفوض
        assert ties.can_challenge(h.db, 1, 3) == "tie_not"
        await h.tap(a, "tt:2")                                                # ✓ يتحدّاه
        d = h.db.get_duel(1)
        assert d["creator"] == 1 and d["target"] == 2 and d["tie"] == 1
        inv = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == 2]
        assert inv and "5 ساعات" in inv[-1].text and "du:acc:1" in {x.callback_data for r in inv[-1].reply_markup.inline_keyboard for x in r}
        assert ties.can_challenge(h.db, 1, 2) == "tie_cooldown"             # لا تكرار خلال 24 ساعة
        # الإخفاء يمنع التحدي (لاعب آخر بنفس التقييم مخفي)
        h.db.upsert_user(4, "Dee")
        with h.db.conn:
            h.db.conn.execute("UPDATE users SET best_score=8.0, lb_hidden=1 WHERE tg_id=4")
        assert ties.can_challenge(h.db, 1, 4) == "tie_hidden"
        assert 4 not in [r["tg_id"] for r in h.db.ties_of(1)]
    run(go())


def test_tie_window_expires_after_five_hours_and_earlier_reacher_wins():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        h.db.upsert_user(1, "Ali"); h.db.upsert_user(2, "Bob")
        with h.db.conn:
            h.db.conn.execute("UPDATE users SET best_score=8.0 WHERE tg_id IN (1,2)")
        now = time.time()
        # Bob وصل للتقييم أولًا (قبل ساعتين)، وAli بعده بساعة
        with h.db.conn:
            h.db.conn.execute("INSERT INTO sessions(tg_id,started_at,mode,state,score,finished_at,counted) VALUES(2,?,'full','finished',8.0,?,1)",
                              (now - 7200, now - 7200))
            h.db.conn.execute("INSERT INTO sessions(tg_id,started_at,mode,state,score,finished_at,counted) VALUES(1,?,'full','finished',8.0,?,1)",
                              (now - 3600, now - 3600))
        await h.tap(a, "tt:2")
        did = 1
        # مرّت 6 ساعات دون أن يلعب Bob
        with h.db.conn:
            h.db.conn.execute("UPDATE duels SET created_at=? WHERE id=?", (now - 6 * 3600, did))
        await ties.sweep(h.bot, h.db, now)
        assert h.db.get_duel(did)["state"] == "done"
        msgs_b = [c.text for c in sent_to(h, 2)]
        msgs_a = [c.text for c in sent_to(h, 1)]
        assert any("أنت الأفضل" in (x or "") for x in msgs_b)                              # Bob وصل أولًا فهو الأفضل
        assert any("لـBob" in (x or "") or "Bob" in (x or "") for x in msgs_a)           # Ali يعرف أن الفوز لـ Bob
    run(go())


def test_expired_tie_cannot_be_accepted_late():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        h.db.upsert_user(1, "Ali"); h.db.upsert_user(2, "Bob")
        with h.db.conn:
            h.db.conn.execute("UPDATE users SET best_score=8.0 WHERE tg_id IN (1,2)")
        await h.tap(a, "tt:2")
        with h.db.conn:
            h.db.conn.execute("UPDATE duels SET created_at=? WHERE id=1", (time.time() - 6 * 3600,))
        await h.say(b, "/start du_1")
        await h.tap(b, "du:acc:1")
        assert h.db.get_duel(1)["opponent"] is None                          # لم يُقبل
    run(go())
