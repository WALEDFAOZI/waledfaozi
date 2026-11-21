"""المرحلة 2: مستأجران في العملية نفسها، ولا يرى أحدهما حالة الآخر."""
import asyncio

from harness import Harness
from otaku_bot import mafia_game as MG
from otaku_bot.links import back_rows
from otaku_bot.state import CURRENT, GameState, current, scoped
from otaku_bot.texts import t


def _run(coro):
    return asyncio.run(coro)


def test_each_tenant_has_its_own_state_objects():
    a, b = GameState(), GameState()
    assert a.mafia_games is not b.mafia_games and a.online_queue is not b.online_queue
    assert a.swaps is not b.swaps and a.channel is not b.channel


def test_channel_button_follows_the_tenant_serving_the_update():
    """المسار الكامل عبر الموزّع: كل بوت يعرض قناته هو فقط في القائمة الرئيسية."""
    from harness import last_menu_call

    ha = Harness(channel="@ChannelA", state=GameState())
    hb = Harness(channel="@ChannelB", state=GameState())
    ha.session.member = True
    hb.session.member = True

    async def go():
        await ha.say(ha.user(1, "Ann"), "/start")
        await hb.say(hb.user(1, "Ben"), "/start")
        urls_a = [b.url for row in last_menu_call(ha).reply_markup.inline_keyboard for b in row if b.url]
        urls_b = [b.url for row in last_menu_call(hb).reply_markup.inline_keyboard for b in row if b.url]
        assert "https://t.me/ChannelA" in urls_a and "https://t.me/ChannelB" not in urls_a
        assert "https://t.me/ChannelB" in urls_b and "https://t.me/ChannelA" not in urls_b
    _run(go())


def test_game_started_in_one_tenant_is_invisible_to_the_other():
    ha = Harness(state=GameState())
    hb = Harness(state=GameState())
    assert ha.ctx.state.mafia_games is not hb.ctx.state.mafia_games
    assert MG.games is not ha.ctx.state.mafia_games              # الافتراضي منفصل عن مستأجر الاختبار
    ha.ctx.state.mafia_games[-100] = object()
    assert -100 not in hb.ctx.state.mafia_games


def test_chat_info_cache_is_per_tenant():
    class Chat:
        username, type = "Shared", "channel"

    class Bot:
        async def get_chat(self, chat_id):
            return Chat()

    ha, hb = GameState(), GameState()

    async def go():
        t_a = CURRENT.set(ha)
        try:
            await back_rows(Bot(), -100555, 7, "ar")
        finally:
            CURRENT.reset(t_a)
        assert -100555 in ha.chat_info and -100555 not in hb.chat_info
    _run(go())


def test_scoped_runs_background_work_in_the_tenant_state():
    st = GameState()

    async def probe():
        return current()

    async def go():
        return await scoped(st, probe())
    assert _run(go()) is st
    assert current() is not st                      # خارج النطاق يعود للافتراضي
