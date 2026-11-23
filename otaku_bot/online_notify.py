"""إشعار «بدأ طابور لعبة أونلاين»: اختياري (مغلق افتراضيًا)، ويصل لمن فعّله فقط.

الرسالة فيها زر انضمام يفتح الطابور مباشرة. الإشعار يُرسل مرة واحدة عند فتح كل طابور.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from .bot import btn, kb
from .texts import t

log = logging.getLogger(__name__)
KEY = "onnotify:{uid}"
GAP = 0.05          # ثانية بين الرسائل حتى لا نغرق تليجرام


def is_on(db, uid: int) -> bool:
    return db.get_setting(KEY.format(uid=uid)) == "1"


def toggle(db, uid: int) -> bool:
    now = not is_on(db, uid)
    db.set_setting(KEY.format(uid=uid), "1" if now else "0")
    return now


def subscribers(db) -> list[int]:
    out = []
    for k, v in db._settings.items():                  # الإعدادات مخزنة في الذاكرة أيضًا
        if k.startswith("onnotify:") and v == "1":
            out.append(int(k.split(":", 1)[1]))
    return out


async def announce(bot: Bot, db, opener: int, label_key: str, join_data: str,
                   busy: Callable[[int], bool]) -> None:
    """يُرسل لمن فعّل الإشعار: «بدأ طابور {game}، تحب تنضم؟» مع زر انضمام."""
    for uid in subscribers(db):
        if uid == opener or busy(uid):
            continue
        L = db.get_lang(uid)
        try:
            await bot.send_message(uid, t(L, "on_notify_open", game=t(L, label_key)), parse_mode="HTML",
                                   reply_markup=kb([btn(t(L, "on_notify_join"), join_data)]))
        except TelegramAPIError:
            pass
        await asyncio.sleep(GAP)
