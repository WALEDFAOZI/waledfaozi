"""رابط الدعوة الخاص بقناة الاشتراك الإجباري: يُستعمل في الزر، ويُحسب من دخل عنه."""
import asyncio
import datetime as dt

from aiogram.types import Chat, ChatInviteLink, ChatMemberLeft, ChatMemberMember, ChatMemberUpdated, Update, User

from harness import Harness

CH = "@Anime1Galaxy"
CHAT = Chat(id=-1001001, type="channel", username="Anime1Galaxy", title="أنمي")


def join_via(uid, link, chat=CHAT):
    user = User(id=uid, is_bot=False, first_name="U")
    return ChatMemberUpdated(chat=chat, from_user=user, date=dt.datetime.now(),
                             old_chat_member=ChatMemberLeft(user=user), new_chat_member=ChatMemberMember(user=user),
                             invite_link=ChatInviteLink(invite_link=link, creator=user, creates_join_request=False,
                                                        is_primary=False, is_revoked=False) if link else None)


async def feed(h, e, seq=[5000]):
    seq[0] += 1
    await h.dp.feed_update(h.bot, Update(update_id=seq[0], chat_member=e))


def test_gate_button_uses_private_invite_link_and_joins_are_counted_once():
    async def go():
        h = Harness(channel=CH)
        h.session.member = False
        await h.tap(h.user(1), "go")                         # يطلب الاشتراك => يظهر الزر بالرابط الخاص
        prompt = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == 1][-1]
        urls = [b.url for row in prompt.reply_markup.inline_keyboard for b in row if b.url]
        assert urls == ["https://t.me/+TESTLINK1"]
        await h.tap(h.user(1), "go")                         # الرابط يُعاد استعماله ولا يُنشأ من جديد
        assert h.db.get_setting("gate_invite") and h.session.invite_n == 1
        link = "https://t.me/+TESTLINK1"
        await feed(h, join_via(21, link))                    # دخل عبر رابطنا
        await feed(h, join_via(21, link))                    # تكرار لا يُحسب مرتين
        await feed(h, join_via(22, "https://t.me/+OTHER"))   # رابط آخر لا يُحسب
        await feed(h, join_via(23, None))                    # دخل بالبحث العام لا يُحسب
        n = h.db.conn.execute("SELECT COUNT(*) n FROM events WHERE kind='gate_link_join'").fetchone()["n"]
        assert n == 1
        f = h.db.funnel_stats()
        assert f["via_link"] == 1 and f["via_link_7d"] == 1
        await h.say(h.user(1), "/diag")
        assert "https://t.me/+TESTLINK1" in h.session.texts()[-1]
    asyncio.run(go())


def test_gate_falls_back_to_public_link_when_invite_creation_fails():
    async def go():
        h = Harness(channel=CH)
        h.session.member = False

        async def broken(bot, method, timeout=None):
            if type(method).__name__ == "CreateChatInviteLink":
                from aiogram.exceptions import TelegramBadRequest
                raise TelegramBadRequest(method=method, message="Bad Request: not enough rights")
            return await orig(bot, method, timeout)
        orig = h.session.make_request
        h.session.make_request = broken
        await h.tap(h.user(2), "go")
        prompt = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == 2][-1]
        urls = [b.url for row in prompt.reply_markup.inline_keyboard for b in row if b.url]
        assert urls == ["https://t.me/Anime1Galaxy"]
    asyncio.run(go())
