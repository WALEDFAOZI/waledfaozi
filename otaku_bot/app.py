from __future__ import annotations

import asyncio
import logging
import secrets
import time

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.utils.backoff import BackoffConfig
from aiogram.types import BotCommand, CallbackQuery

from .admin import build_admin_router
from .backup import backup_loop
from .bot import build_router
from .config import Settings
from .ctx import Ctx
from .db import DB
from .games import build_games_router

log = logging.getLogger(__name__)


class Guard(BaseMiddleware):
    """يسجّل أي تحديث أبطأ من ثانية، وإن فشل المعالج يردّ على الزر حتى لا يبقى «يحمّل» بلا نهاية."""

    async def __call__(self, handler, event, data):
        t0 = time.monotonic()
        sent_at = getattr(event, "date", None)          # وقت إرسال المستخدم للرسالة (للرسائل فقط)
        if sent_at is not None:
            age = time.time() - sent_at.timestamp()
            if age > 4:
                log.warning("late update: delivered %.1fs after it was sent (polling/network/Conflict delay, not handler speed): %s",
                            age, getattr(event, "text", None))
        try:
            return await handler(event, data)
        except Exception:  # noqa: BLE001
            log.exception("handler failed")
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer("⚠️ حدث خطأ مؤقت، جرّب مرة ثانية")
                except Exception:  # noqa: BLE001
                    pass
        finally:
            dt = time.monotonic() - t0
            if dt > 1.0:
                log.warning("slow update %.2fs: %s", dt, getattr(event, "data", None) or getattr(event, "text", None))


def build_dispatcher(ctx: Ctx) -> Dispatcher:
    dp = Dispatcher()
    dp.message.outer_middleware(Guard())
    dp.callback_query.outer_middleware(Guard())
    dp.include_router(build_admin_router(ctx))   # أولًا: محميّ بفلتر المشرفين
    dp.include_router(build_games_router(ctx))
    dp.include_router(build_router(ctx))
    return dp


async def run(settings: Settings) -> None:
    db = DB(settings.db_path)
    n = db.load_questions(settings.questions_path)
    ctx = Ctx(settings, db)
    log.info("loaded %d questions", n)
    if not settings.admin_ids and db.admin_count() == 0:
        ctx.claim_code = secrets.token_hex(4)
        banner = f"\n{'=' * 50}\n  كود تفعيل المالك (مرة واحدة):  /claim {ctx.claim_code}\n  أرسله للبوت من حسابك لتصير المالك.\n{'=' * 50}"
        log.warning(banner)
        print(banner, flush=True)
    bot = Bot(settings.token)
    await bot.delete_webhook(drop_pending_updates=False)   # لا نفقد الرسائل المعلّقة أثناء إعادة التشغيل
    try:   # زر «القائمة» الدائم بجانب خانة الكتابة
        await bot.set_my_commands([
            BotCommand(command="start", description="القائمة الرئيسية 🎌"),
            BotCommand(command="games", description="الألعاب 🎮"),
            BotCommand(command="weekly", description="متصدرو الأسبوع 📅"),
            BotCommand(command="top", description="المتصدرون 🏆"),
            BotCommand(command="stats", description="إحصائياتي 📈"),
            BotCommand(command="lang", description="اللغة 🌐")])
        await bot.set_my_commands([
            BotCommand(command="start", description="Main menu 🎌"),
            BotCommand(command="games", description="Games 🎮"),
            BotCommand(command="weekly", description="Weekly board 📅"),
            BotCommand(command="top", description="Leaderboard 🏆"),
            BotCommand(command="stats", description="My stats 📈"),
            BotCommand(command="lang", description="Language 🌐")], language_code="en")
    except Exception as e:  # noqa: BLE001
        log.warning("set_my_commands failed: %s", e)
    ctx.tasks.append(asyncio.create_task(backup_loop(bot, ctx)))   # نسخة احتياطية أسبوعية تلقائية
    dp = build_dispatcher(ctx)
    await dp.start_polling(
        bot, allowed_updates=dp.resolve_used_update_types(),
        backoff_config=BackoffConfig(min_delay=0.2, max_delay=1.5, factor=1.3, jitter=0.1))   # إعادة اتصال أسرع (الافتراضي حتى 5ث)
