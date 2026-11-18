"""ألعاب المجموعات: غرفة انتظار، أسئلة بعدّاد، ردود على صاحب الأمر، هوية القناة/المجموعة، الصلاحيات."""
import asyncio
import datetime as dt

import pytest
from aiogram.types import CallbackQuery, Chat, Message, MessageEntity, Update, User

from harness import Harness, run
from otaku_bot import group

GROUP = Chat(id=-1001, type="supergroup", title="شلة الأوتاكو")


@pytest.fixture(autouse=True)
def fast():
    old = (group.LOBBY_SECONDS, group.Q_SECONDS, group.PAUSE, group.CHAT_COOLDOWN, group.START_COOLDOWN)
    group.LOBBY_SECONDS, group.Q_SECONDS, group.PAUSE, group.CHAT_COOLDOWN, group.START_COOLDOWN = 0.5, 0.6, 0.02, 0, 0
    yield
    group.LOBBY_SECONDS, group.Q_SECONDS, group.PAUSE, group.CHAT_COOLDOWN, group.START_COOLDOWN = old


def gmsg(user, text, mid=7, chat=GROUP, sender_chat=None, reply_to=None):
    ents = [MessageEntity(type="bot_command", offset=0, length=len(text.split()[0]))] if text.startswith("/") else None
    return Message(message_id=mid, date=dt.datetime.now(), chat=chat, from_user=user, text=text, entities=ents,
                   sender_chat=sender_chat, reply_to_message=reply_to)


async def gsay(h, user, text, mid=7, **kw):
    h.uid += 1
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, message=gmsg(user, text, mid, **kw)))


async def gtap(h, user, data, msg_id=500, reply_to=None):
    h.uid += 1
    m = Message(message_id=msg_id, date=dt.datetime.now(), chat=GROUP, text=".", reply_to_message=reply_to)
    cb = CallbackQuery(id=str(h.uid), from_user=user, chat_instance="g", data=data, message=m)
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, callback_query=cb))


def sent(h):
    return [c for c in h.session.calls if type(c).__name__ in ("SendMessage", "SendPhoto") and c.chat_id == GROUP.id]


def buttons(call):
    return [b.callback_data for row in call.reply_markup.inline_keyboard for b in row] if call.reply_markup else []


def last_with(h, prefix):
    for c in reversed(sent(h)):
        if any((d or "").startswith(prefix) for d in buttons(c)):
            return c
    return None


async def play_out(h, users, timeout=8.0):
    """يضغط (الخيار 0) لكل لاعب على كل سؤال جديد حتى تنتهي اللعبة."""
    done, t0 = set(), asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - t0 < timeout:
        if any("انتهت اللعبة" in (c.text or "") for c in sent(h) if type(c).__name__ == "SendMessage"):
            return True
        c = last_with(h, "gp:a:")
        if c is not None and id(c) not in done:
            done.add(id(c))
            data = [d for d in buttons(c) if d.startswith("gp:a:")][0]
            for u in users:
                await gtap(h, u, data)
        await asyncio.sleep(0.05)
    return False


def start_lobby(h, host, kind="quiz", mid=7, **kw):
    return gsay(h, host, f"/{kind}", mid, **kw)


def test_full_game_replies_to_command_and_saves_results():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await start_lobby(h, a, "quiz", mid=77)
        lobby = sent(h)[0]
        gid = buttons(lobby)[0].split(":")[2]
        assert "Ali" in lobby.text and lobby.reply_parameters.message_id == 77
        await gtap(h, a, f"gp:j:{gid}")
        await gtap(h, b, f"gp:j:{gid}")
        await gtap(h, b, f"gp:j:{gid}")                         # انضمام مكرر لا يضاعفه
        assert await play_out(h, [a, b]), "اللعبة لم تنتهِ"
        msgs = sent(h)
        assert len(msgs) >= 12                                  # غرفة + 10 أسئلة + نهاية
        assert all(c.reply_parameters and c.reply_parameters.message_id == 77 for c in msgs)   # الرد على صاحب الأمر دائمًا
        final = [c for c in msgs if "انتهت اللعبة" in (c.text or "")][0]
        assert "Ali" in final.text and "Bob" in final.text
        assert len(h.db.conn.execute("SELECT 1 FROM group_results WHERE chat_id=?", (GROUP.id,)).fetchall()) == 2
        await gsay(h, a, "/gtop", mid=80)
        assert "متصدرو المجموعة" in sent(h)[-1].text and sent(h)[-1].reply_parameters.message_id == 80
        assert h.db.get_user(1)["best_score"] == 0               # لا يمس التقييم الفردي
    run(go())


def test_too_few_players_busy_and_stop():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await start_lobby(h, a)
        await start_lobby(h, b, mid=9)                          # لعبة شغالة
        assert any("فيه لعبة شغالة" in (c.text or "") for c in sent(h))
        await asyncio.sleep(0.9)
        edits = [c for c in h.session.calls if type(c).__name__ == "EditMessageText"]
        assert any("ما اكتمل العدد" in e.text for e in edits)
        # إيقاف: غير المضيف وغير الأدمن مرفوض، والمضيف مقبول
        await start_lobby(h, a, mid=11)
        await gsay(h, b, "/gstop", mid=12)
        assert any("لصاحب الأمر" in (c.text or "") for c in sent(h))
        await gsay(h, a, "/gstop", mid=13)
        await asyncio.sleep(0.1)
        assert any("تم إيقاف اللعبة" in (c.text or "") for c in sent(h))
        h.session.admins = {2}
        await start_lobby(h, a, mid=14)
        await gsay(h, b, "/gstop", mid=15)                      # أدمن المجموعة يقدر
        await asyncio.sleep(0.1)
        assert sum("تم إيقاف اللعبة" in (c.text or "") for c in sent(h)) == 2
    run(go())


def test_channel_and_anonymous_admin_are_registered_by_name():
    async def go():
        h = Harness()
        chan = Chat(id=-100777, type="channel", title="قناة الأنمي")
        ch_user = User(id=136817688, is_bot=True, first_name="Channel")
        await start_lobby(h, ch_user, mid=21, sender_chat=chan)
        assert "قناة الأنمي" in sent(h)[0].text and sent(h)[0].reply_parameters.message_id == 21
        await gsay(h, ch_user, "/gstop", mid=22, sender_chat=GROUP)       # مجموعة (أدمن مخفي) يقدر يوقف
        await asyncio.sleep(0.1)
        h2 = Harness()
        anon = User(id=1087968824, is_bot=True, first_name="Group")
        await start_lobby(h2, anon, mid=31, sender_chat=GROUP)
        assert "شلة الأوتاكو" in sent(h2)[0].text
    run(go())


def test_bot_admin_is_hidden_and_excluded_from_group_board():
    async def go():
        h = Harness()
        owner, b = h.user(9, "OwnerReal"), h.user(2, "Bob")
        h.db.upsert_user(9, "OwnerReal"); h.db.add_admin(9, owner=True)
        await start_lobby(h, b, mid=41)
        gid = buttons(sent(h)[0])[0].split(":")[2]
        await gtap(h, owner, f"gp:j:{gid}")
        await gtap(h, b, f"gp:j:{gid}")
        assert await play_out(h, [owner, b])
        everything = " ".join((c.text or "") for c in sent(h))
        assert "OwnerReal" not in everything and "مجهول" in everything
        assert [r["name"] for r in h.db.group_top(GROUP.id)] == ["Bob"]
    run(go())


def test_private_features_do_not_leak_into_groups_and_menu_flow():
    async def go():
        h = Harness(admin_ids=(9,))
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await gsay(h, a, "/start")
        assert any("/play" in (c.text or "") for c in sent(h)) and not any(type(c).__name__ == "SendPhoto" for c in sent(h))
        n = len(h.session.calls)
        await gsay(h, h.user(9, "Boss"), "/admin")
        await gsay(h, a, "/top")
        assert len(h.session.calls) == n                         # لا شيء من لوحة الأدمن/الخاص يظهر في المجموعة
        # قائمة الاختيار: غير صاحب الأمر مرفوض
        cmd = gmsg(a, "/play", mid=51)
        await gsay(h, a, "/play", mid=51)
        menu = sent(h)[-1]
        assert menu.reply_parameters.message_id == 51 and "gp:n:quiz" in buttons(menu)
        await gtap(h, b, "gp:n:quiz", reply_to=cmd)
        assert not any("بعد" in (c.text or "") and "تبدأ" in (c.text or "") for c in sent(h))
        await gtap(h, a, "gp:n:tf", reply_to=cmd)
        lobby = [c for c in sent(h) if "تبدأ بعد" in (c.text or "")][-1]
        assert "صح أم غلط" in lobby.text and lobby.reply_parameters.message_id == 51
    run(go())


def test_subscription_required_to_join_and_toggle_off():
    async def go():
        h = Harness(channel="@Anime1Galaxy")
        h.session.member = True
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await start_lobby(h, a)
        gid = buttons(sent(h)[0])[0].split(":")[2]
        h.session.member = False
        before = len(sent(h))
        await gtap(h, b, f"gp:j:{gid}")
        assert len(sent(h)) == before                            # تنبيه فقط، لا رسالة في المجموعة
        h.session.member = True
        await gtap(h, b, f"gp:j:{gid}")
        await gsay(h, a, "/gstop", mid=8)
        await asyncio.sleep(0.1)
        h.db.set_setting("grp_enabled", "0")
        await asyncio.sleep(0.05)
        await start_lobby(h, a, mid=61)
        assert any("متوقفة" in (c.text or "") for c in sent(h))
    run(go())


def test_every_game_kind_builds_and_sudden_eliminates():
    async def go():
        for kind in ("quiz", "sudden", "tf", "song", "char", "quote", "order"):
            h = Harness()
            a, b = h.user(1, "Ali"), h.user(2, "Bob")
            await start_lobby(h, a, kind, mid=70)
            gid = buttons(sent(h)[0])[0].split(":")[2]
            await gtap(h, a, f"gp:j:{gid}")
            await gtap(h, b, f"gp:j:{gid}")
            assert await play_out(h, [a, b], timeout=12), kind
            assert all(c.reply_parameters.message_id == 70 for c in sent(h)), kind
    run(go())
