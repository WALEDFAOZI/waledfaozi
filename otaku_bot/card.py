"""بطاقات الصور بأسلوب المانغا (النتيجة، الملف الشخصي، الموت المفاجئ، والبانر الترحيبي).

لمسات «بشرية»: اهتزاز بسيط في الخطوط والزوايا يختلف من لاعب لآخر، حبيبات ورق، أختام وشريط لاصق مائل، وجُمل قصيرة بنبرة بشرية.
تتطلب خطًا يدعم العربية؛ إن لم يوجد يرجع البوت لرسالة نصية.
"""
from __future__ import annotations

import hashlib
import math
import re

from .art import BLACK, PAPER, S, Canvas, find_font, has_jp
from .config import CATEGORY_LABELS, CATEGORY_LABELS_EN
from .mascot import draw_mascot, mood_for

__all__ = ["find_font", "strip_emoji", "make_card", "make_profile_card", "make_sudden_card", "make_banner", "tier_of"]

# (الحد الأدنى, اسم المستوى, حرف الرتبة)
TIERS = [(9.5, "king", "S+"), (8.0, "sensei", "S"), (6.0, "seasoned", "A"), (4.0, "otaku", "B"), (2.0, "casual", "C"), (0.0, "noob", "D")]
PALETTE = {   # أعلى، أسفل، لون الشريط/الملصقات، لون الجاكيت
    "king": ((52, 10, 84), (255, 45, 111), (214, 40, 80), (255, 99, 132)),
    "sensei": ((28, 20, 100), (123, 47, 247), (196, 52, 74), (150, 110, 255)),
    "seasoned": ((15, 59, 110), (31, 162, 255), (214, 70, 60), (90, 200, 255)),
    "otaku": ((9, 80, 75), (46, 204, 150), (214, 80, 60), (120, 230, 190)),
    "casual": ((90, 62, 20), (230, 165, 58), (190, 60, 50), (255, 200, 90)),
    "noob": ((40, 44, 58), (100, 112, 130), (160, 60, 60), (170, 180, 200)),
}
SFX = {"king": "ドーン!!", "sensei": "ゴゴゴ", "seasoned": "キラッ", "otaku": "パチパチ", "casual": "ふむ…", "noob": "しーん…"}
QUIPS = {
    "ar": {"king": ["ما شاء الله!!", "أسطورة!", "ملك بحق"], "sensei": ["كفو والله!", "سينسي!", "يا سلام"],
           "seasoned": ["ممتاز!", "قريب من القمة", "ماشي حالك"], "otaku": ["مو بطّال", "كمّل يا بطل", "في الطريق"],
           "casual": ["همم… عادي", "تحتاج أنمي أكثر", "لسا بدري"], "noob": ["يا ويلي", "ولا يهمك", "نبدأ من الصفر"]},
    "en": {"king": ["Legendary!!", "Absolute king", "No way!"], "sensei": ["Sugoi!", "Sensei vibes", "Nice one!"],
           "seasoned": ["Solid!", "So close", "Not bad at all"], "otaku": ["Not bad!", "Keep going", "Getting there"],
           "casual": ["Hmm… meh", "Watch more anime", "Too early"], "noob": ["Oh no…", "It's fine", "Start from zero"]},
}


def strip_emoji(text: str) -> str:
    return re.sub(r"[^\w\s/&.\-+]", "", text, flags=re.UNICODE).strip()


def tier_of(score: float) -> tuple[str, str]:
    for threshold, name, letter in TIERS:
        if score >= threshold:
            return name, letter
    return TIERS[-1][1], TIERS[-1][2]


def _seed(*parts) -> str:
    return hashlib.md5("|".join(map(str, parts)).encode("utf-8")).hexdigest()


def _need_font():
    if not find_font():
        raise RuntimeError("no usable font found; set FONT_PATH")


def _ribbon(c: Canvas, box, color, notch=16):
    """شريط عنوان بنهايات «ذيل سنونو»."""
    x0, y0, x1, y1 = box
    mid = (y0 + y1) / 2
    pts = [(x0, y0), (x1, y0), (x1 - notch, mid), (x1, y1), (x0, y1), (x0 + notch, mid)]
    c.d.polygon(c.P([(x + 5, y + 6) for x, y in pts]), fill=(0, 0, 0, 90))
    c.d.polygon(c.P(pts), fill=color)
    c.d.line(c.P(pts + [pts[0]]), fill=BLACK, width=int(3.5 * 2), joint="curve")


def _speech_bubble(c: Canvas, box, text, lang, tail_to=(0, 0)):
    x0, y0, x1, y1 = box
    c.hand_rect(box, fill=PAPER, outline=BLACK, width=3.2, amp=1.2)
    tx, ty = tail_to
    bx = (x0 + x1) / 2
    c.d.polygon(c.P([(bx - 14, y1 - 2), (bx + 12, y1 - 2), (tx, ty)]), fill=PAPER)
    c.d.line(c.P([(bx - 14, y1 - 1), (tx, ty), (bx + 12, y1 - 1)]), fill=BLACK, width=int(3.2 * 2), joint="curve")
    size = c.fit(text, "ar", 28, x1 - x0 - 22)
    c.text(((x0 + x1) / 2, (y0 + y1) / 2 + 1), text, "ar", size, fill=BLACK)


def _name_tag(c: Canvas, name, box, tilt=-2):
    x0, y0, x1, y1 = box
    c.hand_rect(box, fill=PAPER, outline=BLACK, width=3, amp=1.0)
    c.d.ellipse(c.B((x0 + 12, (y0 + y1) / 2 - 5, x0 + 22, (y0 + y1) / 2 + 5)), fill=(120, 110, 130))        # ثقب الشريط
    size = c.fit(name, "ar", 32, x1 - x0 - 56)
    c.text(((x0 + x1) / 2 + 8, (y0 + y1) / 2 + 1), name, "ar", size, fill=BLACK)
    c.tape((x1 - 24, y0 + 2), 58, 20, 18)


def _scene(c: Canvas, tier, center, focus_r=150):
    top, bottom, accent, jacket = PALETTE[tier]
    c.gradient(top, bottom)
    c.halftone((0, c.h * 0.5, c.w * 0.5, c.h), (255, 255, 255), toward=(-1, 1), alpha=60)
    c.halftone((c.w * 0.55, 0, c.w, c.h * 0.45), (0, 0, 0), toward=(1, -1), alpha=45)
    c.speed_lines(center, focus_r, max(c.w, c.h) * 0.8, n=80)
    return accent, jacket


def make_card(name: str, score: float, title: str, percentile: float | None,
              breakdown: dict[str, tuple[int, int]], lang: str = "ar", mode_text: str | None = None,
              handle: str = "@Otaku1GalaxyBot") -> bytes:
    """بطاقة نتيجة الاختبار."""
    _need_font()
    en = lang == "en"
    tier, letter = tier_of(score)
    seed = _seed(name, score)
    c = Canvas(900, 560, seed)
    accent, jacket = _scene(c, tier, (655, 240), 150)
    labels = CATEGORY_LABELS_EN if en else CATEGORY_LABELS
    c.sakura(9, (20, 330, 880, 545), (8, 15))

    # الشخصية + فقاعة كلام
    draw_mascot(c, 190, 330, 245, mood_for(score), seed, jacket)
    quip = c.rng.choice(QUIPS["en" if en else "ar"][tier])
    _speech_bubble(c, (36, 34, 330, 104), quip, lang, tail_to=(150, 168))
    if mode_text:
        c.hand_rect((40, 118, 40 + c.text_width(mode_text, "ar", 20) + 26, 150), fill=(255, 235, 140), width=2.4)
        c.text((53 + c.text_width(mode_text, "ar", 20) / 2, 134), mode_text, "ar", 20, fill=BLACK)

    # بطاقة الاسم
    _name_tag(c, name[:26], (452, 26, 868, 82))

    # مؤثر صوتي ياباني + بالونة الدرجة
    if has_jp():
        c.text((508, 112), SFX[tier], "jp", 48, fill=(255, 235, 140), stroke=4, rotate=-9, arabic=False)
    c.starburst((655, 250), 178, 138, spikes=15, fill=PAPER, width=4.4)
    sc = f"{score:.1f}"
    c.text((638, 246), sc, "display", 112, fill=(255, 255, 255), stroke=7, shadow=4, arabic=False)
    c.text((772, 296), "/10", "display", 40, fill=(255, 235, 140), stroke=4, arabic=False)
    c.hanko((822, 128), 46, letter, "RANK" if en else "الرتبة", angle=-13)

    # شريط اللقب
    t = strip_emoji(title)
    _ribbon(c, (450, 398, 872, 462), accent)
    c.text((661, 430), t, "ar", c.fit(t, "ar", 42, 340), fill=(255, 255, 255), stroke=3.2, shadow=2)

    # أفضل من …% + شرائح التصنيفات
    y = 484
    if percentile is not None:
        txt = f"Better than {percentile:.0f}% of players" if en else f"أفضل من {percentile:.0f}% من اللاعبين"
        c.text((661, y), txt, "ar", 24, fill=(255, 255, 255), stroke=2.6)
        y += 36
    best = sorted(breakdown.items(), key=lambda kv: -kv[1][0] / max(kv[1][1], 1))[:3]
    if best:
        w = 132
        x = 661 - (len(best) * w + (len(best) - 1) * 8) / 2
        for cat, (ok, total) in best:
            c.hand_rect((x, y - 14, x + w, y + 22), fill=PAPER, width=2.6, amp=0.9)
            lab = labels.get(cat, cat)
            c.text((x + w / 2, y - 1), f"{lab} {ok}/{total}", "ar", c.fit(f"{lab} {ok}/{total}", "ar", 20, w - 14), fill=BLACK)
            x += w + 8
    c.text((24, 540), handle, "ar", 20, fill=(255, 255, 255), stroke=2.4, anchor="lm", arabic=False)
    return c.jpeg()


def make_profile_card(p: dict, title: str, lang: str = "ar", handle: str = "@Otaku1GalaxyBot") -> bytes:
    """بطاقة الملف الشخصي."""
    _need_font()
    en = lang == "en"
    best = float(p.get("best") or 0)
    tier, letter = tier_of(best)
    seed = _seed(p.get("name"), best, "profile")
    c = Canvas(900, 600, seed)
    accent, jacket = _scene(c, tier, (640, 250), 150)
    labels = CATEGORY_LABELS_EN if en else CATEGORY_LABELS
    c.sakura(8, (20, 360, 880, 590), (8, 14))
    draw_mascot(c, 150, 275, 190, mood_for(best), seed, jacket)

    heading = "OTAKU PROFILE" if en else "ملف الأوتاكو"
    c.text((660, 52), heading, "ar", c.fit(heading, "ar", 50, 380), fill=(255, 220, 90), stroke=5, shadow=3, rotate=-2)
    _name_tag(c, (p.get("name") or "")[:24], (452, 92, 868, 146))

    c.starburst((650, 275), 162, 126, spikes=14, fill=PAPER, width=4.4)
    c.text((640, 270), f"{best:.1f}", "display", 100, fill=(255, 255, 255), stroke=7, shadow=4, arabic=False)
    c.text((762, 318), "/10", "display", 36, fill=(255, 235, 140), stroke=4, arabic=False)
    c.hanko((820, 168), 44, letter, "BEST" if en else "الأفضل", angle=12)

    t = strip_emoji(title)
    _ribbon(c, (440, 432, 868, 492), accent)
    c.text((654, 462), t, "ar", c.fit(t, "ar", 40, 340), fill=(255, 255, 255), stroke=3, shadow=2)

    # لوحات إحصائيات على طريقة صفحات المانغا
    stats = []
    if p.get("rank"):
        stats.append((f"#{p['rank']}", "Overall rank" if en else "الترتيب العام"))
    if p.get("weekly_rank"):
        stats.append((f"#{p['weekly_rank']}", "This week" if en else "هذا الأسبوع"))
    stats.append((str(p.get("tests", 0)), "Full tests" if en else "اختبارات كاملة"))
    if p.get("answers"):
        stats.append((f"{round(100 * p['correct'] / p['answers'])}%", "Accuracy" if en else "الدقة"))
    if p.get("sudden"):
        stats.append((str(p["sudden"]), "Sudden death" if en else "موت مفاجئ"))
    stats = stats[:4]
    pw, gap = 112, 8
    x = 640 - (len(stats) * pw + (len(stats) - 1) * gap) / 2
    for i, (val, lab) in enumerate(stats):
        y0 = 512 + (4 if i % 2 else -2)          # ارتفاعات مختلفة قليلًا: لمسة يدوية
        c.hand_rect((x, y0, x + pw, y0 + 66), fill=PAPER, width=3, amp=1.3)
        c.text((x + pw / 2, y0 + 24), val, "display", 30, fill=BLACK, arabic=False)
        c.text((x + pw / 2, y0 + 51), lab, "ar", c.fit(lab, "ar", 17, pw - 12), fill=(90, 80, 110))
        x += pw + gap

    # أقوى التصنيفات
    cats = (p.get("cats") or [])[:3]
    y = 392 - len(cats) * 0
    if cats:
        c.text((160, 470), "Strongest" if en else "أقوى تصنيفاتك", "ar", 22, fill=(255, 235, 140), stroke=3)
        yy = 494
        for cat, acc, n in cats:
            lab = labels.get(cat, cat)
            c.text((24, yy + 9), lab, "ar", c.fit(lab, "ar", 18, 112), fill=(255, 255, 255), stroke=2.2, anchor="lm")
            c.hand_rect((140, yy, 280, yy + 18), fill=(40, 30, 70), outline=BLACK, width=2.2, amp=0.6)
            c.d.rectangle(c.B((142, yy + 2, 142 + 136 * acc, yy + 16)), fill=(255, 214, 102))
            c.text((290, yy + 9), f"{acc * 100:.0f}%", "ar", 17, fill=(255, 255, 255), stroke=2.2, anchor="lm", arabic=False)
            yy += 27
    c.text((24, 590), handle, "ar", 16, fill=(255, 255, 255), stroke=2.2, anchor="lm", arabic=False)
    return c.jpeg()


def make_sudden_card(name: str, streak: int, level: int, best: int, lang: str = "ar",
                     handle: str = "@Otaku1GalaxyBot") -> bytes:
    """بطاقة «الموت المفاجئ»."""
    _need_font()
    en = lang == "en"
    score_equiv = min(10.0, streak / 5)                 # مزاج الشخصية: 50 صحيحة متتالية = ممتاز
    tier, letter = tier_of(score_equiv)
    seed = _seed(name, streak, "sd")
    c = Canvas(900, 560, seed)
    accent, jacket = _scene(c, "noob" if streak < 5 else tier, (650, 250), 150)
    draw_mascot(c, 190, 330, 245, mood_for(score_equiv + (1 if streak >= 5 else 0)), seed, jacket)
    _name_tag(c, name[:26], (452, 26, 868, 82))
    if has_jp():
        c.text((560, 118), "ゴゴゴ" if streak >= 10 else "しーん…", "jp", 50, fill=(255, 235, 140), stroke=4, rotate=-9, arabic=False)
    c.starburst((655, 250), 176, 136, spikes=16, fill=PAPER, width=4.4)
    c.text((655, 240), str(streak), "display", 120, fill=(255, 255, 255), stroke=7, shadow=4, arabic=False)
    c.text((655, 318), "IN A ROW" if en else "إجابة متتالية", "ar", 26, fill=BLACK)
    _ribbon(c, (450, 398, 872, 462), (190, 40, 60))
    label = "SUDDEN DEATH" if en else "الموت المفاجئ"
    c.text((661, 430), label, "ar", c.fit(label, "ar", 40, 340), fill=(255, 255, 255), stroke=3.2, shadow=2)
    sub = f"Fell at level {level} · record {best}" if en else f"سقطت عند المستوى {level} · رقمك القياسي {best}"
    c.text((661, 488), sub, "ar", c.fit(sub, "ar", 24, 400), fill=(255, 255, 255), stroke=2.6)
    c.text((24, 540), handle, "ar", 20, fill=(255, 255, 255), stroke=2.4, anchor="lm", arabic=False)
    return c.jpeg()


def make_banner(lang: str = "ar", handle: str = "@Otaku1GalaxyBot", title_ar: str = "اختبار الأوتاكو",
                title_en: str = "OTAKU QUIZ", mood: str = "crown", tag_ar: str | None = None,
                tag_en: str | None = None) -> bytes:
    """لافتة اللعبة: عنوانها حسب نوع اللعبة (المافيا، برا السالفة، الاختبار...)."""
    _need_font()
    c = Canvas(1280, 640, "banner")
    c.gradient((40, 12, 80), (255, 60, 120))
    c.halftone((0, 320, 640, 640), (255, 255, 255), toward=(-1, 1), alpha=60, max_r=4.2, spacing=12)
    c.halftone((700, 0, 1280, 300), (0, 0, 0), toward=(1, -1), alpha=45, max_r=4.2, spacing=12)
    c.speed_lines((420, 330), 200, 900, n=110)
    c.sakura(16, (20, 20, 1260, 620), (10, 22))
    draw_mascot(c, 330, 360, 330, mood, "banner", (255, 99, 132))
    if has_jp():
        c.text((820, 118), "オタク", "jp", 84, fill=(255, 235, 140), stroke=6, rotate=-6, arabic=False)
    c.starburst((880, 330), 330, 270, spikes=18, fill=PAPER, width=5)
    c.text((880, 310), title_ar, "ar", c.fit(title_ar, "ar", 92, 480), fill=(255, 255, 255), stroke=8, shadow=5, rotate=-2)
    c.text((880, 410), title_en, "display", 62, fill=(255, 220, 90), stroke=6, shadow=3, arabic=False, rotate=-2)
    _ribbon(c, (640, 496, 1130, 566), (214, 40, 80))
    tag = (tag_ar or "1400+ سؤال · ألعاب · تحديات") if lang == "ar" else (tag_en or "1400+ questions · games · challenges")
    c.text((885, 531), tag, "ar", c.fit(tag, "ar", 34, 430), fill=(255, 255, 255), stroke=3)
    c.hanko((1165, 150), 70, "10", "/10", angle=-12)
    return c.jpeg(grain=0.04)


def _role_icon(c: Canvas, key: str, cx: float, cy: float, r: float) -> None:
    """أيقونة الدور بأشكال بسيطة (بدون إيموجي): خنجر، صليب، عدسة، درع، شخص."""
    w = int(3 * S)
    if key == "killer":                                  # خنجر
        c.d.polygon(c.P([(cx - 4, cy - r), (cx + 4, cy - r), (cx + 4, cy + r * 0.3), (cx, cy + r * 0.55),
                         (cx - 4, cy + r * 0.3)]), fill=(220, 225, 235, 255), outline=BLACK)
        c.d.rectangle(c.B((cx - 9, cy + r * 0.3, cx + 9, cy + r * 0.6)), fill=(120, 60, 30, 255), outline=BLACK)
    elif key == "doctor":                                # صليب طبي
        c.d.rectangle(c.B((cx - r * 0.3, cy - r, cx + r * 0.3, cy + r)), fill=(230, 40, 60, 255), outline=BLACK)
        c.d.rectangle(c.B((cx - r, cy - r * 0.3, cx + r, cy + r * 0.3)), fill=(230, 40, 60, 255), outline=BLACK)
    elif key == "detective":                             # عدسة مكبّرة
        c.d.ellipse(c.B((cx - r * 0.7, cy - r * 0.7, cx + r * 0.35, cy + r * 0.35)), outline=BLACK, width=w * 2,
                    fill=(200, 230, 255, 255))
        c.d.line(c.P([(cx + r * 0.2, cy + r * 0.2), (cx + r, cy + r)]), fill=BLACK, width=w * 2)
    elif key == "guard":                                 # درع
        c.d.polygon(c.P([(cx - r * 0.8, cy - r), (cx + r * 0.8, cy - r), (cx + r * 0.8, cy), (cx, cy + r),
                         (cx - r * 0.8, cy)]), fill=(180, 190, 200, 255), outline=BLACK)
    else:                                                # شخص عادي
        c.d.ellipse(c.B((cx - r * 0.4, cy - r, cx + r * 0.4, cy - r * 0.2)), fill=(240, 200, 170, 255), outline=BLACK)
        c.d.polygon(c.P([(cx - r * 0.7, cy + r), (cx + r * 0.7, cy + r), (cx + r * 0.4, cy), (cx - r * 0.4, cy)]),
                    fill=(90, 120, 200, 255), outline=BLACK)


def _cards_banner(title_ar: str, title_en: str, tag: str, cards: list, theme: tuple, seed: str) -> bytes:
    """لافتة بعنوان وشريط ووصف، وصفّ من البطاقات (شخصية + أيقونة + اسم)."""
    _need_font()
    c = Canvas(1280, 640, seed)
    top, bottom, accent = theme
    c.gradient(top, bottom)
    c.halftone((0, 330, 1280, 640), accent, toward=(0, 1), alpha=40, max_r=3.6, spacing=14)
    c.speed_lines((640, 200), 150, 900, n=90, color=accent, alpha=35)
    c.text((640, 150), title_ar, "ar", c.fit(title_ar, "ar", 130, 700), fill=(255, 255, 255), stroke=10, shadow=6)
    c.text((640, 232), title_en, "display", 70, fill=(255, 220, 90), stroke=6, shadow=3, arabic=False)
    _ribbon(c, (200, 262, 1080, 322), accent)
    c.text((640, 292), tag, "ar", c.fit(tag, "ar", 34, 760), fill=(255, 255, 255), stroke=3)
    for i, (key, label, jacket, mood) in enumerate(cards):
        x0 = 50 + i * 244
        x1, y0, y1 = x0 + 220, 350, 600
        c.d.rounded_rectangle(c.B((x0, y0, x1, y1)), radius=18 * S, fill=(20, 10, 24, 235),
                              outline=(255, 220, 90, 255) if key == "outsider" else (255, 255, 255, 230), width=4 * S)
        draw_mascot(c, x0 + 110, 430, 110, mood, key, jacket)
        _role_icon(c, key, x0 + 34, y0 + 34, 22)
        c.d.rounded_rectangle(c.B((x0 + 10, 536, x1 - 10, 590)), radius=12 * S, fill=(0, 0, 0, 200))
        c.text((x0 + 110, 563), label, "ar", c.fit(label, "ar", 36, 200), fill=(255, 255, 255), stroke=3)
    return c.jpeg(grain=0.04)


def make_mafia_banner(lang: str = "ar", handle: str = "@Otaku1GalaxyBot") -> bytes:
    """لافتة المافيا: أدوار اللعبة (القاتل، الطبيب، المحقق، الحارس، المواطن) بأشكالها وأيقوناتها."""
    cards = [("killer", "القاتل", (60, 20, 30), "sweat"), ("doctor", "الطبيب", (235, 245, 250), "happy"),
             ("detective", "المحقق", (40, 70, 130), "star"), ("guard", "الحارس", (30, 110, 70), "smile"),
             ("citizen", "المواطن", (120, 120, 130), "smile")]
    return _cards_banner("المافيا", "MAFIA", "القتلة · الطبيب · المحقق · الحارس · المواطنون", cards,
                         ((10, 6, 18), (72, 8, 26), (200, 30, 60)), "mafia")


def make_spy_banner(lang: str = "ar", handle: str = "@Otaku1GalaxyBot") -> bytes:
    """لافتة برا السالفة: لاعبون يتشابهون، ومتطفل واحد مختلف."""
    same = [("player", "لاعب", (60, 90, 150), "smile")] * 4
    cards = [("player", "لاعب", (60, 90, 150), "smile"), ("player", "لاعب", (60, 90, 150), "happy"),
             ("player", "لاعب", (60, 90, 150), "star"), ("outsider", "المتطفل", (230, 170, 40), "sweat"),
             ("player", "لاعب", (60, 90, 150), "smile")]
    return _cards_banner("برا السالفة", "ODD ONE OUT", "الكل يعرف الموضوع... إلا واحد!", cards,
                         ((8, 16, 30), (20, 50, 90), (60, 160, 230)), "spy")
