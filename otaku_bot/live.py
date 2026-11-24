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
# عنوان اللافتة حسب نوع اللعبة: (عربي، إنجليزي)
TITLES = {
    "quiz": ("اختبار الأوتاكو", "OTAKU QUIZ"), "sudden": ("الموت المفاجئ", "SUDDEN DEATH"),
    "tf": ("صح أم خطأ", "TRUE OR FALSE"), "song": ("خمّن الأغنية", "ANIME SONG"),
    "char": ("من هي الشخصية؟", "WHO IS IT?"), "quote": ("من قال الاقتباس؟", "QUOTE GUESS"),
    "ord": ("أيّها أقدم؟", "WHICH IS OLDER?"), "images": ("أسئلة صور", "PICTURE QUIZ"),
    "mafia": ("المافيا", "MAFIA"), "spy": ("برا السالفة", "ODD ONE OUT"),
    "xo": ("إكس أو", "TIC TAC TOE"), "rps": ("حجرة ورقة مقص", "ROCK PAPER SCISSORS"),
    "c4": ("أربعة في صف", "CONNECT FOUR"),
}
# شكل كل لعبة في اللافتة: تعبير الشخصية، وسطر الوصف (عربي، إنجليزي)
KIND_STYLE = {
    "quiz": ("crown", "1400+ سؤال · ألعاب · تحديات", "1400+ questions · games · challenges"),
    "sudden": ("sweat", "آخر من يبقى يفوز!", "Last one standing wins!"),
    "tf": ("happy", "صح أو خطأ؟ بسرعة!", "True or false? Quick!"),
    "song": ("star", "خمّن الأنمي من الأغنية", "Guess the anime from the song"),
    "char": ("dizzy", "من هي هذي الشخصية؟", "Who is this character?"),
    "quote": ("happy", "من قال هذا الاقتباس؟", "Who said this quote?"),
    "ord": ("smile", "رتّب الأنمي حسب السنة", "Order the anime by year"),
    "images": ("star", "خمّن من الصورة", "Guess from the picture"),
    "xo": ("happy", "أول من يكمل ثلاثة يفوز!", "First to three in a row wins!"),
    "rps": ("smile", "أفضل من 3 جولات", "Best of three rounds"),
    "c4": ("star", "أربعة متتالية قبل خصمك!", "Four in a row before your rival!"),
}
_BANNER: dict[tuple[str, str], bytes] = {}
_BANNER_ID: dict[tuple[str, str], str] = {}      # معرّف الملف في تليجرام بعد أول إرسال
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


async def banner(lang: str, kind: str = "quiz") -> bytes:
    key = (lang, kind if kind in TITLES else "quiz")
    if key not in _BANNER:
        if key[1] == "mafia":
            _BANNER[key] = await asyncio.to_thread(card.make_mafia_banner, lang)
        elif key[1] == "spy":
            _BANNER[key] = await asyncio.to_thread(card.make_spy_banner, lang)
        else:
            ar, en = TITLES[key[1]]
            mood, tag_ar, tag_en = KIND_STYLE.get(key[1], KIND_STYLE["quiz"])
            _BANNER[key] = await asyncio.to_thread(card.make_banner, lang, "@Otaku1GalaxyBot", ar, en,
                                                   mood, tag_ar, tag_en)
    return _BANNER[key]


async def banner_media(lang: str, kind: str = "quiz"):
    """وسيط اللافتة: معرّف الملف إن عُرف، وإلا بياناتها."""
    key = (lang, kind if kind in TITLES else "quiz")
    return _BANNER_ID.get(key) or BufferedInputFile(await banner(lang, kind), "banner.jpg")


async def send(bot: Bot, chat_id: int, text: str, markup=None, lang: str = "ar",
               reply_to: int | None = None, thread: int | None = None, on_error=None, kind: str = "quiz") -> int | None:
    """يرسل الرسالة الحيّة الوحيدة للعبة: لافتة مع التعليق. يرجع معرّفها أو None."""
    kw = {"reply_markup": markup}
    if reply_to:
        kw["reply_parameters"] = ReplyParameters(message_id=reply_to, allow_sending_without_reply=True)
    if thread:
        kw["message_thread_id"] = thread
    key = (lang, kind if kind in TITLES else "quiz")
    photo = _BANNER_ID.get(key) or BufferedInputFile(await banner(lang, kind), "banner.jpg")
    for _ in range(2):
        try:
            m = await bot.send_photo(chat_id, photo, caption=fit(text), parse_mode="HTML", **kw)
            if m.photo:
                _BANNER_ID[key] = m.photo[-1].file_id
            return m.message_id
        except TelegramRetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 10))
        except TelegramAPIError as e:
            log.warning("live send failed in %s: %s", chat_id, type(e).__name__)
            if on_error:
                on_error(str(e))
            return None
    return None


GONE_MARKERS = ("message to edit not found", "message can't be edited", "message_id_invalid", "message to delete not found",
                "message is not found")


async def edit(bot: Bot, chat_id: int, mid: int, text: str, markup=None, media=None, on_gone=None) -> bool:
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
            low = str(e).lower()
            if on_gone and any(m in low for m in GONE_MARKERS):   # الرسالة الحيّة حُذفت: نبلّغ المستدعي
                on_gone()
                return False
            return "not modified" in low
        except TelegramRetryAfter as e:
            if attempt == 2:
                return False
            await asyncio.sleep(min(e.retry_after, 5))
        except TelegramAPIError:
            return False
    return False


async def inline_photo_id(bot: Bot, db, upload_chat: int | None, lang: str, kind: str) -> str | None:
    """معرّف صورة اللافتة لنتائج الوضع الداخلي (بدون رابط عام). يُرفع مرة واحدة لمحادثة الأدمن ثم يُحذف الرسالة، ويُحفظ المعرّف."""
    key = f"inl_photo:{kind}:{lang}"
    saved = db.get_setting(key)
    if saved:
        return saved
    if not upload_chat:
        return None
    try:
        data = await banner(lang, kind)
        m = await bot.send_photo(upload_chat, BufferedInputFile(data, "banner.jpg"))
    except Exception:  # noqa: BLE001  (لا لافتة = نتيجة نصية كالمعتاد)
        log.warning("inline photo upload failed for %s", kind)
        return None
    file_id = m.photo[-1].file_id if m.photo else None
    try:
        await bot.delete_message(upload_chat, m.message_id)
    except TelegramAPIError:
        pass
    if file_id:
        db.set_setting(key, file_id)
    return file_id
