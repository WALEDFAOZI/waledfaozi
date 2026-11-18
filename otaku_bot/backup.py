"""نسخة احتياطية أسبوعية تلقائية من قاعدة البيانات تُرسل لمالك البوت في تليجرام.

لماذا؟ الاستضافات المجانية قد تحذف الملفات أو تتوقف فجأة؛ بهذه النسخة تحتفظ بكل شيء عندك (الأسئلة، اللاعبون، النتائج).
للاستعادة: فك ضغط الملف وضع otaku.db مكان القاعدة الحالية ثم أعد تشغيل البوت.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile

from .ctx import Ctx
from .timeutil import TZ_HOURS

log = logging.getLogger(__name__)
INTERVAL = 7 * 86400          # أسبوع
CHECK_EVERY = 3600            # نتحقق كل ساعة هل حان الموعد


def enabled(ctx: Ctx) -> bool:
    return ctx.db.get_setting("auto_backup", "1") == "1"


def due(ctx: Ctx, now: float | None = None) -> bool:
    now = now if now is not None else time.time()
    last = float(ctx.db.get_setting("last_backup", "0") or 0)
    return enabled(ctx) and now - last >= INTERVAL


def last_backup_text(ctx: Ctx) -> str:
    last = float(ctx.db.get_setting("last_backup", "0") or 0)
    if not last:
        return "لم تُرسل بعد"
    return (datetime.fromtimestamp(last, timezone.utc) + timedelta(hours=TZ_HOURS)).strftime("%Y-%m-%d %H:%M")


def make_zip(ctx: Ctx, dest_dir: Path) -> Path:
    raw = dest_dir / "otaku.db"
    ctx.db.backup_to(str(raw))
    stamp = (datetime.now(timezone.utc) + timedelta(hours=TZ_HOURS)).strftime("%Y-%m-%d")
    out = dest_dir / f"otaku-backup-{stamp}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(raw, "otaku.db")
    raw.unlink()
    return out


def summary(ctx: Ctx) -> str:
    s = ctx.db.admin_stats(max_age=0)
    return (f"💾 نسخة احتياطية أسبوعية\n👥 {s['users']} مستخدم · 🔥 نشطون (7 أيام): {s['active_7d']}\n"
            f"✅ اختبارات (7 أيام): {s['finished_7d']} · 📚 أسئلة: {s['bank_active']}\n"
            "للاستعادة: فك الضغط وضع otaku.db مكان القاعدة ثم أعد التشغيل.")


async def send_backup(bot: Bot, ctx: Ctx) -> int:
    """يرسل النسخة لكل المالكين. يرجع عدد من وصلتهم. لا يسجّل «تمّت» إذا لم يصل لأحد (فيعيد المحاولة)."""
    owners = ctx.owner_ids()
    if not owners:
        return 0
    sent = 0
    with tempfile.TemporaryDirectory() as d:
        path = make_zip(ctx, Path(d))
        caption = summary(ctx)
        if path.stat().st_size > 49 * 1024 * 1024:
            caption += "\n⚠️ الملف كبير؛ قد يرفضه تليجرام."
        for owner in owners:
            try:
                await bot.send_document(owner, FSInputFile(path), caption=caption)
                sent += 1
            except TelegramAPIError as e:
                log.warning("backup to %s failed: %s", owner, e)
    if sent:
        ctx.db.set_setting("last_backup", str(time.time()))
    return sent


async def backup_loop(bot: Bot, ctx: Ctx) -> None:
    while True:
        try:
            if due(ctx):
                await send_backup(bot, ctx)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("auto backup failed")
        await asyncio.sleep(CHECK_EVERY)
