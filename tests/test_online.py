"""لعب أونلاين: طابور، مطابقة، أسئلة متطابقة، ونتيجة للطرفين."""
import asyncio

import pytest

from harness import Harness, run
from otaku_bot import online as O


@pytest.fixture(autouse=True)
def fast():
    old = (O.ROUNDS, O.ROUND_SECS, O.GAP_SECS, O.QUEUE_SECS)
    O.ROUNDS, O.ROUND_SECS, O.GAP_SECS, O.QUEUE_SECS = 3, 1.5, 0, 30
    O.matches.clear(); O.user_match.clear()
    for k in O.queue:
        O.queue[k].clear()
    yield
    O.ROUNDS, O.ROUND_SECS, O.GAP_SECS, O.QUEUE_SECS = old
    O.matches.clear(); O.user_match.clear()


async def wait_until(cond, timeout=15.0):
    t0 = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - t0 < timeout:
        if cond():
            return True
        await asyncio.sleep(0.1)
    return False


def texts(h, uid):
    return [(getattr(c, "text", None) or "") for c in h.session.calls
            if getattr(c, "chat_id", None) == uid and type(c).__name__ in ("SendMessage", "EditMessageText")]


def test_two_players_are_matched_answer_and_both_see_result():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        h.db.upsert_user(1, "Ali"); h.db.upsert_user(2, "Bob")
        await h.tap(a, "on:j:quiz")                                # ينتظر
        assert 1 in [x[0] for x in O.queue["quiz"]]
        await h.tap(b, "on:j:quiz")                                # يُطابَق
        assert O.user_match.get(1) and O.user_match.get(1) == O.user_match.get(2)
        mid = O.user_match[1]
        m = O.matches[mid]
        assert m.qs[0]["text"] and len(m.qs) == 3
        for _ in range(3):
            assert await wait_until(lambda: m.rnd >= 0 and len(m.answers) == 0)
            rnd = m.rnd
            await h.tap(a, f"on:a:{mid}:{rnd}:{m.qs[rnd]['answer']}")     # الصحيح
            await h.tap(b, f"on:a:{mid}:{rnd}:{(m.qs[rnd]['answer'] + 1) % len(m.qs[rnd]['opts'])}")
            assert await wait_until(lambda: m.rnd != rnd or mid not in O.matches)
        assert await wait_until(lambda: mid not in O.matches)
        assert any("فزت" in x for x in texts(h, 1)) and any("خسرت" in x for x in texts(h, 2))
        assert any("انتهت المباراة" in x for x in texts(h, 2))
        # بعد الانتهاء يمكن اللعب من جديد
        assert 1 not in O.user_match
    run(go())


def test_same_questions_for_both_and_cancel_and_busy():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        h.db.upsert_user(1, "Ali"); h.db.upsert_user(2, "Bob")
        await h.tap(a, "on:j:tf")
        await h.tap(a, "on:j:tf")                                   # مرة ثانية وهو في الطابور: لا تكرار
        assert len([x for x in O.queue["tf"] if x[0] == 1]) == 1
        await h.tap(a, "on:c:tf")
        assert not O.queue["tf"]
        await h.tap(a, "on:j:tf")
        await h.tap(b, "on:j:tf")
        mid = O.user_match[1]
        m = O.matches[mid]
        await h.tap(b, "on:j:tf")                                   # في مباراة: لا يُضاف للطابور
        assert not O.queue["tf"] and 2 not in [x[0] for x in O.queue["tf"]]
        assert [q["text"] for q in m.qs] and len(m.qs) == 3
        await h.tap(a, f"on:q:{mid}")                               # الانسحاب يخسر
        assert await wait_until(lambda: mid not in O.matches)
        assert any("خسرت" in x for x in texts(h, 1))
        assert any("فزت" in x for x in texts(h, 2))
    run(go())
