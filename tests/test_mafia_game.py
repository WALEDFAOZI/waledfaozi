"""لعبة المافيا على تليجرام: الانضمام، الإعدادات، الليل، النهار، والنتيجة."""
import asyncio
import datetime as dt

import pytest
from aiogram.types import CallbackQuery, Chat, Message, MessageEntity, Update

from harness import Harness, run
from otaku_bot import mafia_game as MG

GROUP = Chat(id=-2001, type="supergroup", title="شلة المافيا")


@pytest.fixture(autouse=True)
def fast():
    old = (MG.LOBBY_SECS, MG.NIGHT_SECS, MG.DAY_SECS, MG.EDIT_GAP, MG.COOLDOWN_SECS)
    MG.LOBBY_SECS, MG.NIGHT_SECS, MG.DAY_SECS, MG.EDIT_GAP, MG.COOLDOWN_SECS = 4, 3, 3, 0.2, 0
    MG.games.clear()
    yield
    MG.LOBBY_SECS, MG.NIGHT_SECS, MG.DAY_SECS, MG.EDIT_GAP, MG.COOLDOWN_SECS = old
    MG.games.clear()


async def gcmd(h, user, text, mid):
    h.uid += 1
    ents = [MessageEntity(type="bot_command", offset=0, length=len(text.split()[0]))]
    m = Message(message_id=mid, date=dt.datetime.now(), chat=GROUP, from_user=user, text=text, entities=ents)
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, message=m))


async def gtap(h, user, data, mid=500):
    h.uid += 1
    m = Message(message_id=mid, date=dt.datetime.now(), chat=GROUP, text=".")
    cb = CallbackQuery(id=str(h.uid), from_user=user, chat_instance="g", data=data, message=m)
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, callback_query=cb))


async def wait_until(cond, timeout=15.0):
    t0 = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - t0 < timeout:
        if cond():
            return True
        await asyncio.sleep(0.1)
    return False


def dms_to(h, uid):
    return [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == uid]


def group_texts(h):
    return [(getattr(c, "text", None) or getattr(c, "caption", None) or "") for c in h.session.calls
            if type(c).__name__ in ("SendMessage", "EditMessageText") and c.chat_id == GROUP.id]


def test_full_game_roles_night_day_and_result():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 7)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        host = users[0]
        await gcmd(h, host, "/mafia", 77)
        g = MG.games[GROUP.id]
        assert g.host_id == 1 and 1 in g.players
        lobby = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == GROUP.id][-1]
        assert lobby.reply_parameters.message_id == 77                       # كل رسالة ترد على صاحب الأمر
        assert "كيف تلعب" in lobby.text                                      # الشرح واضح للمنضم
        for u in users[1:]:
            await gtap(h, u, f"mf:j:{g.gid}")
        await gtap(h, host, f"mf:r:{g.gid}:doctor")                          # الطبيب دور إضافي
        await gtap(h, users[1], f"mf:k:{g.gid}:+")                           # غير المضيف لا يغيّر الإعدادات
        assert g.killers == 1
        await gtap(h, host, f"mf:s:{g.gid}")
        assert await wait_until(lambda: g.state == "night"), g.state
        # كل لاعب تلقّى دوره في الخاص
        assert all(dms_to(h, u.id) for u in users)
        roles = {uid: p.role for uid, p in g.players.items()}
        killer = next(u for u, r in roles.items() if r == "killer")
        doctor = next(u for u, r in roles.items() if r == "doctor")
        citizens = [u for u, r in roles.items() if r == "citizen"]
        victim = citizens[0]
        assert "دورك" in dms_to(h, killer)[0].text and "القاتل" in dms_to(h, killer)[0].text
        await h.tap(next(x for x in users if x.id == killer), f"mf:n:{g.gid}:killer:{victim}")
        await h.tap(next(x for x in users if x.id == doctor), f"mf:n:{g.gid}:doctor:{doctor}")   # الطبيب يحمي نفسه
        assert await wait_until(lambda: g.state == "day"), g.state
        assert not g.players[victim].alive                                  # القتيل مات في الليل
        assert any("وجدوا" in x and "P" in x for x in group_texts(h))
        alive = [u for u in users if g.players[u.id].alive]
        for u in alive:
            if u.id != killer:
                await gtap(h, u, f"mf:v:{g.gid}:{killer}")                  # أربعة أصوات من خمسة أحياء
        assert await wait_until(lambda: g.state == "done"), g.state
        texts = group_texts(h)
        assert any("فاز المواطنون" in x for x in texts)
        assert any("الأدوار" in x for x in texts)
        assert len(h.db.conn.execute("SELECT 1 FROM group_results WHERE chat_id=?", (GROUP.id,)).fetchall()) >= 5
        assert GROUP.id not in MG.games
    run(go())


def test_host_rules_and_invalid_configurations_are_refused():
    async def go():
        h = Harness()
        users = [h.user(i, f"P{i}") for i in range(1, 6)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 80)
        g = MG.games[GROUP.id]
        for u in users[1:]:
            await gtap(h, u, f"mf:j:{g.gid}")
        for _ in range(3):
            await gtap(h, users[0], f"mf:k:{g.gid}:+")                     # 4 قتلة من 5 = مرفوض
        assert g.killers >= 2
        await gtap(h, users[0], f"mf:s:{g.gid}")
        assert g.state == "lobby"                                           # لا تبدأ بإعدادات فاسدة
        await gtap(h, users[0], f"mf:k:{g.gid}:-")
        await gtap(h, users[0], f"mf:r:{g.gid}:doctor")                    # 1 قاتل + طبيب + 3 مواطنين = صالح
        await gtap(h, users[0], f"mf:s:{g.gid}")
        assert await wait_until(lambda: g.state != "lobby")
        g.task.cancel()
        await wait_until(lambda: GROUP.id not in MG.games, 5)
    run(go())


def test_leaving_mid_game_counts_as_elimination_and_cancel_works():
    async def go():
        h = Harness()
        users = [h.user(i, f"P{i}") for i in range(1, 7)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 90)
        g = MG.games[GROUP.id]
        for u in users[1:]:
            await gtap(h, u, f"mf:j:{g.gid}")
        await gtap(h, users[0], f"mf:s:{g.gid}")
        assert await wait_until(lambda: g.state == "night")
        await gtap(h, users[2], f"mf:l:{g.gid}")                          # ينسحب أثناء اللعب
        assert not g.players[3].alive
        await gtap(h, users[0], f"mf:x:{g.gid}")                          # المضيف يلغي
        assert await wait_until(lambda: GROUP.id not in MG.games, 5)
        assert any("أُلغيت" in x for x in group_texts(h))
    run(go())
