"""أسماء الأنمي والشخصيات: في الوضع العربي تُعرض «عربي (English)» داخل الأسئلة والخيارات."""
from __future__ import annotations

import json
import re
from functools import lru_cache

from .config import ROOT


@lru_cache(maxsize=1)
def _load():
    try:
        d = json.loads((ROOT / "data" / "names_ar.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, {}, None
    names, opt_only = d.get("names", {}), d.get("option_only", {})
    keys = sorted((k for k in names if k.strip()), key=len, reverse=True)       # الأطول أولًا (Naruto Uzumaki قبل Naruto)
    pat = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(k) for k in keys) + r")(?![A-Za-z0-9])") if keys else None
    return names, opt_only, pat


def loc(text: str, lang: str = "ar", option: bool = False) -> str:
    """يضيف الاسم العربي بجانب كل اسم إنجليزي معروف (تمريرة واحدة، فلا يتكرر الاستبدال). الإنجليزية لا تتغير."""
    if lang != "ar" or not text:
        return text
    names, opt_only, pat = _load()
    if option and text in opt_only:
        return f"{opt_only[text]} ({text})"
    if pat is None:
        return text
    return pat.sub(lambda m: f"{names[m.group(0)]} ({m.group(0)})", text)


def loc_opt(text: str, lang: str = "ar") -> str:
    return loc(text, lang, option=True)
