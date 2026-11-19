"""الخبرة (XP) والمستويات والإنجازات. منطق نقي فوق DB، وأي حدث يمرّ عبر record() فيرجع ملخصًا للعرض."""
from __future__ import annotations

from dataclasses import dataclass, field

from .texts import t

PRACTICE_DAILY_CAP = 150          # سقف خبرة التدريب اليومي (سريع/تصنيف/موت مفاجئ/ألعاب) حتى لا تُستغل بالتكرار
ACH_BONUS = 25
INVITE_XP = 100

# (أول مستوى, لقب عربي, لقب إنجليزي)
RANKS = [(1, "مبتدئ 🍼", "Rookie 🍼"), (3, "مشاهد 📺", "Viewer 📺"), (5, "متابع 🎌", "Fan 🎌"), (8, "أوتاكو ⚔️", "Otaku ⚔️"),
         (12, "أوتاكو متمرس 🔥", "Seasoned Otaku 🔥"), (17, "سينسي 🥋", "Sensei 🥋"), (23, "أسطورة 🌟", "Legend 🌟"),
         (30, "ملك الأوتاكو 👑", "King of Otaku 👑")]

# (المفتاح, أيقونة, الاسم عربي, الاسم إنجليزي, الإحصاء, المطلوب)
ACH = [
    ("t1", "🎯", "أول اختبار كامل", "First full test", "tests", 1),
    ("t10", "📚", "10 اختبارات كاملة", "10 full tests", "tests", 10),
    ("t50", "🏛", "50 اختبارًا كاملًا", "50 full tests", "tests", 50),
    ("s5", "⭐", "تقييم 5 من 10", "Score 5/10", "best10", 50),
    ("s7", "🌟", "تقييم 7 من 10", "Score 7/10", "best10", 70),
    ("s9", "💎", "تقييم 9 من 10", "Score 9/10", "best10", 90),
    ("sd10", "☠️", "10 متتالية في الموت المفاجئ", "10 in sudden death", "best_sudden", 10),
    ("sd25", "💀", "25 متتالية في الموت المفاجئ", "25 in sudden death", "best_sudden", 25),
    ("c100", "✅", "100 إجابة صحيحة", "100 correct answers", "correct", 100),
    ("c500", "🧠", "500 إجابة صحيحة", "500 correct answers", "correct", 500),
    ("c2000", "🏆", "2000 إجابة صحيحة", "2000 correct answers", "correct", 2000),
    ("st3", "🔥", "سلسلة 3 أيام", "3-day streak", "best_streak", 3),
    ("st7", "🔥", "سلسلة أسبوع", "7-day streak", "best_streak", 7),
    ("st30", "🌋", "سلسلة 30 يومًا", "30-day streak", "best_streak", 30),
    ("dy7", "📅", "7 تحديات يومية", "7 daily challenges", "daily_played", 7),
    ("dyp", "💯", "تحدي يومي كامل 5/5", "Perfect daily 5/5", "perfect_daily", 1),
    ("g25", "🎮", "25 لعبة", "25 games", "games", 25),
    ("g100", "🕹", "100 لعبة", "100 games", "games", 100),
    ("du1", "⚔️", "أول فوز في مواجهة", "First duel win", "duel_wins", 1),
    ("du10", "🗡", "10 انتصارات في المواجهات", "10 duel wins", "duel_wins", 10),
    ("gw1", "👥", "أول فوز في مجموعة", "First group win", "group_wins", 1),
    ("gw10", "🛡", "10 انتصارات جماعية", "10 group wins", "group_wins", 10),
    ("iv1", "🌱", "أول دعوة مكتملة", "First invite", "invites", 1),
    ("iv5", "🤝", "5 دعوات مكتملة", "5 invites", "invites", 5),
]


def level_of(xp: int) -> int:
    return int((max(xp, 0) / 50) ** 0.5) + 1


def xp_for(level: int) -> int:
    return 50 * (level - 1) ** 2


def rank_of(level: int, L: str) -> str:
    cur = RANKS[0]
    for r in RANKS:
        if level >= r[0]:
            cur = r
    return cur[1] if L == "ar" else cur[2]


def bar(frac: float, n: int = 10) -> str:
    k = max(0, min(n, round(frac * n)))
    return "▰" * k + "▱" * (n - k)


def level_line(xp: int, L: str) -> str:
    lv = level_of(xp)
    lo, hi = xp_for(lv), xp_for(lv + 1)
    return t(L, "pg_level", lv=lv, rank=rank_of(lv, L), bar=bar((xp - lo) / (hi - lo)), xp=xp, nxt=hi)


@dataclass
class Summary:
    xp: int = 0
    level_up: int | None = None             # المستوى الجديد إن ارتقى
    achs: list = field(default_factory=list)  # إنجازات جديدة: (icon, اسم عربي, اسم إنجليزي)

    @property
    def notable(self) -> bool:
        return bool(self.level_up or self.achs)


def _award(db, uid: int, amount: int, kind: str, s: Summary) -> None:
    if amount <= 0:
        return
    before = level_of(db.get_user(uid)["xp"])
    new = db.add_xp(uid, amount, kind)
    s.xp += amount
    after = level_of(new)
    if after > before:
        s.level_up = after


def record(db, uid: int, event: str, **kw) -> Summary:
    """يسجّل حدثًا: إحصاءات + خبرة + فحص إنجازات. event: full|quick|sudden|dq|daily|game|duel|group|invite"""
    s = Summary()
    u = db.get_user(uid)
    if not u:
        return s
    practice = event in ("quick", "sudden", "game")
    amount = 0
    if event == "full":
        db.bump_stat(uid, "tests")
        db.max_stat(uid, "best10", int(round(kw.get("score", 0) * 10)))
        db.bump_stat(uid, "correct", kw.get("correct", 0))
        amount = 40 + int(round(kw.get("score", 0) * 10))
    elif event == "quick":
        db.bump_stat(uid, "correct", kw.get("correct", 0))
        amount = 10 + kw.get("correct", 0)
    elif event == "sudden":
        db.max_stat(uid, "best_sudden", kw.get("streak", 0))
        db.bump_stat(uid, "correct", kw.get("streak", 0))
        amount = 5 + 2 * kw.get("streak", 0)
    elif event == "dq":
        db.bump_stat(uid, "correct", kw.get("correct", 0))
        amount = 10
    elif event == "daily":
        db.bump_stat(uid, "daily_played")
        db.bump_stat(uid, "correct", kw.get("correct", 0))
        if kw.get("correct", 0) == kw.get("total", 5):
            db.bump_stat(uid, "perfect_daily")
        amount = 20 + 5 * kw.get("correct", 0)
    elif event == "game":
        db.bump_stat(uid, "games")
        amount = 5 + 2 * kw.get("score", 0)
    elif event == "duel":
        db.bump_stat(uid, "duels")
        db.bump_stat(uid, "correct", kw.get("correct", 0))
        amount = 15 + (25 if kw.get("won") else 0)
        if kw.get("won"):
            db.bump_stat(uid, "duel_wins")
    elif event == "group":
        db.bump_stat(uid, "group_games")
        db.bump_stat(uid, "correct", kw.get("correct", 0))
        amount = 10 + 3 * kw.get("correct", 0) + (30 if kw.get("won") else 0)
        if kw.get("won"):
            db.bump_stat(uid, "group_wins")
    elif event == "invite":
        db.bump_stat(uid, "invites")
        amount = INVITE_XP
    if practice:                                           # سقف يومي للتدريب
        room = PRACTICE_DAILY_CAP - db.xp_today(uid, "practice")
        amount = max(0, min(amount, room))
    _award(db, uid, amount, ("practice:" if practice else "") + event, s)
    db.max_stat(uid, "best_streak", db.get_user(uid)["best_streak"])
    for key, icon, ar, en, stat, need in ACH:
        if db.stat(uid, stat) >= need and db.unlock(uid, key):
            s.achs.append((icon, ar, en))
            _award(db, uid, ACH_BONUS, "achievement", s)
    return s


def notice(s: Summary, L: str) -> str:
    """نص إشعار قصير: ارتقاء مستوى و/أو إنجازات جديدة (فارغ إن لا شيء)."""
    lines = []
    if s.level_up:
        lines.append(t(L, "pg_levelup", lv=s.level_up, rank=rank_of(s.level_up, L)))
    for icon, ar, en in s.achs:
        lines.append(t(L, "pg_ach_new", icon=icon, name=ar if L == "ar" else en))
    return "\n".join(lines)


def ach_list(db, uid: int, L: str) -> str:
    got = db.achievements_of(uid)
    rows = [f"{'✅' if k in got else '🔒'} {icon} {ar if L == 'ar' else en}" for k, icon, ar, en, _, _ in ACH]
    return t(L, "pg_ach_head", n=len(got), total=len(ACH)) + "\n\n" + "\n".join(rows)


def bonus(db, uid: int, kind: str, xp: int, stat: str | None = None) -> Summary:
    """خبرة إضافية بلا حدث جديد (مثل مكافأة فوز مواجهة)، مع إحصاء اختياري وفحص الإنجازات."""
    s = Summary()
    if not db.get_user(uid):
        return s
    if stat:
        db.bump_stat(uid, stat)
    _award(db, uid, xp, kind, s)
    for key, icon, ar, en, st, need in ACH:
        if db.stat(uid, st) >= need and db.unlock(uid, key):
            s.achs.append((icon, ar, en))
            _award(db, uid, ACH_BONUS, "achievement", s)
    return s


def merge(a: Summary, b: Summary) -> Summary:
    return Summary(a.xp + b.xp, b.level_up or a.level_up, a.achs + b.achs)


async def send_notice(bot, uid: int, L: str, s: Summary) -> None:
    """رسالة قصيرة واحدة عند ارتقاء المستوى أو فتح إنجاز (لا شيء إن لم يحدث)."""
    if not s.notable:
        return
    try:
        await bot.send_message(uid, notice(s, L), parse_mode="HTML")
    except Exception:  # noqa: BLE001  (حظر البوت وغيره)
        pass
