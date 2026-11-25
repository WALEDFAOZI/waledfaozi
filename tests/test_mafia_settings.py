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
        assert await wu(lambda: g.voting, 15)
        assert g.day_mid is not None
        for u in [u for u in users if g.players[u.id].alive]:   # كل حي تلقّى رسالة فيها زر يفتح التصويت
            dm = [c for c in dms_to(h, u.id) if "التصويت الصباحي" in (c.text or "")]
            assert dm, u.first_name
            urls = [b.url for row in dm[-1].reply_markup.inline_keyboard for b in row if b.url]
            assert urls and f"/{g.day_mid}" in urls[0] and urls[0].startswith("https://t.me/")
        assert await wu(lambda: any("بقي صامتًا" in x for x in group_texts(h)), 15)
        assert any("على نفسه" in x for x in group_texts(h))
    run(go())


def test_killer_who_leaves_after_picking_cannot_kill():
    from test_mafia_game import gtap, wait_until as wu
    from otaku_bot import mafia_game as MGm

    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 6)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 92)
        g = MGm.games[GROUP.id]
        for u in users:
            await h.say(u, f"/start mf_{g.gid}")
        await ptap(h, users[0], f"mf:s:{g.gid}")
        assert await wu(lambda: g.state == "night", 15)
        killer = next(p for p in g.players.values() if p.role == "killer")
        victim = next(p for p in g.players.values() if p.role != "killer" and p.uid != killer.uid)
        k_user = next(u for u in users if u.id == killer.uid)
        await h.tap(k_user, f"mf:n:{g.gid}:killer:{victim.uid}")          # يختار ضحية
        await gtap(h, k_user, f"mf:l:{g.gid}")                              # ثم ينسحب في الليل نفسه
        assert await wu(lambda: g.state in ("day", "done"), 15)   # القاتل خرج: يفوز المواطنون بعد الليل
        assert g.players[victim.uid].alive, "من انسحب لا يجوز أن يقتل"
    run(go())


def test_mafia_that_picks_nobody_gets_a_victim_chosen_by_the_bot():
    from test_mafia_game import wait_until as wu
    from otaku_bot import mafia_game as MGm

    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 6)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 93)
        g = MGm.games[GROUP.id]
        for u in users:
            await h.say(u, f"/start mf_{g.gid}")
        await ptap(h, users[0], f"mf:s:{g.gid}")
        assert await wu(lambda: g.state in ("day", "done"), 15)      # لا أحد من القتلة يختار
        dead = [p for p in g.players.values() if not p.alive]
        assert len(dead) == 1 and dead[0].role != "killer"           # البوت اختار ضحية من غير القتلة
    run(go())


def test_vote_results_show_counts_without_naming_voters():
    from test_mafia_game import gtap, group_texts, wait_until as wu
    from otaku_bot import mafia_game as MGm

    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 6)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 94)
        g = MGm.games[GROUP.id]
        for u in users:
            await h.say(u, f"/start mf_{g.gid}")
        await ptap(h, users[0], f"mf:s:{g.gid}")
        assert await wu(lambda: g.voting, 15)
        a = [u for u in users if g.players[u.id].alive]
        assert len(a) >= 4
        await gtap(h, a[0], f"mf:v:{g.gid}:{a[2].id}")
        await gtap(h, a[1], f"mf:v:{g.gid}:{a[2].id}")
        await gtap(h, a[3], f"mf:v:{g.gid}:0")
        assert await wu(lambda: any("حصيلة الأصوات" in x for x in group_texts(h)), 15)
        res = [x for x in group_texts(h) if "حصيلة الأصوات" in x][-1]
        # a[2] لم يصوّت فصوته يُحسب على نفسه: صوتان من الآخرين + صوته = 3
        assert f"{a[2].first_name}: 3" in res and "تخطّي: 1" in res          # العدد يظهر
        for voter in a[:2] + [a[3]]:
            assert voter.first_name not in res                              # لا أسماء المصوتين
    run(go())


def test_mayor_reveals_once_during_the_day_and_is_announced():
    from test_mafia_game import wait_until as wu, group_texts
    from otaku_bot import mafia_game as MGm

    async def go():
        MGm.DAY_SECS, MGm.DISCUSS_SECS = 30, 1               # وقت كافٍ للضغط على زر الكشف حتى مع ضغط الجهاز
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 9)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 96)
        g = MGm.games[GROUP.id]
        for u in users:
            await h.say(u, f"/start mf_{g.gid}")
        await ptap(h, users[0], f"mf:s:{g.gid}")
        assert await wu(lambda: g.state in ("night", "day"), 15)
        mayor = next(p for p in g.players.values() if p.role == "mayor")
        mayor_user = next(u for u in users if u.id == mayor.uid)
        victim = next(p for p in g.players.values() if p.role == "citizen")   # القتلة يختارون مواطنًا غير العمدة
        for p in g.players.values():
            if p.role == "killer":
                await ptap(h, next(u for u in users if u.id == p.uid), f"mf:n:{g.gid}:killer:{victim.uid}")
        assert await wu(lambda: g.voting, 15)
        assert g.players[mayor.uid].alive                      # العمدة ما زال حيًّا
        await ptap(h, mayor_user, f"mf:rv:{g.gid}")              # يكشف نفسه في النهار
        assert g.mayor_revealed
        assert any(mayor.name in x and "يكشف عن نفسه" in x for x in group_texts(h))   # يُعلن الاسم
        await ptap(h, mayor_user, f"mf:rv:{g.gid}")              # مرة واحدة فقط
        assert sum(1 for x in group_texts(h) if "يكشف عن نفسه" in x) == 1
        MGm.DAY_SECS = 3
    run(go())


def test_deleted_live_message_stops_the_game_and_tells_the_host():
    from test_mafia_game import wait_until as wu
    from otaku_bot import mafia_game as MGm

    async def go():
        MGm.games.clear()
        MGm.cooldown.clear()
        h = Harness()
        users = [h.user(i, f"P{i}") for i in range(1, 4)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 97)
        g = MGm.games[GROUP.id]
        h.session.edit_gone = True                              # الرسالة الحيّة حُذفت
        await h.say(users[1], f"/start mf_{g.gid}")             # الانضمام يعدّل الرسالة الحيّة
        assert await wu(lambda: g.gone, 10)
        assert g.state == "done"
        assert await wu(lambda: any("توقفت لعبة المافيا" in (getattr(c, "text", None) or "") for c in h.session.calls
                                    if type(c).__name__ == "SendMessage" and c.chat_id == users[0].id), 10)
        h.session.edit_gone = False
    run(go())


def test_reveal_on_death_is_off_by_default_and_toggles_from_settings():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 6)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 91)
        g = MG.games[GROUP.id]
        assert g.reveal_death is False                                  # افتراضيًا مخفي
        await ptap(h, users[0], f"mf:rd:{g.gid}")
        assert g.reveal_death is True
        await ptap(h, users[0], f"mf:rd:{g.gid}")
        assert g.reveal_death is False
        g.start_now = True
    run(go())


def test_failed_role_dm_removes_player_and_reopens_lobby_for_90s():
    async def go():
        from test_mafia_game import wait_until
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 7)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 92)
        g = MG.games[GROUP.id]
        for u in users[1:]:
            await h.say(u, f"/start mf_{g.gid}")
        h.session.blocked_chats.add(users[2].id)                   # يحظر البوت فلا يصله دوره
        await ptap(h, users[0], f"mf:s:{g.gid}")
        assert await wait_until(lambda: users[2].id not in g.players, 15)
        assert await wait_until(lambda: any("نفتح اللوبي" in x for x in group_texts_of(h)), 15)
        assert g.state == "lobby"                                   # رجع للوبي ولم تنته اللعبة
        g.start_now = True
    run(go())


def group_texts_of(h):
    return [(getattr(c, "text", None) or getattr(c, "caption", None) or "") for c in h.session.calls
            if getattr(c, "chat_id", None) == GROUP.id]


def test_too_few_players_deletes_the_lobby_message():
    from test_mafia_game import wait_until

    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 4)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 93)
        g = MG.games[GROUP.id]
        for u in users[1:]:
            await h.say(u, f"/start mf_{g.gid}")
        lobby_mid = g.live
        g.lobby_secs = 1
        assert await wait_until(lambda: GROUP.id not in MG.games, 15)
        deleted = [c for c in h.session.calls if type(c).__name__ == "DeleteMessage" and c.message_id == lobby_mid]
        assert deleted, "رسالة اللوبي لازم تُحذف"
    run(go())


def test_nine_players_get_two_killers_not_three():
    assert M.auto_config(9)[0] == 2
    assert M.auto_config(10)[0] == 2
    assert M.auto_config(11)[0] == 3


def test_five_to_eight_players_get_one_killer():
    for n in range(5, 9):
        assert M.auto_config(n)[0] == 1
    assert M.auto_config(9)[0] == 2


def test_killers_never_exceed_three_and_fifteen_players_is_the_cap():
    for n in range(5, 16):
        assert 1 <= M.auto_config(n)[0] <= 3
    assert M.auto_config(15)[0] == 3
    assert M.MAX_PLAYERS == 15
    try:
        M.Config(killers=4, specials=[]).validate(15)
        assert False, "4 قتلة لازم ترفض"
    except M.ConfigError:
        pass
