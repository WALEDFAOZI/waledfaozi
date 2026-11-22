"""رسالة خاصة واحدة لمن يخرج من القناة الإلزامية."""
import asyncio
import datetime as dt

from aiogram.types import Chat, ChatMemberLeft, ChatMemberMember, ChatMemberUpdated, Update, User

from harness import Harness

CH = "@Anime1Galaxy"
CHAT = Chat(id=-1001001, type="channel", username="Anime1Galaxy", title="أنمي")


def ev(uid, old, new, chat=CHAT):
    user = User(id=uid, is_bot=False, first_name="U")
    old_m = ChatMemberMember(user=user) if old == "member" else ChatMemberLeft(user=user)
    new_m = ChatMemberMember(user=user) if new == "member" else ChatMemberLeft(user=user)
    return ChatMemberUpdated(chat=chat, from_user=user, date=dt.datetime.now(), old_chat_member=old_m, new_chat_member=new_m)


async def feed(h, e, uid_seq=[1000]):
    uid_seq[0] += 1
    await h.dp.feed_update(h.bot, Update(update_id=uid_seq[0], chat_member=e))


def nudges(h, uid):
    return [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == uid]


def test_user_who_started_the_bot_gets_one_message_on_leaving():
    async def go():
        h = Harness(channel=CH)
        h.session.member = True
        h.db.upsert_user(21, "Ann")
        await feed(h, ev(21, "member", "left"))
        msgs = nudges(h, 21)
        assert len(msgs) == 1 and "غادرت" in msgs[0].text
        await feed(h, ev(21, "member", "left"))                # خرج مرة أخرى
        assert len(nudges(h, 21)) == 1                         # لا تكرار أبدًا
    asyncio.run(go())


def test_user_who_never_started_the_bot_gets_nothing():
    async def go():
        h = Harness(channel=CH)
        await feed(h, ev(22, "member", "left"))
        assert nudges(h, 22) == []
    asyncio.run(go())


def test_joining_or_other_channels_do_nothing():
    async def go():
        h = Harness(channel=CH)
        h.db.upsert_user(23, "Ben")
        await feed(h, ev(23, "left", "member"))                           # انضم
        other = Chat(id=-1002002, type="channel", username="Other", title="x")
        await feed(h, ev(23, "member", "left", chat=other))               # قناة أخرى
        assert nudges(h, 23) == []
    asyncio.run(go())


def test_blocked_users_and_admin_toggle_are_respected():
    async def go():
        h = Harness(channel=CH)
        h.db.upsert_user(24, "Cat")
        h.db.mark_blocked(24)
        await feed(h, ev(24, "member", "left"))
        assert nudges(h, 24) == []
        h.db.upsert_user(25, "Dan")
        h.db.set_setting("leave_nudge", "0")
        await feed(h, ev(25, "member", "left"))
        assert nudges(h, 25) == []
    asyncio.run(go())
