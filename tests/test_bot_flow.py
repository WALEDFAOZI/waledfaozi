"""اختبار تكاملي للبوت كاملًا بدون تليجرام ولا توكن: جلسة وهمية تسجّل الطلبات."""
import asyncio
import datetime as dt
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import (AnswerCallbackQuery, DeleteMessage, DeleteWebhook, EditMessageText,
                             GetMe, SendMessage, SendPhoto)
from aiogram.types import CallbackQuery, Chat, Message, MessageEntity, Update, User

from otaku_bot.bot import build_router
from otaku_bot.config import Settings
from otaku_bot.db import DB

QPATH = str(Path(__file__).resolve().parent.parent / "data" / "questions.json")


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.n = 100

    async def close(self): ...
    async def stream_content(self, *a, **k): yield b""

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, (SendMessage, EditMessageText, SendPhoto)):
            self.n += 1
            chat_id = getattr(method, "chat_id", 1)
            return Message(message_id=self.n, date=dt.datetime.now(), chat=Chat(id=chat_id, type="private"))
        if isinstance(method, GetMe):
            return User(id=999, is_bot=True, first_name="bot", username="otaku_test_bot")
        return True


def mk_settings():
    return Settings(token="1:fake", db_path=":memory:", questions_path=QPATH,
                    timer_seconds=0, cooldown_minutes=0, admin_ids=())


def run_flow():
    db = DB(":memory:")
    db.load_questions(QPATH)
    s = mk_settings()
    session = FakeSession()
    bot = Bot("1:fake", session=session)
    dp = Dispatcher()
    dp.include_router(build_router(s, db))
    user = User(id=1, is_bot=False, first_name="Waled")
    chat = Chat(id=1, type="private")
    uid = [0]

    def msg(text=None, entities=None):
        return Message(message_id=1, date=dt.datetime.now(), chat=chat, from_user=user,
                       text=text, entities=entities)

    async def feed_cb(data):
        uid[0] += 1
        cb = CallbackQuery(id=str(uid[0]), from_user=user, chat_instance="x", data=data, message=msg("."))
        await dp.feed_update(bot, Update(update_id=uid[0], callback_query=cb))

    async def go():
        uid[0] += 1
        m = msg("/start", [MessageEntity(type="bot_command", offset=0, length=6)])
        await dp.feed_update(bot, Update(update_id=uid[0], message=m))
        await feed_cb("go")
        sess = db.active_session(1)
        assert sess is not None
        sid = sess["id"]
        # كل الإجابات صحيحة
        for pos in range(50):
            row = db.session_question(sid, pos)
            await feed_cb(f"a:{sid}:{pos}:{row['correct_pos']}")
        return sid

    sid = asyncio.run(go())
    return db, session, sid


def test_full_quiz_flow():
    db, session, sid = run_flow()
    s = db.get_session(sid)
    assert s["state"] == "finished"
    # كل الإجابات صحيحة لكن بسرعة < 1ث (مشبوهة) فلا تُحتسب في أفضل نتيجة
    assert s["score"] == 10.0
    assert db.get_user(1)["best_score"] == 0
    kinds = [type(c).__name__ for c in session.calls]
    assert "SendPhoto" in kinds or kinds.count("SendMessage") >= 2   # بطاقة أو نص
    assert kinds.count("AnswerCallbackQuery") == 51  # go + 50 إجابة


def test_cannot_answer_twice_or_other_users_session():
    db = DB(":memory:")
    db.load_questions(QPATH)
    s = mk_settings()
    session = FakeSession()
    bot = Bot("1:fake", session=session)
    dp = Dispatcher()
    dp.include_router(build_router(s, db))
    owner = User(id=1, is_bot=False, first_name="A")
    thief = User(id=2, is_bot=False, first_name="B")
    chat = Chat(id=1, type="private")

    async def go():
        m = Message(message_id=1, date=dt.datetime.now(), chat=chat, from_user=owner)

        def cb(user, data, i):
            return Update(update_id=i, callback_query=CallbackQuery(
                id=str(i), from_user=user, chat_instance="x", data=data, message=m))

        await dp.feed_update(bot, cb(owner, "go", 1))
        sid = db.active_session(1)["id"]
        row = db.session_question(sid, 0)
        await dp.feed_update(bot, cb(thief, f"a:{sid}:0:{row['correct_pos']}", 2))
        assert db.session_question(sid, 0)["user_answer"] is None      # لص: مرفوض
        await dp.feed_update(bot, cb(owner, f"a:{sid}:0:{row['correct_pos']}", 3))
        assert db.session_question(sid, 0)["is_correct"] == 1
        await dp.feed_update(bot, cb(owner, f"a:{sid}:0:0", 4))        # إعادة ضغط: تتجاهل
        assert db.get_session(sid)["current_pos"] == 1
        await dp.feed_update(bot, cb(owner, f"a:{sid}:0:0", 5))        # زر قديم لسؤال سابق
        assert db.get_session(sid)["current_pos"] == 1

    asyncio.run(go())
