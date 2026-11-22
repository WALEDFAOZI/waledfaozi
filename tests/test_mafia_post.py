"""المافيا في تعليقات منشور القناة: اختيار المكان، رابط المنشور، ونسخة المنشور في مجموعة التعليقات."""
import asyncio
import datetime as dt

from aiogram.types import Chat, CallbackQuery, Message, MessageOriginChannel, Update

from harness import Harness, run
from otaku_bot import mafia_game as MG

CH = Chat(id=-1001001, type="channel", username=None, title="قناتي")
DISC = Chat(id=-2002, type="supergroup", title="تعليقات قناتي")


def test_parse_and_comment_links():
    assert MG.parse_post_link("https://t.me/Anime1Galaxy/123") == ("Anime1Galaxy", None, 123)
    assert MG.parse_post_link("t.me/c/1234567890/456") == (None, "1234567890", 456)
    assert MG.parse_post_link("hello") is None
    assert MG.comment_link("Anime1Galaxy", -1001234567890, 123, 77) == "https://t.me/Anime1Galaxy/123?comment=77"
    assert MG.comment_link(None, -1001234567890, 456, 9) == "https://t.me/c/1234567890/456?comment=9"


def test_host_starts_mafia_in_the_comments_of_a_post():
    async def go():
        h = Harness()
        owner = h.user(5, "Owner")
        h.db.upsert_user(5, "Owner")
        h.db.link_channel(CH.id, 5, "قناتي")
        # نسخة المنشور تظهر في مجموعة التعليقات (يستقبلها البوت كرسالة تلقائية)
        origin = MessageOriginChannel(date=dt.datetime.now(), chat=CH, message_id=77)
        copy = Message(message_id=900, date=dt.datetime.now(), chat=DISC, is_automatic_forward=True,
                       forward_origin=origin, text="منشور")
        await h.dp.feed_update(h.bot, Update(update_id=1, message=copy))
        assert h.db.get_post_copy(CH.id, 77) == {"group_id": DISC.id, "copy_id": 900}

        # المضيف يختار: في تعليقات منشور
        h.uid += 1
        cb = CallbackQuery(id="c1", from_user=owner, chat_instance="p", data=f"mf:cp:{CH.id}",
                           message=Message(message_id=1, date=dt.datetime.now(),
                                           chat=Chat(id=5, type="private"), text="."))
        await h.dp.feed_update(h.bot, Update(update_id=2, callback_query=cb))
        await h.say(owner, f"https://t.me/c/1001/77")            # رابط المنشور من القناة
        game = MG.games.get(DISC.id)
        assert game is not None and game.reply_to == 900 and game.scope == "group"
        texts = [c.text or getattr(c, "caption", "") or "" for c in h.session.calls
                 if getattr(c, "chat_id", None) == 5 and hasattr(c, "text")]
        assert any("?comment=900" in x for x in texts), texts
    run(go())


def test_unknown_post_is_refused_and_non_owner_cannot_pick():
    async def go():
        h = Harness()
        owner = h.user(5, "Owner")
        h.db.upsert_user(5, "Owner")
        h.db.link_channel(CH.id, 5, "قناتي")
        other = h.user(9, "Other")
        h.uid += 1
        cb = CallbackQuery(id="c2", from_user=other, chat_instance="p", data=f"mf:cp:{CH.id}",
                           message=Message(message_id=1, date=dt.datetime.now(),
                                           chat=Chat(id=9, type="private"), text="."))
        await h.dp.feed_update(h.bot, Update(update_id=3, callback_query=cb))
        await h.say(owner, "x")                                   # لا توجد جلسة اختيار للمالك
        cb2 = CallbackQuery(id="c3", from_user=owner, chat_instance="p", data=f"mf:cp:{CH.id}",
                            message=Message(message_id=2, date=dt.datetime.now(),
                                            chat=Chat(id=5, type="private"), text="."))
        await h.dp.feed_update(h.bot, Update(update_id=4, callback_query=cb2))
        await h.say(owner, "https://t.me/c/1001/999")              # منشور غير موجود عندنا
        assert MG.games.get(DISC.id) is None
    run(go())


def test_direct_channel_choice_still_opens_the_lobby_in_the_channel():
    async def go():
        h = Harness()
        owner = h.user(5, "Owner")
        h.db.upsert_user(5, "Owner")
        h.db.link_channel(CH.id, 5, "قناتي")
        h.uid += 1
        cb = CallbackQuery(id="c9", from_user=owner, chat_instance="p", data=f"mf:cc:{CH.id}",
                           message=Message(message_id=3, date=dt.datetime.now(),
                                           chat=Chat(id=5, type="private"), text="."))
        await h.dp.feed_update(h.bot, Update(update_id=9, callback_query=cb))
        game = MG.games.get(CH.id)
        assert game is not None and game.scope == "channel"
        MG.games.clear()
    run(go())
