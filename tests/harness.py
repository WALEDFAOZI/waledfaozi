"""أدوات اختبار: بوت تليجرام وهمي يسجّل الطلبات ويسمح بتمرير تحديثات حقيقية للموزِّع."""
import asyncio
import datetime as dt
from dataclasses import replace
from pathlib import Path

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import (EditMessageMedia, GetChatMember, GetMe, SendDocument, SendMessage,
                             SendPhoto, EditMessageText)
from aiogram.types import (CallbackQuery, Chat, ChatMemberLeft, ChatMemberMember, Message,
                           MessageEntity, Update, User)

from otaku_bot.app import build_dispatcher
from otaku_bot.config import Settings
from otaku_bot.ctx import Ctx
from otaku_bot.db import DB

QPATH = str(Path(__file__).resolve().parent.parent / "data" / "questions.json")


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.n = 100
        self.member = True          # True / False / None(خطأ)
        self.bad_photos = set()     # صور تُرفض كأن الرابط معطوب

    async def close(self): ...
    async def stream_content(self, *a, **k): yield b""

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, (SendMessage, EditMessageText, SendPhoto, EditMessageMedia, SendDocument)):
            bad = (isinstance(method, SendPhoto) and str(method.photo) in self.bad_photos) or \
                  (isinstance(method, EditMessageMedia) and str(method.media.media) in self.bad_photos)
            if bad:
                raise TelegramBadRequest(method=method, message="Bad Request: failed to get HTTP URL content")
            self.n += 1
            chat_id = getattr(method, "chat_id", 1)
            return Message(message_id=self.n, date=dt.datetime.now(),
                           chat=Chat(id=chat_id, type="private")).as_(bot)
        if isinstance(method, GetChatMember):
            if self.member is None:
                raise TelegramBadRequest(method=method, message="Bad Request: chat not found")
            u = User(id=method.user_id, is_bot=False, first_name="x")
            return ChatMemberMember(user=u) if self.member else ChatMemberLeft(user=u)
        if isinstance(method, GetMe):
            return User(id=999, is_bot=True, first_name="bot", username="otaku_test_bot")
        return True

    def texts(self):
        return [getattr(c, "text", None) or getattr(c, "caption", None) or "" for c in self.calls]

    def sent_to(self, chat_id):
        return [c for c in self.calls if isinstance(c, (SendMessage, SendPhoto)) and c.chat_id == chat_id]


class Harness:
    def __init__(self, channel="", timer=0, cooldown=0, admin_ids=()):
        self.db = DB(":memory:")
        self.db.load_questions(QPATH)
        s = Settings(token="1:fake", db_path=":memory:", questions_path=QPATH, timer_seconds=timer,
                     cooldown_minutes=cooldown, admin_ids=tuple(admin_ids), required_channel=channel)
        self.ctx = Ctx(s, self.db)
        self.session = FakeSession()
        self.bot = Bot("1:fake", session=self.session)
        self.dp = build_dispatcher(self.ctx)
        self.uid = 0

    def user(self, i, name="U", lang="ar"):
        return User(id=i, is_bot=False, first_name=name, language_code=lang)

    def _msg(self, user, text=None, photo=None, caption=None):
        ents = [MessageEntity(type="bot_command", offset=0, length=len(text.split()[0]))] \
            if text and text.startswith("/") else None
        return Message(message_id=1, date=dt.datetime.now(), chat=Chat(id=user.id, type="private"),
                       from_user=user, text=text, entities=ents, photo=photo, caption=caption)

    async def say(self, user, text):
        self.uid += 1
        await self.dp.feed_update(self.bot, Update(update_id=self.uid, message=self._msg(user, text)))

    async def photo(self, user, file_id="FILEID", caption=None):
        from aiogram.types import PhotoSize
        self.uid += 1
        m = self._msg(user, None, photo=[PhotoSize(file_id=file_id, file_unique_id="u", width=1, height=1)],
                      caption=caption)
        await self.dp.feed_update(self.bot, Update(update_id=self.uid, message=m))

    async def tap(self, user, data):
        self.uid += 1
        cb = CallbackQuery(id=str(self.uid), from_user=user, chat_instance="x", data=data,
                           message=self._msg(user, "."))
        await self.dp.feed_update(self.bot, Update(update_id=self.uid, callback_query=cb))

    async def play(self, user, correct=True, limit=None):
        """يلعب الجلسة النشطة حتى تنتهي؛ يرجع معرّف الجلسة."""
        sid = self.db.active_session(user.id)["id"]
        done = 0
        while True:
            s = self.db.get_session(sid)
            if s["state"] != "active" or (limit is not None and done >= limit):
                return sid
            pos = s["current_pos"]
            row = self.db.session_question(sid, pos)
            choice = row["correct_pos"] if correct else (row["correct_pos"] + 1) % 4
            await self.tap(user, f"a:{sid}:{pos}:{choice}")
            done += 1


def run(coro):
    return asyncio.run(coro)
