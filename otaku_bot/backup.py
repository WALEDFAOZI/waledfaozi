"""نسخة احتياطية أسبوعية تلقائية من قاعدة البيانات تُرسل لمالك البوت في تليجرام.

لماذا؟ الاستضافات المجانية قد تحذف الملفات أو تتوقف فجأة؛ بهذه النسخة تحتفظ بكل شيء عندك (الأسئلة، اللاعبون، النتائج).
للاستعادة: فك ضغط الملف وضع otaku.db مكان القاعدة الحالية ثم أعد تشغيل البوت.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import sqlite3
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


# ═════════ حماية التقدم: نسخ متكررة إلى قناة خاصة + استعادة تلقائية ═════════
# الفكرة: كل N ساعات يرسل البوت نسخة إلى قناة/مجموعة خاصة ويثبّتها (pin). وعند أي تشغيل على قاعدة فارغة
# (قرص انمسح/سيرفر جديد) يقرأ البوت الرسالة المثبتة وينزّل آخر نسخة ويستعيد منها كل شيء قبل أن يبدأ.
# لا نحتاج أي خدمة خارجية: تليجرام نفسه هو المخزن.

def parse_chat(value: str):
    v = (value or "").strip()
    if not v:
        return None
    return int(v) if v.lstrip("-").isdigit() else v


def chat_due(ctx: Ctx, now: float | None = None) -> bool:
    if not parse_chat(ctx.settings.backup_chat):
        return False
    now = now if now is not None else time.time()
    last = float(ctx.db.get_setting("last_chat_backup", "0") or 0)
    return now - last >= ctx.settings.backup_hours * 3600


def chat_status_text(ctx: Ctx) -> str:
    if not parse_chat(ctx.settings.backup_chat):
        return "🛟 قناة النسخ الاحتياطي: ❌ غير مضبوطة (BACKUP_CHAT_ID) — لن يُستعاد التقدم تلقائيًا لو انمسح القرص"
    last = float(ctx.db.get_setting("last_chat_backup", "0") or 0)
    when = (datetime.fromtimestamp(last, timezone.utc) + timedelta(hours=TZ_HOURS)).strftime("%Y-%m-%d %H:%M") if last else "لم تُرسل بعد"
    err = ctx.db.get_setting("chat_backup_error", "")
    return (f"🛟 قناة النسخ الاحتياطي: ✅ مضبوطة · كل {ctx.settings.backup_hours} ساعات · آخر نسخة: {when}"
            + (f"\n⚠️ آخر خطأ: {err}" if err else ""))


async def send_chat_backup(bot: Bot, ctx: Ctx) -> tuple[bool, str]:
    """يرسل نسخة إلى قناة النسخ ويثبّتها. يرجع (نجح, رسالة)."""
    chat = parse_chat(ctx.settings.backup_chat)
    if not chat:
        return False, "BACKUP_CHAT_ID غير مضبوط"
    with tempfile.TemporaryDirectory() as d:
        path = make_zip(ctx, Path(d))
        try:
            msg = await bot.send_document(chat, FSInputFile(path), caption=summary(ctx), disable_notification=True)
        except TelegramAPIError as e:
            ctx.db.set_setting("chat_backup_error", f"الإرسال: {e}"[:200])
            log.warning("chat backup send failed: %s", e)
            return False, f"تعذّر الإرسال: {e}"
    try:
        await bot.pin_chat_message(chat, msg.message_id, disable_notification=True)   # الرسالة المثبتة = آخر نسخة
    except TelegramAPIError as e:
        ctx.db.set_setting("chat_backup_error", "الإرسال نجح لكن التثبيت فشل: اجعل البوت أدمن بصلاحية «تثبيت الرسائل»")
        ctx.db.set_setting("last_chat_backup", str(time.time()))
        log.warning("chat backup pin failed: %s", e)
        return True, "أُرسلت النسخة لكن التثبيت فشل (أعطِ البوت صلاحية تثبيت الرسائل، وإلا لن تعمل الاستعادة التلقائية)"
    ctx.db.set_setting("chat_backup_error", "")
    ctx.db.set_setting("last_chat_backup", str(time.time()))
    return True, "تم الإرسال والتثبيت"


def _valid_db(path: Path) -> bool:
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return False
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            return {"users", "questions", "sessions"} <= tables
        finally:
            con.close()
    except sqlite3.Error:
        return False


def db_user_count(path: Path) -> int:
    """عدد اللاعبين في ملف قاعدة؛ -1 إن كان الملف غير صالح، 0 إن لم يوجد."""
    if not path.exists() or path.stat().st_size == 0:
        return 0
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            return con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        finally:
            con.close()
    except sqlite3.Error:
        return -1


# ── نسخ محلية دورية على نفس الجهاز (خارج تليجرام): تحمي من تلف القاعدة أو حذفها بالخطأ ──
LOCAL_KEEP = 30


def local_dir(db_path: str | Path) -> Path:
    return Path(db_path).resolve().parent / "backups"


def local_backup(ctx: Ctx, keep: int = LOCAL_KEEP) -> Path | None:
    """نسخة otaku-YYYYmmdd-HHMM.db، وتبقى آخر `keep` نسخة. لا نكتب نسخة لقاعدة فارغة حتى لا نطرد نسخًا جيدة."""
    if db_user_count_live(ctx) == 0:
        return None
    d = local_dir(ctx.settings.db_path)
    d.mkdir(parents=True, exist_ok=True)
    stamp = (datetime.now(timezone.utc) + timedelta(hours=TZ_HOURS)).strftime("%Y%m%d-%H%M")
    out = d / f"otaku-{stamp}.db"
    ctx.db.backup_to(str(out))
    for old in sorted(d.glob("otaku-*.db"))[:-keep]:
        old.unlink(missing_ok=True)
    ctx.db.set_setting("last_local_backup", str(time.time()))
    return out


def db_user_count_live(ctx: Ctx) -> int:
    return ctx.db.conn.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]


def local_due(ctx: Ctx, now: float | None = None) -> bool:
    now = now if now is not None else time.time()
    last = float(ctx.db.get_setting("last_local_backup", "0") or 0)
    return now - last >= max(1, ctx.settings.backup_hours) * 3600


def _restore_local(path: Path) -> bool:
    for f in sorted(local_dir(path).glob("otaku-*.db"), reverse=True):
        if _valid_db(f) and db_user_count(f) > 0:
            for ext in ("", "-wal", "-shm"):
                old = Path(str(path) + ext)
                if old.exists():
                    old.unlink()
            shutil.copy2(f, path)
            return True
    return False


async def restore_if_empty(bot: Bot, settings) -> str:
    """يُستدعى قبل فتح القاعدة. لا يلمس أي قاعدة فيها لاعبون أبدًا.
    الحالات: kept | restored | no-backup-chat | chat-unreachable | no-pinned-backup | download-failed | bad-zip | bad-db"""
    path = Path(settings.db_path)
    n = db_user_count(path)
    if n > 0:
        return "kept"
    if n == -1:                                   # ملف تالف: نحفظه جانبًا ونحاول الاستعادة
        shutil.move(str(path), f"{path}.corrupt-{int(time.time())}")
    if _restore_local(path):                      # أسرع وأبسط: آخر نسخة محلية سليمة
        return "restored-local"
    chat = parse_chat(getattr(settings, "backup_chat", ""))
    if not chat:
        return "no-backup-chat"
    try:
        info = await bot.get_chat(chat)
    except TelegramAPIError as e:
        log.warning("backup chat unreachable: %s", e)
        return "chat-unreachable"
    pinned = getattr(info, "pinned_message", None)
    doc = getattr(pinned, "document", None)
    if not doc:
        return "no-pinned-backup"
    with tempfile.TemporaryDirectory() as d:
        zp = Path(d) / "backup.zip"
        try:
            await bot.download(doc.file_id, destination=zp)
        except Exception as e:  # noqa: BLE001
            log.warning("backup download failed: %s", e)
            return "download-failed"
        try:
            with zipfile.ZipFile(zp) as z:
                if "otaku.db" not in z.namelist():
                    return "bad-zip"
                z.extract("otaku.db", d)
        except (zipfile.BadZipFile, OSError):
            return "bad-zip"
        restored = Path(d) / "otaku.db"
        if not _valid_db(restored):
            return "bad-db"
        path.parent.mkdir(parents=True, exist_ok=True)
        for ext in ("", "-wal", "-shm"):               # نظّف بقايا القاعدة الفارغة القديمة
            old = Path(str(path) + ext)
            if old.exists():
                old.unlink()
        shutil.copy2(restored, path)
    return "restored"


RESTORE_MESSAGES = {
    "restored-local": "✅ تمت استعادة التقدم من آخر نسخة محلية (مجلد backups).",
    "restored": "✅ تمت استعادة كل التقدم (اللاعبون والتقييمات والأسئلة المضافة) من آخر نسخة احتياطية.",
    "no-backup-chat": "ℹ️ بدأت بقاعدة جديدة. لحماية التقدم ضع BACKUP_CHAT_ID (قناة خاصة أضفتها للبوت أدمن) في .env.",
    "chat-unreachable": "⚠️ بدأت بقاعدة جديدة: لم أستطع الوصول إلى قناة النسخ (BACKUP_CHAT_ID). تأكد أن البوت أدمن فيها.",
    "no-pinned-backup": "ℹ️ بدأت بقاعدة جديدة: لا توجد نسخة مثبتة في قناة النسخ بعد.",
    "download-failed": "⚠️ بدأت بقاعدة جديدة: فشل تنزيل النسخة المثبتة. أعد التشغيل للمحاولة ثانية.",
    "bad-zip": "⚠️ بدأت بقاعدة جديدة: النسخة المثبتة ليست ملف نسخة صالحًا.",
    "bad-db": "⚠️ بدأت بقاعدة جديدة: النسخة المثبتة تالفة.",
}


async def backup_loop(bot: Bot, ctx: Ctx) -> None:
    while True:
        try:
            if local_due(ctx):
                local_backup(ctx)          # في خيط البوت نفسه (اتصال SQLite لا يعمل من خيط آخر)؛ النسخ سريع
            if chat_due(ctx):
                await send_chat_backup(bot, ctx)
            if due(ctx):
                await send_backup(bot, ctx)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("auto backup failed")
        await asyncio.sleep(CHECK_EVERY)
