"""أزرار التنقل بين الخاص والمجموعة/القناة في الألعاب.

- زر «العودة» في رسائل الخاص يفتح رسالة اللعبة الحيّة في المكان الذي تجري فيه
  (داخل تعليقات المنشور إن كانت اللعبة فيها، لأن الرسالة الحيّة تكون ردًا على نسخة المنشور).
- زر «افتح الخاص» في رسائل المجموعة/القناة يفتح محادثة البوت فقط، دون أي أمر.
"""
from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup

from .bot import btn, kb
from .texts import t

_INFO: dict[int, tuple[str | None, str]] = {}   # chat_id -> (username, type)
_ME: dict[str, str] = {}


async def bot_name(bot: Bot) -> str:
    if "u" not in _ME:
        _ME["u"] = (await bot.get_me()).username or ""
    return _ME["u"]


async def chat_info(bot: Bot, chat_id: int) -> tuple[str | None, str]:
    if chat_id not in _INFO:
        try:
            ch = await bot.get_chat(chat_id)
            _INFO[chat_id] = (ch.username, ch.type)
        except TelegramAPIError:
            return None, "group"
    return _INFO[chat_id]


def msg_url(chat_id: int, username: str | None, mid: int) -> str:
    if username:
        return f"https://t.me/{username}/{mid}"
    cid = str(chat_id)
    if cid.startswith("-100"):
        cid = cid[4:]
    return f"https://t.me/c/{cid}/{mid}"


async def back_rows(bot: Bot, chat_id: int, mid: int | None, L: str) -> list:
    """صف زر «العودة» إلى رسالة اللعبة الحيّة، أو لا شيء إن لم تكن موجودة."""
    if not mid:
        return []
    username, ctype = await chat_info(bot, chat_id)
    label = t(L, "btn_back_channel") if ctype == "channel" else t(L, "btn_back_group")
    return [[btn(label, url=msg_url(chat_id, username, mid))]]


async def open_private_rows(bot: Bot, L: str) -> list:
    """صف زر «افتح الخاص»: يفتح محادثة البوت فقط."""
    return [[btn(t(L, "btn_open_private"), url=f"https://t.me/{await bot_name(bot)}")]]


def with_rows(markup: InlineKeyboardMarkup, rows: list) -> InlineKeyboardMarkup:
    return kb(*markup.inline_keyboard, *rows)


async def msg_rows(bot: Bot, chat_id: int, mid: int | None, label_key: str, L: str) -> list:
    """زر يفتح رسالة معيّنة في الدردشة (داخل تعليقات المنشور إن كانت الرسالة فيها)."""
    if not mid:
        return []
    username, _ = await chat_info(bot, chat_id)
    return [[btn(t(L, label_key), url=msg_url(chat_id, username, mid))]]
