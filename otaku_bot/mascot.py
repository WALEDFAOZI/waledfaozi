"""«أوتاكو-تشان»: شخصية صغيرة بأسلوب الأنمي تتغير ملامحها مع النتيجة (مرسومة بالكود، بلا صور جاهزة)."""
from __future__ import annotations

import math
import random

from .art import BLACK, Canvas, has_jp, font, shape

SKIN = (255, 228, 210)
HAIRS = [(43, 27, 77), (31, 42, 68), (91, 42, 134), (138, 45, 59), (36, 90, 70), (60, 48, 40)]
IRISES = [(70, 140, 255), (255, 140, 70), (120, 80, 220), (60, 190, 150), (230, 80, 130)]

# النتيجة ← مزاج الشخصية
def mood_for(score: float) -> str:
    if score >= 9.5:
        return "crown"
    if score >= 8:
        return "star"
    if score >= 6:
        return "happy"
    if score >= 4:
        return "smile"
    if score >= 2:
        return "sweat"
    return "dizzy"


def draw_mascot(c: Canvas, cx: float, cy: float, size: float, mood: str = "smile", seed: str = "x",
                jacket=(255, 99, 132)) -> None:
    rng = random.Random(seed)
    hair = rng.choice(HAIRS)
    iris = rng.choice(IRISES)
    u = size / 100.0
    lw = max(2.6, 3.0 * u)            # سماكة خط الحبر
    d, P, B = c.d, c.P, c.B

    def ell(x0, y0, x1, y1, fill, outline=BLACK, w=lw):
        d.ellipse(B((cx + x0 * u, cy + y0 * u, cx + x1 * u, cy + y1 * u)), fill=fill, outline=outline, width=int(w * 2) if outline else 0)

    def poly(pts, fill, outline=BLACK, w=lw):
        q = [(cx + x * u, cy + y * u) for x, y in pts]
        d.polygon(P(q), fill=fill)
        if outline:
            d.line(P(q + [q[0]]), fill=outline, width=int(w * 2), joint="curve")

    def line(pts, w=lw * 1.1, fill=BLACK):
        d.line(P([(cx + x * u, cy + y * u) for x, y in pts]), fill=fill, width=int(w * 2), joint="curve")

    # شعر خلفي + جانبي
    ell(-49, -52, 49, 42, hair)
    poly([(-49, -2), (-52, 40), (-40, 58), (-34, 30)], hair)
    poly([(49, -2), (52, 40), (40, 58), (34, 30)], hair)
    # جاكيت وعنق
    poly([(-58, 100), (-46, 52), (-12, 40), (12, 40), (46, 52), (58, 100)], jacket)
    poly([(-12, 40), (0, 56), (12, 40)], (255, 255, 255))
    ell(-9, 30, 9, 46, SKIN)
    # وجه
    ell(-42, -38, 42, 38, SKIN)
    # خدود
    def blush(d_):
        for sx in (-1, 1):
            x = cx + sx * 27 * u
            y = cy + 21 * u
            d_.ellipse(B((x - 8 * u, y - 4.5 * u, x + 8 * u, y + 4.5 * u)), fill=(255, 120, 150, 150 if mood != "sweat" else 90))
    c.overlay(blush)
    # أعين
    ey = 9
    for sx in (-1, 1):
        ex = sx * 17
        if mood == "happy":                      # ^ ^
            line([(ex - 9, ey + 3), (ex - 4, ey - 6), (ex, ey - 8), (ex + 4, ey - 6), (ex + 9, ey + 3)], w=lw * 1.4)
        elif mood == "dizzy":                    # دوّامات
            for k, rr in enumerate((10, 7, 4)):
                d.arc(B((cx + (ex - rr) * u, cy + (ey - rr) * u, cx + (ex + rr) * u, cy + (ey + rr) * u)),
                      start=30 + k * 60, end=330 + k * 60, fill=BLACK, width=int(lw * 1.3))
        else:
            ry = 9 if mood == "sweat" else 12
            ell(ex - 9.5, ey - ry, ex + 9.5, ey + ry, (255, 255, 255))
            if mood in ("star", "crown"):
                c.sparkle(cx + ex * u, cy + (ey + 1) * u, 8.5 * u, fill=(255, 205, 60), outline=BLACK, width=1.6)
            else:
                ell(ex - 7, ey - ry + 2, ex + 7, ey + ry - 1, iris, outline=None)
                ell(ex - 3.6, ey - 5, ex + 3.6, ey + 5, BLACK, outline=None)
            ell(ex - 5.2, ey - 7, ex - 1.2, ey - 3, (255, 255, 255), outline=None)
            ell(ex + 1.5, ey + 2, ex + 4, ey + 4.5, (255, 255, 255), outline=None)
            d.arc(B((cx + (ex - 9.5) * u, cy + (ey - ry) * u, cx + (ex + 9.5) * u, cy + (ey + ry) * u)),
                  start=195, end=345, fill=BLACK, width=int(lw * 2.1))
        # حاجب
        if mood == "sweat":
            line([(ex - sx * 9, ey - 19), (ex + sx * 8, ey - 15)], w=lw * 1.2)
        elif mood != "dizzy":
            line([(ex - 8, ey - 17), (ex + 8, ey - 19)], w=lw * 1.1)
    # فم
    my = 27
    if mood in ("star", "crown"):
        poly([(-9, my - 3), (9, my - 3), (7, my + 8), (0, my + 12), (-7, my + 8)], (150, 40, 60))
        ell(-4.5, my + 5, 4.5, my + 11, (255, 130, 140), outline=None)
    elif mood == "happy":
        poly([(-8, my - 2), (8, my - 2), (4, my + 8), (-4, my + 8)], (150, 40, 60))
    elif mood == "smile":
        d.arc(B((cx - 9 * u, cy + (my - 8) * u, cx + 9 * u, cy + (my + 6) * u)), start=20, end=160, fill=BLACK, width=int(lw * 1.5))
    elif mood == "sweat":
        line([(-8, my + 3), (-4, my), (0, my + 3), (4, my), (8, my + 3)], w=lw)
    else:                                         # dizzy
        ell(-3.5, my - 1, 3.5, my + 6, (150, 40, 60))
    # شعر أمامي (غرّة مسننة) + أهوجي
    top = [(math.cos(math.radians(a)) * 46, -6 + math.sin(math.radians(a)) * 45) for a in range(192, 349, 12)]
    zig = []
    xs = [40 - i * 80 / 8 for i in range(9)]
    for i, x in enumerate(xs):
        zig.append((x, -14 if i % 2 == 0 else (-2 if i not in (0, 8) else -14)))
    poly(top + zig, hair)
    line([(0, -50), (-4, -64), (4, -72), (14, -70)], w=lw * 1.3, fill=hair)            # ahoge
    line([(0, -50), (-4, -64), (4, -72), (14, -70)], w=lw * 0.5, fill=BLACK)
    # عصابة الرأس (هاتشيماكي)
    poly([(-43, -23), (43, -23), (42, -13), (-42, -13)], (255, 255, 255))
    d.ellipse(B((cx - 4 * u, cy - 21 * u, cx + 4 * u, cy - 15 * u)), fill=(205, 38, 52))
    poly([(40, -22), (58, -30), (52, -20)], (255, 255, 255))
    poly([(40, -14), (56, -6), (50, -18)], (255, 255, 255))
    # قطرة عرق (بعد الشعر حتى تظهر)
    if mood == "sweat":
        poly([(47, 0), (54, 15), (47, 22), (40, 15)], (150, 215, 255))
        line([(46, 6), (47, 14)], w=lw * 0.5, fill=(255, 255, 255))
    # تاج
    if mood == "crown":
        poly([(-22, -62), (-24, -80), (-12, -70), (0, -86), (12, -70), (24, -80), (22, -62)], (255, 205, 60))
        for x in (-12, 0, 12):
            ell(x - 2.2, -72 if x else -78, x + 2.2, -67.5 if x else -73.5, (220, 60, 90), outline=BLACK, w=1)
    # نجوم/لمعان
    if mood in ("star", "crown"):
        for (x, y, r) in ((-62, -24, 10), (60, -34, 8), (-54, 22, 6), (58, 20, 7)):
            c.sparkle(cx + x * u, cy + y * u, r * u)
    if mood == "dizzy":
        for (x, y) in ((-48, -50), (0, -70), (48, -46)):
            c.sparkle(cx + x * u, cy + y * u, 6 * u, fill=(255, 255, 255))
