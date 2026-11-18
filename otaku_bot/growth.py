"""قياس نمو القناة ومسار اللاعبين.

ما الذي نقيسه فعلًا؟
  • عدد مشتركي القناة يوميًا (لقطة واحدة في اليوم) ← نعرف النمو خلال 7 و30 يومًا.
  • «اشتركوا عبر البوت»: لاعبون عرض لهم البوت طلب الاشتراك ثم صاروا مشتركين بعدها.
  • مسار اللاعب: بدأ البوت ← أكمل اختبارًا كاملًا ← عاد لاختبارين فأكثر.
تنبيه: لا يمكن معرفة مصدر كل مشترك في القناة؛ الرقم «اشتركوا عبر البوت» هو من طُلب منهم الاشتراك فاشتركوا.
"""
import asyncio
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from .ctx import Ctx

log = logging.getLogger(__name__)


async def refresh_count(bot: Bot, ctx: Ctx, max_age: float = 3600) -> int | None:
    """يقيس عدد مشتركي القناة ويحفظه (بحد أقصى مرة كل max_age ثانية). يرجع العدد أو None."""
    ch = ctx.channel()
    if not ch:
        return None
    last = float(ctx.db.get_setting("chan_snap_at", "0") or 0)
    if time.time() - last < max_age:
        g = ctx.db.channel_growth()
        return g["count"] if g else None
    try:
        n = await bot.get_chat_member_count(ch)
    except TelegramAPIError as e:
        log.warning("cannot read channel member count (%s): %s", ch, e)
        return None
    ctx.db.save_channel_count(int(n))
    ctx.db.set_setting("chan_snap_at", str(time.time()))
    return int(n)


def _pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f}%" if b else "—"


def growth_text(ctx: Ctx) -> str:
    """سطور الإحصائيات الخاصة بنمو القناة والمسار (للوحة الأدمن)."""
    f = ctx.db.funnel_stats()
    lines = [
        "🧭 <b>مسار اللاعبين</b>",
        f"  بدأوا البوت: {f['started']} ← أكملوا اختبارًا كاملًا: {f['with_test']} ({_pct(f['with_test'], f['started'])})"
        f" ← عادوا لاختبارين+: {f['returning']} ({_pct(f['returning'], f['with_test'])})",
    ]
    if not ctx.channel():
        return "\n".join(lines)
    g = ctx.db.channel_growth()
    lines.append("📢 <b>نمو القناة</b> " + ctx.channel())
    if g:
        def fmt(v):
            d, span = v
            sign = "+" if d >= 0 else ""
            return f"{sign}{d} خلال {span} يوم" if span else "لا قياس سابق للمقارنة بعد"
        lines.append(f"  المشتركون الآن: <b>{g['count']:,}</b> · 7 أيام: {fmt(g['d7'])} · 30 يومًا: {fmt(g['d30'])}")
    else:
        lines.append("  لا يوجد قياس بعد (البوت لازم يكون أدمن في القناة ليقرأ عدد المشتركين).")
    lines.append(f"  طُلب منهم الاشتراك عبر البوت: {f['prompted']} ← اشتركوا بعدها: <b>{f['joined']}</b> ({_pct(f['joined'], f['prompted'])})"
                 f" · آخر 7 أيام: {f['joined_7d']} من {f['prompted_7d']}")
    return "\n".join(lines)


async def growth_loop(bot: Bot, ctx: Ctx) -> None:
    """لقطة يومية لعدد المشتركين (حتى لو لم تفتح اللوحة)."""
    while True:
        try:
            await refresh_count(bot, ctx, max_age=20 * 3600)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("growth snapshot failed")
        await asyncio.sleep(3600)
