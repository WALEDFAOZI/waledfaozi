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
    old = (MG.LOBBY_SECS, MG.NIGHT_SECS, MG.DAY_SECS, MG.DISCUSS_SECS, MG.EDIT_GAP, MG.COOLDOWN_SECS)
    MG.LOBBY_SECS, MG.NIGHT_SECS, MG.DAY_SECS, MG.DISCUSS_SECS, MG.EDIT_GAP, MG.COOLDOWN_SECS = 4, 3, 3, 1, 0.2, 0
    MG.games.clear()
    yield
    MG.LOBBY_SECS, MG.NIGHT_SECS, MG.DAY_SECS, MG.DISCUSS_SECS, MG.EDIT_GAP, MG.COOLDOWN_SECS = old
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
            if type(c).__name__ in ("SendMessage", "SendPhoto", "EditMessageText", "EditMessageCaption", "EditMessageMedia")
            and c.chat_id == GROUP.id]


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
        assert g.host_id == 1 and 1 not in g.players                         # المضيف يُضاف إن انضم فقط
        lobby = [c for c in h.session.calls if type(c).__name__ in ("SendMessage", "SendPhoto") and c.chat_id == GROUP.id][-1]
        lobby_text = getattr(lobby, "text", None) or getattr(lobby, "caption", None) or ""
        assert lobby.reply_parameters.message_id == 77                       # كل رسالة ترد على صاحب الأمر
        assert "المافيا" in lobby_text and "شرح اللعبة" in lobby_text         # رسالة البدء مرتبة وتدل على الشرح
        assert "كيف تلعب" not in lobby_text                                  # الشرح الكامل في الخاص لا في القروب
        assert "المضيف" not in lobby_text                                    # لا يظهر اسم المضيف في الانتظار
        lobby_buttons = [b for row in lobby.reply_markup.inline_keyboard for b in row]
        assert all(b.callback_data is None or b.callback_data.startswith("mf:l:") for b in lobby_buttons)   # لا أزرار إعداد في القروب
        assert any(b.url and "start=mf_" in b.url for b in lobby_buttons)    # زر انضم يفتح الخاص
        assert any(b.url and b.url.endswith("start=mfh") for b in lobby_buttons)  # زر شرح اللعبة يفتح الخاص
        for u in users[1:]:
            await h.say(u, f"/start mf_{g.gid}")                             # الانضمام يمر بالخاص
        assert len(g.players) == 5 and 1 not in g.players                    # المضيف لم ينضم تلقائيًا
        await h.say(host, f"/start mf_{g.gid}")
        assert 1 in g.players
        await h.tap(host, f"mf:r:{g.gid}:doctor")                            # الإعدادات في خاص المضيف
        await h.tap(users[1], f"mf:k:{g.gid}:+")                             # غير المضيف لا يغيّر الإعدادات
        assert g.killers == 1
        await h.tap(host, f"mf:s:{g.gid}")
        assert await wait_until(lambda: g.state == "night"), g.state
        # كل لاعب تلقّى دوره في الخاص
        assert all(any("دورك" in (c.text or "") for c in dms_to(h, u.id)) for u in users)
        roles = {uid: p.role for uid, p in g.players.items()}
        killer = next(u for u, r in roles.items() if r == "killer")
        doctor = next(u for u, r in roles.items() if r == "doctor")
        citizens = [u for u, r in roles.items() if r == "citizen"]
        victim = citizens[0]
        role_dm = [c.text for c in dms_to(h, killer) if "دورك" in (c.text or "")]
        assert role_dm and "القاتل" in role_dm[-1]
        await h.tap(next(x for x in users if x.id == killer), f"mf:n:{g.gid}:killer:{victim}")
        await h.tap(next(x for x in users if x.id == doctor), f"mf:n:{g.gid}:doctor:{doctor}")   # الطبيب يحمي نفسه
        assert await wait_until(lambda: g.voting), g.state
        assert not g.players[victim].alive                                  # القتيل مات في الليل
        assert any("سقط" in x and "P" in x for x in group_texts(h))
        new_msgs = [c for c in h.session.calls if type(c).__name__ in ("SendMessage", "SendPhoto") and c.chat_id == GROUP.id]
        assert len(new_msgs) >= 4                # اللوبي + الليل + النهار + الصباح ...: كل مرحلة رسالة جديدة
        alive = [u for u in users if g.players[u.id].alive]
        for u in alive:
            if u.id != killer:
                await gtap(h, u, f"mf:v:{g.gid}:{killer}")                  # أربعة أصوات من خمسة أحياء
                if u is users[0]:
                    assert any("ما زالوا يترددون" in x for x in group_texts(h))   # الرسالة تقول من لم يصوّت بعد
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
        for u in users:
            await h.say(u, f"/start mf_{g.gid}")
        for _ in range(3):
            await h.tap(users[0], f"mf:k:{g.gid}:+")                       # 4 قتلة من 5 = مرفوض
        assert g.killers >= 2
        await h.tap(users[0], f"mf:s:{g.gid}")
        assert g.state == "lobby"                                           # لا تبدأ بإعدادات فاسدة
        await h.tap(users[0], f"mf:k:{g.gid}:-")
        await h.tap(users[0], f"mf:r:{g.gid}:doctor")                      # 1 قاتل + طبيب + 3 مواطنين = صالح
        await h.tap(users[0], f"mf:s:{g.gid}")
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
        for u in users:
            await h.say(u, f"/start mf_{g.gid}")
        await h.tap(users[0], f"mf:s:{g.gid}")
        assert await wait_until(lambda: g.state == "night")
        await gtap(h, users[2], f"mf:l:{g.gid}")                          # ينسحب أثناء اللعب
        assert not g.players[3].alive
        await h.tap(users[0], f"mf:x:{g.gid}")                            # المضيف يلغي من خاصه
        assert await wait_until(lambda: GROUP.id not in MG.games, 5)
        assert any("أُلغيت" in x for x in group_texts(h))
    run(go())


def test_help_deep_link_sends_full_explanation_in_private():
    h = Harness()

    async def go():
        user = h.user(41, "Helper")
        h.db.upsert_user(user.id, user.first_name)
        await h.say(user, "/start mfh")
        msgs = dms_to(h, user.id)
        assert msgs, "شرح اللعبة لازم يوصل في الخاص"
        text = msgs[-1].text
        assert "دليل اللعبة الكامل" in text and "الهدف" in text and "الليل" in text
        assert len(text) <= 4096
    run(go())


def test_lobby_countdown_ticks_down_without_joins():
    h = Harness()
    old_secs, old_tick = MG.LOBBY_SECS, MG.LOBBY_TICK

    async def go():
        h.db.fast_answer_ratio = lambda sid: 0.0
        host = h.user(1, "Host")
        h.db.upsert_user(host.id, host.first_name)
        await gcmd(h, host, "/mafia", 77)
        g = MG.games[GROUP.id]
        assert await wait_until(lambda: g.lobby_secs > 0 and g.state == "lobby", 3)
        await asyncio.sleep(2.3)                                  # بلا أي انضمام
        import re
        nums = []
        for c in h.session.calls:
            if type(c).__name__ in ("EditMessageText", "EditMessageCaption") and c.chat_id == GROUP.id:
                m = re.search(r"تبدأ بعد (\d+) ثانية", getattr(c, "text", None) or getattr(c, "caption", None) or "")
                if m:
                    nums.append(int(m.group(1)))
        assert len(nums) >= 2 and nums[-1] < nums[0], nums        # العدّاد ينزل
        g.start_now = True
    try:
        MG.LOBBY_SECS, MG.LOBBY_TICK = 30, 0.5
        run(go())
    finally:
        MG.LOBBY_SECS, MG.LOBBY_TICK = old_secs, old_tick


def test_lobby_timeout_starts_the_game_without_host_pressing_start():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 6)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/mafia", 61)
        g = MG.games[GROUP.id]
        for u in users:                                                  # المضيف يُحسب لاعبًا إن انضم
            await h.say(u, f"/start mf_{g.gid}")
        assert await wait_until(lambda: g.state == "night", 15)         # انتهى الوقت: تبدأ مباشرة بدون ضغط «ابدأ»
        assert not g.start_now
    run(go())


def test_killers_are_told_who_their_fellow_killers_are():
    from otaku_bot import texts
    txt = texts.t("ar", "mo_killer_mates", names="أحمد")
    assert "أحمد" in txt and "القتلة" in txt

