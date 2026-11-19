"""شكل موحّد لكل الترتيبات (عام/أسبوعي/اليوم/الموت/الألعاب/المجموعات/العشائر).

- كل سطر: ميدالية أو رقم ثابت · الاسم · القيمة، وخط فاصل يبقي الشكل مرتبًا.
- الاسم يُعزل باتجاهه (FSI/PDI) حتى لا تختلط الأسماء العربية والإنجليزية في السطر الواحد.
- الاسم مقصوص لطول ثابت حتى لا يكسر الأسطر.
"""
from __future__ import annotations

import html

RULE = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
MAX_NAME = 16
MEDALS = ["🥇", "🥈", "🥉"]
FSI, PDI = "⁨", "⁩"


def clean(name: str | None) -> str:
    n = " ".join((name or "?").split()) or "?"
    return n if len(n) <= MAX_NAME else n[: MAX_NAME - 1] + "…"


def name_html(name: str | None) -> str:
    return FSI + html.escape(clean(name), quote=False) + PDI


def row(i: int, name: str | None, value: str) -> str:
    badge = MEDALS[i - 1] if i <= 3 else f"<b>{i}.</b>"
    return f"{badge} {name_html(name)}  ·  <b>{value}</b>"


def render(title: str, pairs: list[tuple[str | None, str]], empty: str, footer: str = "") -> str:
    """pairs = [(الاسم, القيمة)] بالترتيب. العنوان فوق، والتذييل (ترتيبك) تحت."""
    body = "\n".join(row(i, n, v) for i, (n, v) in enumerate(pairs, 1)) or empty
    parts = [title, RULE, body, RULE]
    if footer:
        parts.append(footer)
    return "\n".join(parts)
