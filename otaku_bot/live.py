"""الرسالة الحيّة الواحدة للألعاب الجماعية.

كل لعبة تبدأ بلافتة صورة واحدة، ثم تُعدَّل نفس الرسالة في كل مرحلة:
- التعليق (caption) والأزرار للنص والمراحل.
- الصورة (media) لصور الجولات أو بطاقة النتيجة.
لا تُرسل رسائل جديدة أثناء اللعب ولا تُحذف الرسالة في النهاية.
"""
from __future__ import annotations

import asyncio
import logging
import re

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramRetryAfter
from aiogram.types import BufferedInputFile, InputMediaPhoto, ReplyParameters

from . import card

log = logging.getLogger(__name__)

CAPTION_MAX = 1024          # حد تليجرام للتعليق
_BANNER: dict[str, bytes] = {}
_BANNER_ID: dict[str, str] = {}      # معرّف الملف في تليجرام بعد أول إرسال
_TAG = re.compile(r"<(/?)(b|i|u|s|code|pre|a)\b[^>]*>")


def fit(text: str, limit: int = CAPTION_MAX) -> str:
    """يقصّ النص إلى الحد دون أن يكسر وسوم HTML: يقطع عند سطر، ثم يغلق الوسوم المفتوحة."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 2]
    nl = cut.rfind("\n")
    if nl > limit // 2:
        cut = cut[:nl]
    stack: list[str] = []
    for m in _TAG.finditer(cut):
        name = m.group(2)
        if m.group(1):
            if stack and stack[-1] == name:
                stack.pop()
        else:
            stack.append(name)
    return cut + "…" + "".join(f"</{n}>" for n in reversed(stack))


async def banner(lang: str) -> bytes:
    if lang not in _BANNER:
        _BANNER[lang] = await asyncio.to_thread(card.make_banner, lang)
    return _BANNER[lang]


async def banner_media(lang: str):
    """وسيط اللافتة: معرّف الملف إن عُرف، وإلا بياناتها."""
    return _BANNER_ID.get(lang) or BufferedInputFile(await banner(lang), "banner.jpg")


async def send(bot: Bot, chat_id: int, text: str, markup=None, lang: str = "ar",
               reply_to: int | None = None, thread: int | None = None, on_error=None) -> int | None:
    """يرسل الرسالة الحيّة الوحيدة للعبة: لافتة مع التعليق. يرجع معرّفها أو None."""
    kw = {"reply_markup": markup}
    if reply_to:
        kw["reply_parameters"] = ReplyParameters(message_id=reply_to, allow_sending_without_reply=True)
    if thread:
        kw["message_thread_id"] = thread
    photo = _BANNER_ID.get(lang) or BufferedInputFile(await banner(lang), "banner.jpg")
    for _ in range(2):
        try:
            m = await bot.send_photo(chat_id, photo, caption=fit(text), parse_mode="HTML", **kw)
            if m.photo:
                _BANNER_ID[lang] = m.photo[-1].file_id
            return m.message_id
        except TelegramRetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except TelegramAPIError as e:
            log.warning("live send failed in %s: %s", chat_id, type(e).__name__)
            if on_error:
                on_error(str(e))
            return None
    return None


async def edit(bot: Bot, chat_id: int, mid: int, text: str, markup=None, media=None) -> bool:
    """يعدّل التعليق والأزرار، وإن أُعطيت media يغيّر الصورة أيضًا. True إن نجح أو لم يتغير شيء.
    عند حد تليجرام ينتظر قليلًا ويعيد المحاولة مرة واحدة، حتى لا تضيع آخر حالة (مثل النتيجة النهائية)."""
    for attempt in (1, 2):
        try:
            if media is None:
                await bot.edit_message_caption(chat_id=chat_id, message_id=mid, caption=fit(text),
                                               parse_mode="HTML", reply_markup=markup)
            else:
                await bot.edit_message_media(chat_id=chat_id, message_id=mid,
                                             media=InputMediaPhoto(media=media, caption=fit(text), parse_mode="HTML"),
                                             reply_markup=markup)
            return True
        except TelegramBadRequest as e:
            return "not modified" in str(e).lower()
        except TelegramRetryAfter as e:
            if attempt == 2:
                return False
            await asyncio.sleep(min(e.retry_after, 5))
        except TelegramAPIError:
            return False
    return False
