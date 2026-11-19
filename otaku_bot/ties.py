"""تحدّي التعادل: لاعبان بنفس أفضل تقييم يتحدّى أحدهما الآخر لتحديد الأفضل.

القواعد:
• المدة: 5 ساعات. إن لم يلعب المدعو خلالها يُحسب الفوز لمن وصل لهذا التقييم أولًا، ويصير ترتيبه أعلى من صاحب نفس التقييم.
• لا يُتحدّى نفس الشخص أكثر من مرة كل 24 ساعة.
• التحدي نفسه مواجهة (7 أسئلة) تُحسب بالطريقة العادية إن لعب الطرفان.
"""
from __future__ import annotations

import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from . import progress
from .texts import t

log = logging.getLogger(__name__)
TIE_HOURS = 5
COOLDOWN_HOURS = 24


def can_challenge(db, me: int, other: int) -> str | None:
    """None إن كان التحدي ممكنًا، وإلا مفتاح نص الرفض."""
    if me == other:
        return "tie_no"
    a, b = db.get_user(me), db.get_user(other)
    if not a or not b or db.is_admin(me) or db.is_admin(other):
        return "tie_no"
    if not a["best_score"] or abs(a["best_score"] - b["best_score"]) > 0.001:
        return "tie_not"
    if a["lb_hidden"] or b["lb_hidden"]:
        return "tie_hidden"
    if db.recent_tie(me, other, time.time() - COOLDOWN_HOURS * 3600):
        return "tie_cooldown"
    return None


async def sweep(bot: Bot, db, now: float | None = None) -> None:
    """يُغلق تحدّيات التعادل التي انتهت مهلتها دون أن يلعب المدعو."""
    now = now or time.time()
    for d in db.open_tie_duels(now - TIE_HOURS * 3600):
        creator, target = d["creator"], d["target"]
        if not target:
            continue
        score = db.get_user(creator)["best_score"]
        fc = db.first_reached(creator, score)
        ft = db.first_reached(target, score)
        winner, loser = (creator, target) if (fc or float("inf")) <= (ft or float("inf")) else (target, creator)
        db.duel_done(d["id"])
        db.apply_tie_result(winner, loser, score)                     # الترتيب: الفائز يصير أعلى من صاحب نفس التقييم
        wps = progress.bonus(db, winner, "duel_win", 25, "duel_wins")
        no_show = target                                              # المدعو هو من لم يلعب (المضيف لعب قبل ذلك)
        msgs = {winner: ("tie_timeout_win", loser), loser: ("tie_timeout_lose" if loser == no_show else "tie_timeout_lose_played", winner)}
        for uid, (key, other) in msgs.items():
            Lx = db.get_lang(uid)
            try:
                await bot.send_message(uid, t(Lx, key, name=_name(db, other)), parse_mode="HTML")
            except TelegramAPIError:
                pass
        await progress.send_notice(bot, winner, db.get_lang(winner), wps)


def _name(db, uid: int) -> str:
    from .html_util import esc
    u = db.get_user(uid)
    return esc((u["name"] if u else "") or "?")
