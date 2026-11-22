from __future__ import annotations

import asyncio
import logging
import secrets
import time
from pathlib import Path

from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramServerError
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.utils.backoff import BackoffConfig
from aiogram.types import BotCommand, CallbackQuery

from .admin import build_admin_router
from .backup import RESTORE_MESSAGES, backup_loop, db_user_count, restore_if_empty
from .daily import reminder_loop
from .growth import growth_loop
from .bot import build_router
from .config import Settings
from .ctx import Ctx
from .db import DB
from .texts import t
from .recommend import build_recommend_router
from .teams import build_teams_router
from .personality import build_persona_router
from .mafia_game import build_mafia_router
from .spy_game import build_spy_router
from .swap_game import build_swap_router
from .online import build_online_router
from .games import build_games_router
from .group import build_group_router

log = logging.getLogger(__name__)


class SubGate(BaseMiddleware):
    """الاشتراك الإجباري على كل زر: من غادر القناة في منتصف الاختبار لا يضغط أي زر حتى يعود مشتركًا.
    المستثنى: زر «تحققت» نفسه، والأدمن (يمرّون في subscribed)، ومن تعذّر التحقق منه (البوت ليس أدمن بالقناة)."""
    EXEMPT = ("chk", "noop")

    def __init__(self, ctx: Ctx):
        self.ctx = ctx

    async def __call__(self, handler, event, data):
        if isinstance(event, CallbackQuery) and event.message and event.message.chat.type == "channel":
            return await handler(event, data)             # مسابقات القنوات: لا فحص لكل ضغطة (آلاف)؛ يُتحقق من الفائزين فقط
        if (isinstance(event, CallbackQuery) and self.ctx.subscribed and self.ctx.channel()
                and (event.data or "") not in self.EXEMPT):
            try:
                ok = await self.ctx.subscribed(event.bot, event.from_user.id)
            except Exception:  # noqa: BLE001
                ok = None
            if ok is False:
                L = self.ctx.db.get_lang(event.from_user.id)
                try:
                    await event.answer(t(L, "sub_left"), show_alert=True)
                except Exception:  # noqa: BLE001
                    pass
                if event.message and event.message.chat.type == "private":     # في المجموعات: تنبيه فقط (بلا رسائل)
                    await self.ctx.gate(event.bot, event.message.chat.id, event.from_user.id)
                return None
        return await handler(event, data)


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


async def _tell_owners(bot: Bot, ctx: Ctx, text: str) -> None:
    for owner in ctx.owner_ids():
        try:
            await bot.send_message(owner, text)
        except Exception:  # noqa: BLE001
            pass


def build_dispatcher(ctx: Ctx) -> Dispatcher:
    dp = Dispatcher()
    dp.message.outer_middleware(Guard())
    dp.callback_query.outer_middleware(Guard())
    dp.callback_query.outer_middleware(SubGate(ctx))
    dp.include_router(build_admin_router(ctx))   # أولًا: محميّ بفلتر المشرفين
    dp.include_router(build_mafia_router(ctx))    # قبل المجموعات: أزرار المافيا
    dp.include_router(build_spy_router(ctx))      # برا السالفة
    dp.include_router(build_swap_router(ctx))     # تبادل الشخصيات (قبل start العادي)
    dp.include_router(build_online_router(ctx))   # لعب أونلاين
    dp.include_router(build_group_router(ctx))    # المجموعات: قبل الباقي، والباقي مقيّد بالخاص
    dp.include_router(build_games_router(ctx))
    dp.include_router(build_recommend_router(ctx))
    dp.include_router(build_teams_router(ctx))
    dp.include_router(build_persona_router(ctx))
    dp.include_router(build_router(ctx))
    return dp


async def run(settings: Settings) -> None:
    bot = Bot(settings.token)
    restore = await restore_if_empty(bot, settings)          # قبل فتح القاعدة: لو انمسح القرص نستعيد التقدم
    if restore != "kept":
        log.warning("database startup: %s", restore)
        print(f"\n[قاعدة البيانات] {RESTORE_MESSAGES.get(restore, restore)}\n", flush=True)
    db = DB(settings.db_path)
    n = db.load_questions(settings.questions_path)
    ctx = Ctx(settings, db)
    log.info("loaded %d questions", n)
    if not settings.admin_ids and db.admin_count() == 0:
        ctx.claim_code = secrets.token_hex(4)
        banner = f"\n{'=' * 50}\n  كود تفعيل المالك (مرة واحدة):  /claim {ctx.claim_code}\n  أرسله للبوت من حسابك لتصير المالك.\n{'=' * 50}"
        log.warning(banner)
        print(banner, flush=True)
    if restore in ("restored", "restored-local"):
        ctx.tasks.append(asyncio.create_task(_tell_owners(bot, ctx, RESTORE_MESSAGES[restore]
                                                              + f"\n👥 اللاعبون الآن: {db_user_count(Path(settings.db_path))}")))
    elif restore in ("chat-unreachable", "download-failed", "bad-zip", "bad-db"):
        ctx.tasks.append(asyncio.create_task(_tell_owners(bot, ctx, RESTORE_MESSAGES[restore])))
    # لا نفقد الرسائل المعلّقة أثناء إعادة التشغيل. إن تعذّر الوصول لتليجرام مؤقتًا لا ننهار: نعيد المحاولة.
    for attempt in range(1, 1000):
        try:
            await bot.delete_webhook(drop_pending_updates=False)
            break
        except (TelegramNetworkError, TelegramServerError, TelegramRetryAfter, asyncio.TimeoutError, OSError) as e:
            wait = min(60, 3 * attempt)
            log.warning("cannot reach Telegram yet (%s). retry #%d in %ds", e, attempt, wait)
            await asyncio.sleep(wait)
    try:   # اسم البوت لزر «بوت اللعبة» بجانب زر القناة
        from .bot import set_bot_username
        set_bot_username((await bot.get_me()).username)
    except (TelegramNetworkError, TelegramServerError, TelegramRetryAfter, asyncio.TimeoutError, OSError):
        log.warning("cannot read bot username yet; bot button will appear after restart")
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
    try:   # أوامر المجموعات تظهر في قائمة «/» داخل المجموعات فقط
        from aiogram.types import BotCommandScopeAllGroupChats
        await bot.set_my_commands([
            BotCommand(command="play", description="ابدأ لعبة جماعية 🎮"), BotCommand(command="quiz", description="أسئلة عامة 🎯"),
            BotCommand(command="sudden", description="الموت المفاجئ ☠️"), BotCommand(command="gtop", description="متصدرو المجموعة 🏆"),
            BotCommand(command="gstop", description="إيقاف اللعبة ⛔")], scope=BotCommandScopeAllGroupChats())
        await bot.set_my_commands([
            BotCommand(command="play", description="Start a group game 🎮"), BotCommand(command="quiz", description="General quiz 🎯"),
            BotCommand(command="sudden", description="Sudden death ☠️"), BotCommand(command="gtop", description="Group leaderboard 🏆"),
            BotCommand(command="gstop", description="Stop the game ⛔")], scope=BotCommandScopeAllGroupChats(), language_code="en")
    except Exception as e:  # noqa: BLE001
        log.warning("group commands failed: %s", e)
    ctx.tasks.append(asyncio.create_task(growth_loop(bot, ctx)))   # لقطة يومية لعدد مشتركي القناة
    ctx.tasks.append(asyncio.create_task(reminder_loop(bot, ctx)))   # تذكير يومي اختياري
    ctx.tasks.append(asyncio.create_task(backup_loop(bot, ctx)))   # نسخة احتياطية أسبوعية تلقائية
    dp = build_dispatcher(ctx)
    await dp.start_polling(
        bot, allowed_updates=dp.resolve_used_update_types(),
        backoff_config=BackoffConfig(min_delay=0.2, max_delay=1.5, factor=1.3, jitter=0.1))   # إعادة اتصال أسرع (الافتراضي حتى 5ث)
