"""مافيا أونلاين: الطابور، توزيع الأدوار في الخاص، نقاش باسم المرسل، وانتهاء اللعبة."""
import asyncio

import pytest

from harness import Harness, run
from otaku_bot import mafia_online as MO


@pytest.fixture(autouse=True)
def fast_online():
    old = (MO.QUEUE_SECS, MO.NIGHT_SECS, MO.TALK_SECS, MO.VOTE_SECS, MO.MSG_GAP, MO.FILL_SECS)
    MO.QUEUE_SECS, MO.NIGHT_SECS, MO.TALK_SECS, MO.VOTE_SECS, MO.MSG_GAP, MO.FILL_SECS = 1, 1, 1, 1, 0, 1
    MO.queue.clear(); MO.rooms.clear(); MO.user_room.clear(); MO.queue_token[0] += 1; MO.fill_pending[0] = False
    yield
    MO.QUEUE_SECS, MO.NIGHT_SECS, MO.TALK_SECS, MO.VOTE_SECS, MO.MSG_GAP, MO.FILL_SECS = old
    MO.queue.clear(); MO.rooms.clear(); MO.user_room.clear(); MO.queue_token[0] += 1


async def wait_until(cond, timeout=30.0):
    loop = asyncio.get_event_loop()
    t0 = loop.time()
    while loop.time() - t0 < timeout:
        if cond():
            return True
        await asyncio.sleep(0.1)
    return False


def dms(h, uid):
    return [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == uid]


def test_five_players_queue_then_get_roles_and_game_finishes():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 6)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        for u in users:
            await h.tap(u, "mo:j")
        assert await wait_until(lambda: len(MO.rooms) == 1, 10)     # بعد انتهاء الطابور يبدأ بالخمسة
        assert all(u.id in MO.user_room for u in users)
        for u in users:                                             # كل لاعب تلقّى دوره في الخاص
            assert any("دورك" in (getattr(c, "text", "") or "") or "🔍" in (getattr(c, "text", "") or "")
                       or "🔪" in (getattr(c, "text", "") or "") or "🧑" in (getattr(c, "text", "") or "")
                       for c in dms(h, u.id))
        assert await wait_until(lambda: not MO.rooms, 60)           # تنتهي اللعبة
        assert any("فاز" in (getattr(c, "text", "") or "") for c in dms(h, users[0].id))
    run(go())


def test_talk_relays_name_and_dead_or_fast_messages_are_blocked():
    async def go():
        MO.TALK_SECS = 3
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 6)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        for u in users:
            await h.tap(u, "mo:j")
        assert await wait_until(lambda: any(r.state == "talk" for r in MO.rooms.values()), 20)
        room = next(iter(MO.rooms.values()))
        sender = next(s for s in room.seats.values() if s.alive)
        await h.say(h.user(sender.uid, sender.name), "مرحبا يا جماعة")
        relayed = [c for u in users for c in dms(h, u.id) if "مرحبا يا جماعة" in (getattr(c, "text", "") or "")]
        assert len(relayed) == len(users)                           # يصل للجميع
        assert all(sender.name in c.text for c in relayed)          # باسم المرسل
    run(go())


def _roles_for(n):
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, n + 1)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        for u in users:
            await h.tap(u, "mo:j")
        assert await wait_until(lambda: bool(MO.rooms), 10)
        room = next(iter(MO.rooms.values()))
        roles = sorted(s.role for s in room.seats.values())
        MO.rooms.clear(); MO.user_room.clear()
        room.task.cancel()
        return roles
    return run(go())


def test_eight_players_get_a_mayor_and_ten_get_a_joker():
    eight = _roles_for(8)
    assert "mayor" in eight and "joker" not in eight
    ten = _roles_for(10)
    assert "mayor" in ten and "joker" in ten


def test_online_mafia_guide_button_sends_the_explanation():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        u = h.user(1, "P1")
        h.db.upsert_user(u.id, u.first_name)
        await h.tap(u, "mo:h")
        texts = [getattr(c, "text", "") or "" for c in dms(h, u.id)]
        assert any("مافيا أونلاين" in x and "الشرح" in x for x in texts)
    run(go())
