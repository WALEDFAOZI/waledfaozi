"""إعدادات المافيا من الخاص: التلقائي، الأوقات، والرسائل الجديدة في المجموعة."""
import asyncio

from harness import Harness, run
from otaku_bot import mafia as M
from otaku_bot import mafia_game as MG
from aiogram.types import CallbackQuery, Chat, Message, Update
import datetime as dt

from test_mafia_game import GROUP, fast, gcmd  # noqa: F401  (fixture + helpers)


async def ptap(h, user, data):
    """ضغطة من الخاص مع البوت (إعدادات المضيف تعيش في الخاص)."""
    h.uid += 1
    chat = Chat(id=user.id, type="private")
    m = Message(message_id=900, date=dt.datetime.now(), chat=chat, text=".")
    cb = CallbackQuery(id=str(h.uid), from_user=user, chat_instance="p", data=data, message=m)
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, callback_query=cb))


def test_auto_config_is_valid_for_every_player_count():
    for n in range(M.MIN_PLAYERS, M.MAX_PLAYERS + 1):
        k, sp = M.auto_config(n)
        M.Config(killers=k, specials=sp).validate(n)         # يمرّ دائمًا من التحقق
        assert k >= 1 and len(sp) == len(set(sp))


def test_host_sets_timers_from_private_chat_within_limits():
    async def go():
        h = Harness()
        host = h.user(1, "Host")
        for i in range(2, 6):
            h.db.upsert_user(i, f"P{i}")
        await gcmd(h, host, "/mafia", 77)
        g = MG.games[GROUP.id]
        before = g.night_secs
        await ptap(h, host, f"mf:tm:{g.gid}:night:+")
        assert g.night_secs == before + 15
        for _ in range(40):
            await ptap(h, host, f"mf:tm:{g.gid}:lobby:+")
        assert g.lobby_secs == 600                           # الحد الأعلى للانتظار
        for _ in range(40):
            await ptap(h, host, f"mf:tm:{g.gid}:day:-")
        assert g.day_secs == 15                              # الحد الأدنى للنهار
    run(go())


def test_non_host_cannot_change_timers_or_auto():
    async def go():
        h = Harness()
        host, other = h.user(1, "Host"), h.user(9, "Other")
        await gcmd(h, host, "/mafia", 78)
        g = MG.games[GROUP.id]
        before = (g.lobby_secs, g.night_secs, g.day_secs)
        await ptap(h, other, f"mf:tm:{g.gid}:night:+")
        await ptap(h, other, f"mf:a:{g.gid}")
        assert (g.lobby_secs, g.night_secs, g.day_secs) == before
    run(go())


def test_manual_change_turns_auto_off_and_auto_button_turns_it_back_on():
    async def go():
        h = Harness()
        host = h.user(1, "Host")
        await gcmd(h, host, "/mafia", 79)
        g = MG.games[GROUP.id]
        assert g.auto is True
        await ptap(h, host, f"mf:k:{g.gid}:+")
        assert g.auto is False
        await ptap(h, host, f"mf:a:{g.gid}")
        assert g.auto is True and g.killers == M.auto_config(max(M.MIN_PLAYERS, len(g.players)))[0]
    run(go())
