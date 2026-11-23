"""لعبة «كت»: تكتب «كت» فيصلك سؤال عن الأنمي، وزر «🎲 سؤال آخر» يعطيك غيره (بنك 1000 سؤال).

تعمل في الخاص وفي المجموعات. لا تُكرر السؤال للشخص حتى يستنفد البنك كله.
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from .bot import btn, esc, kb
from .config import ROOT
from .texts import t

log = logging.getLogger(__name__)
TRIGGER = re.compile(r"^\s*(كت|kt)\s*$", re.IGNORECASE)


@lru_cache(maxsize=1)
def questions() -> list[dict]:
    path = ROOT / "data" / "kt_questions.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.exception("kt: cannot load %s", path)
        return []


def next_question(qs: list[dict], seen: set, rng) -> dict | None:
    """سؤال لم يُعرض لهذا الشخص من قبل. إن استُنفدت القائمة تبدأ من جديد."""
    if not qs:
        return None
    if len(seen) >= len(qs):
        seen.clear()
    q = rng.choice([x for x in qs if x["id"] not in seen])
    seen.add(q["id"])
    return q


def build_kt_router(ctx) -> Router:
    db, rng = ctx.db, ctx.rng
    r = Router(name="kt")
    seen: dict[int, set] = {}

    def pick(uid: int) -> dict | None:
        return next_question(questions(), seen.setdefault(uid, set()), rng)

    def render(q: dict, lang: str) -> str:
        body = q["en"] if lang == "en" else q["ar"]
        return f"{t(lang, 'kt_title')}\n{esc(body)}"

    @r.message(F.text.regexp(TRIGGER))
    async def on_trigger(m: Message):
        uid = m.from_user.id
        lang = db.get_lang(uid)
        q = pick(uid)
        if q is None:
            await m.answer(t(lang, "kt_empty"))
            return
        await m.reply(render(q, lang), parse_mode="HTML")

    @r.message(CommandStart(deep_link=True, magic=F.args == "kt"))
    async def on_inline_kt(m: Message):
        """من نتيجة الوضع الداخلي: يرسل سؤالًا مباشرة."""
        uid = m.from_user.id
        lang = db.get_lang(uid)
        q = pick(uid)
        if q is None:
            await m.answer(t(lang, "kt_empty"))
            return
        await m.answer(render(q, lang), parse_mode="HTML")

    @r.callback_query(F.data == "kt:n")
    async def on_next(c: CallbackQuery):
        uid = c.from_user.id
        lang = db.get_lang(uid)
        q = pick(uid)
        await c.answer()
        if q is None:
            return
        try:
            await c.message.edit_text(render(q, lang), parse_mode="HTML")
        except Exception:  # noqa: BLE001 - الرسالة قديمة أو محذوفة: نرسل سؤالًا جديدًا
            await c.message.answer(render(q, lang), parse_mode="HTML")

    return r
