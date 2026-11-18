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


def make_profile_card(p: dict, title: str, lang: str = "ar") -> bytes:
    """بطاقة الملف الشخصي: الاسم واللقب وأفضل تقييم والترتيب وأقوى التصنيفات."""
    font_path = find_font()
    if not font_path:
        raise RuntimeError("no usable font found; set FONT_PATH")
    en = lang == "en"
    labels = CATEGORY_LABELS_EN if en else CATEGORY_LABELS
    W, H = 900, 600
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        row = (int(20 + 50 * t), int(40 + 20 * t), int(95 + 55 * t))     # تدرّج أزرق (يميّزها عن بطاقة النتيجة)
        for x in range(W):
            px[x, y] = row
    d = ImageDraw.Draw(img)
    engine = ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC

    def font(size: int):
        return ImageFont.truetype(font_path, size, layout_engine=engine)

    def center(text: str, y: int, size: int, fill=(255, 255, 255)):
        f = font(size)
        d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)

    center(_ar("Otaku Profile" if en else "ملف الأوتاكو"), 24, 36, (255, 214, 102))
    center(_ar((p.get("name") or "")[:28]), 78, 40)
    center(f"{p['best']:.1f} / 10", 128, 100)
    center(_ar(strip_emoji(title)), 245, 44, (255, 214, 102))

    stats = []
    if p.get("rank"):
        stats.append((f"#{p['rank']}", "Overall rank" if en else "الترتيب العام"))
    if p.get("weekly_rank"):
        stats.append((f"#{p['weekly_rank']}", "This week" if en else "هذا الأسبوع"))
    stats.append((str(p.get("tests", 0)), "Full tests" if en else "اختبارات كاملة"))
    if p.get("answers"):
        stats.append((f"{round(100 * p['correct'] / p['answers'])}%", "Accuracy" if en else "الدقة"))
    if p.get("sudden"):
        stats.append((str(p["sudden"]), "Sudden death" if en else "الموت المفاجئ"))
    stats = stats[:5]
    slot = W / max(len(stats), 1)
    for i, (val, label) in enumerate(stats):
        cx = slot * i + slot / 2
        fv, fl = font(42), font(22)
        d.text((cx - d.textlength(val, font=fv) / 2, 318), val, font=fv, fill=(255, 255, 255))
        lab = _ar(label)
        d.text((cx - d.textlength(lab, font=fl) / 2, 372), lab, font=fl, fill=(200, 215, 255))

    y = 430
    for cat, acc, n in (p.get("cats") or [])[:3]:
        label = _ar(labels.get(cat, cat))
        d.text((W - 90 - d.textlength(label, font=font(24)), y), label, font=font(24), fill=(255, 255, 255))
        x0, x1 = 90, 560
        d.rounded_rectangle((x0, y + 6, x1, y + 28), 10, fill=(40, 60, 120))
        if acc > 0:
            d.rounded_rectangle((x0, y + 6, x0 + (x1 - x0) * acc, y + 28), 10, fill=(255, 214, 102))
        d.text((x1 + 14, y), f"{acc * 100:.0f}%", font=font(24), fill=(255, 255, 255))
        y += 42

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
