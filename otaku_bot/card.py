"""بطاقة النتيجة كصورة PNG. تحتاج خطًا يدعم العربية؛ إن لم يوجد يرجع البوت لرسالة نصية."""
from __future__ import annotations

import io
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features

from .config import CATEGORY_LABELS, CATEGORY_LABELS_EN, ROOT

_FONT_CANDIDATES = [
    os.getenv("FONT_PATH", ""),
    str(ROOT / "assets" / "font.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def find_font() -> str | None:
    return next((p for p in _FONT_CANDIDATES if p and Path(p).is_file()), None)


def _ar(text: str) -> str:
    # مع raqm يتولى Pillow التشكيل والاتجاه بنفسه؛ بدونه نشكّل ونعكس يدويًا
    if features.check("raqm"):
        return text
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(text))


def strip_emoji(text: str) -> str:
    return re.sub(r"[^\w\s/&.\-]", "", text, flags=re.UNICODE).strip()


def make_card(name: str, score: float, title: str, percentile: float | None,
              breakdown: dict[str, tuple[int, int]], lang: str = "ar") -> bytes:
    font_path = find_font()
    if not font_path:
        raise RuntimeError("no usable font found; set FONT_PATH")

    W, H = 900, 560
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):  # تدرّج بنفسجي → وردي
        t = y / (H - 1)
        row = (int(40 + 120 * t), int(18 + 20 * t), int(90 + 40 * t))
        for x in range(W):
            px[x, y] = row
    d = ImageDraw.Draw(img)

    def font(size: int):
        engine = ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC
        return ImageFont.truetype(font_path, size, layout_engine=engine)

    def center(text: str, y: int, size: int, fill=(255, 255, 255)):
        f = font(size)
        w = d.textlength(text, font=f)
        d.text(((W - w) / 2, y), text, font=f, fill=fill)

    en = lang == "en"
    labels = CATEGORY_LABELS_EN if en else CATEGORY_LABELS
    center(_ar("Otaku Rating" if en else "تقييم الأوتاكو"), 28, 40, (255, 214, 102))
    center(_ar(name[:28]), 90, 34)
    center(f"{score:.1f} / 10", 140, 120, (255, 255, 255))
    center(_ar(strip_emoji(title)), 285, 50, (255, 214, 102))
    if percentile is not None:
        txt = f"Better than {percentile:.0f}% of players" if en else f"أفضل من {percentile:.0f}% من اللاعبين"
        center(_ar(txt), 350, 28, (225, 220, 255))

    rows = sorted(breakdown.items(), key=lambda kv: kv[1][0] / max(kv[1][1], 1), reverse=True)[:3]
    y = 415
    for cat, (ok, total) in rows:
        label = _ar(labels.get(cat, cat))
        pct = ok / total if total else 0
        d.text((W - 90 - d.textlength(label, font=font(24)), y), label, font=font(24), fill=(255, 255, 255))
        x0, x1 = 90, 560
        d.rounded_rectangle((x0, y + 6, x1, y + 28), 10, fill=(70, 40, 120))
        if pct > 0:
            d.rounded_rectangle((x0, y + 6, x0 + (x1 - x0) * pct, y + 28), 10, fill=(255, 214, 102))
        d.text((x1 + 14, y), f"{ok}/{total}", font=font(24), fill=(255, 255, 255))
        y += 42

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
