"""عناصر شكلية موحّدة: الفاصل، أشرطة التقدم، الرموز، وتنسيق الأرقام."""
from __future__ import annotations

SEP = "━━━━━━━━━━━━━━━━"          # فاصل واحد لكل الرسائل

# رموز الأدوار والحالات: مصدر واحد لكل الألعاب
ICON = {
    "killer": "🔪", "citizen": "🧑", "detective": "🔍", "doctor": "🩺", "mayor": "🎖", "joker": "🃏",
    "turn": "🟢", "wait": "⏳", "vote": "🗳", "win": "🏆", "lose": "😅", "draw": "🤝", "night": "🌙", "day": "☀️",
}


def bar(frac: float, size: int = 8) -> str:
    """شريط تقدّم بالمربعات: ▰▰▰▱▱. frac بين 0 و1 (الجزء المتبقي أو المنجز)."""
    frac = max(0.0, min(1.0, frac))
    filled = round(frac * size)
    return "▰" * filled + "▱" * (size - filled)


def fmt(n: int | float | None) -> str:
    """أرقام بفواصل الآلاف، والقيم الفارغة تُعرض شرطة."""
    if n is None:
        return "—"
    return f"{int(n):,}"
