from __future__ import annotations

import logging
import secrets

from aiogram import Bot, Dispatcher

from .admin import build_admin_router
from .bot import build_router
from .config import Settings
from .ctx import Ctx
from .db import DB
from .games import build_games_router

log = logging.getLogger(__name__)


def build_dispatcher(ctx: Ctx) -> Dispatcher:
    dp = Dispatcher()
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
    await build_dispatcher(ctx).start_polling(bot)
