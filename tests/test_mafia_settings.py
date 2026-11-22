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


def test_three_quiet_rounds_kill_a_random_player():
    from test_mafia_game import gtap, wait_until, group_texts
    from otaku_bot import mafia_game as MGm

    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 6)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 90)
        g = MGm.games[GROUP.id]
        for u in users:
            await h.say(u, f"/start mf_{g.gid}")
        await ptap(h, users[0], f"mf:s:{g.gid}")
        assert await wait_until(lambda: g.state == "night", 10)
        for _ in range(400):
            if any("⚰️" in x for x in group_texts(h)):
                break
            if g.state == "day":
                for u in users:
                    if g.players[u.id].alive:
                        await gtap(h, u, f"mf:v:{g.gid}:0")     # الكل يتخطى التصويت
            await asyncio.sleep(0.1)
        texts = group_texts(h)                                  # بالترتيب الزمني
        i_death = next(i for i, x in enumerate(texts) if "⚰️" in x)
        i_day3 = next(i for i, x in enumerate(texts) if "النهار 3" in x)
        assert not any("⚰️" in x for x in texts[:i_day3]), "مات أحد قبل الجولة الثالثة"
        assert i_death > i_day3, "يجب أن يحدث الموت بعد الجولة الهادئة الثالثة"
        dead = [p for p in g.players.values() if not p.alive]
        assert len(dead) == 1
    run(go())


def test_morning_vote_dms_link_to_the_vote_and_non_voters_are_announced():
    from test_mafia_game import dms_to, group_texts, wait_until as wu
    from otaku_bot import mafia_game as MGm

    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 6)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 91)
        g = MGm.games[GROUP.id]
        for u in users:
            await h.say(u, f"/start mf_{g.gid}")
        await ptap(h, users[0], f"mf:s:{g.gid}")
        assert await wu(lambda: g.state == "day", 15)
        assert g.day_mid is not None
        for u in users:                                      # كل حي تلقّى رسالة فيها زر يفتح التصويت
            dm = [c for c in dms_to(h, u.id) if "التصويت الصباحي" in (c.text or "")]
            assert dm, u.first_name
            urls = [b.url for row in dm[-1].reply_markup.inline_keyboard for b in row if b.url]
            assert urls and f"/{g.day_mid}" in urls[0] and urls[0].startswith("https://t.me/")
        assert await wu(lambda: any("لم يصوّت" in x for x in group_texts(h)), 15)
        assert any("على نفسه" in x for x in group_texts(h))
    run(go())
