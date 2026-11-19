"""التحدي اليومي (نفس الأسئلة للجميع)، سؤال اليوم، سلسلة الأيام، وتذكير اختياري (مرة يوميًا كحد أقصى)."""
from __future__ import annotations

import asyncio
import logging
import random
import time

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from .bot import btn, kb
from .ctx import Ctx
from .quiz import pick_questions
from .texts import t

log = logging.getLogger(__name__)
REMIND_HOUR = 18            # توقيت مكة: تذكير واحد في اليوم لمن فعّله
STREAK_MILESTONES = (3, 7, 14, 30, 100)


def daily_questions(pool, day: int, mode: str):
    """أسئلة اليوم: ثابتة لليوم نفسه عند كل اللاعبين (بذرة = رقم اليوم)."""
    pool = sorted(pool, key=lambda q: q.id)
    rng = random.Random(day * 7 + (1 if mode == "dq" else 2))
    qs = pick_questions(pool, {}, rng, per_level=1)
    if len(qs) < 10:
        return []
    return [qs[4]] if mode == "dq" else [qs[i] for i in (1, 3, 5, 7, 9)]


def duel_questions(pool, seen, rng):
    qs = pick_questions(pool, seen, rng, per_level=1)
    return qs[1:8] if len(qs) >= 8 else []


def remind_text(L: str, streak: int, streak_day: int, day: int) -> str:
    if streak > 0 and streak_day == day - 1:
        return t(L, "dy_remind_streak", n=streak)
    return t(L, "dy_remind_new")


async def reminder_loop(bot: Bot, ctx: Ctx) -> None:
    """مرة في اليوم بعد الساعة 18:00، فقط لمن فعّل التذكير ولم يلعب اليوم. من حظر البوت يُوقَف تذكيره."""
    while True:
        try:
            hour = int(((time.time() + 3 * 3600) % 86400) // 3600)
            if hour >= REMIND_HOUR:
                day = ctx.db.today()
                for u in ctx.db.remind_targets(day):
                    ctx.db.mark_reminded(u["tg_id"], day)           # أولًا: حتى لا يتكرر لو تعثّر الإرسال
                    L = u["lang"]
                    try:
                        await bot.send_message(u["tg_id"], remind_text(L, u["streak"], u["streak_day"], day),
                                               reply_markup=kb([btn(t(L, "dy_open"), "dy:m")],
                                                               [btn(t(L, "dy_remind_off"), "dy:off")]))
                    except TelegramForbiddenError:
                        ctx.db.set_remind(u["tg_id"], False)
                    except TelegramAPIError:
                        pass
                    await asyncio.sleep(0.07)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("reminder loop failed")
        try:                                                     # تحدّيات التعادل التي انتهت مهلتها
            from .ties import sweep
            await sweep(bot, ctx.db)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("tie sweep failed")
        await asyncio.sleep(600)
