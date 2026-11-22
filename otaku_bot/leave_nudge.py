"""رسالة خاصة واحدة لمن يخرج من القناة الإلزامية، إن كان قد بدأ البوت ولم يحظره.

- تعمل فقط إن كان البوت أدمنًا في القناة (تليجرام يرسل تحديثات الأعضاء في هذه الحالة).
- مرة واحدة لكل شخص، وتُسجَّل قبل الإرسال حتى لا تتكرر.
- يمكن إيقافها من لوحة الأدمن (الإعداد leave_nudge).
"""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup

from .texts import t

log = logging.getLogger(__name__)

JOINED = ("member", "administrator", "creator", "restricted")
LEFT = ("left", "kicked")


def enabled(db) -> bool:
    return db.get_setting("leave_nudge", "1") == "1"


async def on_channel_change(ev: ChatMemberUpdated, bot: Bot, db, channel: str) -> bool:
    """يرجع True إن أُرسلت الرسالة."""
    if not channel or ev.chat.type != "channel":
        return False
    if (ev.chat.username or "").lower() != channel.lstrip("@").lower():
        return False
    if ev.old_chat_member.status not in JOINED or ev.new_chat_member.status not in LEFT:
        return False
    if not enabled(db):
        return False
    user = ev.new_chat_member.user
    if user.is_bot or not db.can_message(user.id) or db.has_event(user.id, "left_nudge"):
        return False
    db.log_event(user.id, "left_nudge")                    # قبل الإرسال: لا تتكرر أبدًا
    L = db.get_lang(user.id)
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(L, "btn_channel"), url=f"https://t.me/{channel.lstrip('@')}")]])
    try:
        await bot.send_message(user.id, t(L, "leave_nudge", ch=channel), parse_mode="HTML", reply_markup=markup)
    except TelegramAPIError as e:                          # لم يبدأ البوت أو حظره
        log.info("leave nudge not delivered: %s", type(e).__name__)
        return False
    return True
