"""رسم بطاقات بأسلوب المانغا: خطوط السرعة، نقاط الـscreentone، بالونات مسنّنة، ختم هانكو، وشخصية «أوتاكو-تشان».

كل شيء يُرسم بـ Pillow فقط (بدون صور جاهزة) ويُرسم بدقة مضاعفة ثم يُصغَّر لتنعيم الحواف.
الاهتزاز البسيط في الخطوط والزوايا مقصود: يعطي إحساس اليد البشرية، ويتغير لكل لاعب (يعتمد على اسمه) فلا تتشابه بطاقتان.
"""
from __future__ import annotations

import io
import math
import os
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, features

from .config import ROOT

S = 2                         # دقة مضاعفة ثم تصغير (anti-aliasing)
BLACK = (24, 18, 38)          # «حبر» المانغا: أسود مائل للبنفسجي أنعم من الأسود الصرف
PAPER = (255, 250, 240)

_FONT_CANDIDATES = [
    os.getenv("FONT_PATH", ""), str(ROOT / "assets" / "font.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Unicode.ttf", "C:/Windows/Fonts/arialbd.ttf",
]
_DISPLAY = [str(ROOT / "assets" / "fonts" / "Inter-Black.otf")]
_JP = [str(ROOT / "assets" / "fonts" / "ipagp.ttf"), "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"]


def _first(paths):
    return next((p for p in paths if p and Path(p).is_file()), None)


def find_font() -> str | None:
    return _first(_FONT_CANDIDATES)


def has_jp() -> bool:
    return _first(_JP) is not None


def _engine():
    return ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC


def shape(text: str) -> str:
    """عربي: مع raqm يتولى Pillow التشكيل والاتجاه؛ بدونه نشكّل ونعكس يدويًا."""
    if features.check("raqm"):
        return text
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(text))


def font(kind: str, size: float) -> ImageFont.FreeTypeFont:
    """kind: ar (عربي/لاتيني) | display (أرقام وعناوين لاتينية عريضة) | jp (كتابة يابانية)."""
    path = {"ar": find_font(), "display": _first(_DISPLAY) or find_font(), "jp": _first(_JP)}[kind]
    if not path:
        raise RuntimeError(f"no usable font for {kind}; set FONT_PATH")
    return ImageFont.truetype(path, int(size * S), layout_engine=_engine() if kind == "ar" else ImageFont.Layout.BASIC)


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Canvas:
    def __init__(self, w: int, h: int, seed: str = "otaku"):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 255))
        self.d = ImageDraw.Draw(self.img)
        self.rng = random.Random(seed)

    # ── أدوات عامة ─────────────────────────────────────
    def P(self, pts):
        return [(x * S, y * S) for x, y in pts]

    def B(self, box):
        x0, y0, x1, y1 = box
        return (x0 * S, y0 * S, x1 * S, y1 * S)

    def gradient(self, top, bottom, vignette: float = 0.35):
        size = (self.w * S, self.h * S)
        mask = Image.linear_gradient("L").resize(size)
        base = Image.composite(Image.new("RGB", size, bottom), Image.new("RGB", size, top), mask)
        if vignette:
            vg = ImageChops.invert(Image.radial_gradient("L").resize(size)).point(lambda v: int(v * vignette))
            base = Image.composite(Image.new("RGB", size, (0, 0, 0)), base, vg)
        self.img.paste(base.convert("RGBA"))
        self.d = ImageDraw.Draw(self.img)

    def overlay(self, fn):
        """يرسم على طبقة شفافة كاملة (للشفافية) ثم يلصقها."""
        layer = Image.new("RGBA", (self.w * S, self.h * S), (0, 0, 0, 0))
        fn(ImageDraw.Draw(layer))
        self.img.alpha_composite(layer)
        self.d = ImageDraw.Draw(self.img)

    def wobble(self, pts, amp: float = 1.2):
        return [(x + self.rng.uniform(-amp, amp), y + self.rng.uniform(-amp, amp)) for x, y in pts]

    def hand_rect(self, box, fill=None, outline=BLACK, width=3, amp=1.4, radius=0):
        """مستطيل بحواف «مرسومة باليد» (اهتزاز خفيف)."""
        x0, y0, x1, y1 = box
        pts = []
        steps = 8
        for i in range(steps + 1):
            t = i / steps
            pts.append((x0 + (x1 - x0) * t, y0))
        for i in range(1, steps + 1):
            pts.append((x1, y0 + (y1 - y0) * i / steps))
        for i in range(1, steps + 1):
            pts.append((x1 - (x1 - x0) * i / steps, y1))
        for i in range(1, steps):
            pts.append((x0, y1 - (y1 - y0) * i / steps))
        pts = self.wobble(pts, amp)
        if fill:
            self.d.polygon(self.P(pts), fill=fill)
        if outline:
            self.d.line(self.P(pts + [pts[0]]), fill=outline, width=int(width * S), joint="curve")

    # ── زخارف المانغا ──────────────────────────────────
    def halftone(self, region, color, spacing=9, max_r=3.2, toward=(0, 1), alpha=70):
        """نقاط screentone تكبر باتجاه زاوية معيّنة."""
        x0, y0, x1, y1 = region

        def fn(d):
            y = y0
            row = 0
            while y < y1:
                x = x0 + (spacing / 2 if row % 2 else 0)
                while x < x1:
                    fx = (x - x0) / max(1, x1 - x0) if toward[0] >= 0 else 1 - (x - x0) / max(1, x1 - x0)
                    fy = (y - y0) / max(1, y1 - y0) if toward[1] >= 0 else 1 - (y - y0) / max(1, y1 - y0)
                    r = max_r * (fx * 0.5 + fy * 0.5) ** 1.4
                    if r > 0.35:
                        d.ellipse(self.B((x - r, y - r, x + r, y + r)), fill=(*color, alpha))
                    x += spacing
                y += spacing * 0.866
                row += 1
        self.overlay(fn)

    def speed_lines(self, center, r_in, r_out, n=70, color=(255, 255, 255), alpha=55, width=(0.4, 2.2)):
        cx, cy = center

        def fn(d):
            for _ in range(n):
                a = self.rng.uniform(0, math.tau)
                spread = math.radians(self.rng.uniform(*width)) * 0.5
                ri = r_in * self.rng.uniform(0.9, 1.4)
                ro = r_out * self.rng.uniform(0.75, 1.15)
                d.polygon(self.P([(cx + ri * math.cos(a), cy + ri * math.sin(a)),
                                  (cx + ro * math.cos(a - spread), cy + ro * math.sin(a - spread)),
                                  (cx + ro * math.cos(a + spread), cy + ro * math.sin(a + spread))]), fill=(*color, alpha))
        self.overlay(fn)

    def starburst(self, center, r_out, r_in, spikes=14, fill=PAPER, outline=BLACK, width=4, shadow=True):
        """بالونة صراخ مسنّنة كما في المانغا."""
        cx, cy = center
        pts = []
        for i in range(spikes * 2):
            a = math.pi * i / spikes + self.rng.uniform(-0.04, 0.04)
            r = (r_out if i % 2 == 0 else r_in) * self.rng.uniform(0.94, 1.06)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a) * 0.82))
        if shadow:
            self.d.polygon(self.P([(x + 6, y + 7) for x, y in pts]), fill=(0, 0, 0, 90))
        self.d.polygon(self.P(pts), fill=fill)
        self.d.line(self.P(pts + [pts[0]]), fill=outline, width=int(width * S), joint="curve")

    def sparkle(self, x, y, r, fill=(255, 235, 140), outline=BLACK, width=2):
        pts = [(x, y - r), (x + r * 0.22, y - r * 0.22), (x + r, y), (x + r * 0.22, y + r * 0.22),
               (x, y + r), (x - r * 0.22, y + r * 0.22), (x - r, y), (x - r * 0.22, y - r * 0.22)]
        self.d.polygon(self.P(pts), fill=fill)
        if outline:
            self.d.line(self.P(pts + [pts[0]]), fill=outline, width=int(width * S))

    def petal_flower(self, x, y, r, angle=0.0, color=(255, 183, 213), alpha=235):
        """زهرة ساكورا خماسية البتلات (خفيفة، للتزيين)."""
        def fn(d):
            for k in range(5):
                a = angle + k * math.tau / 5
                px, py = x + r * 0.55 * math.cos(a), y + r * 0.55 * math.sin(a)
                d.ellipse(self.B((px - r * 0.5, py - r * 0.5, px + r * 0.5, py + r * 0.5)), fill=(*color, alpha))
            d.ellipse(self.B((x - r * 0.18, y - r * 0.18, x + r * 0.18, y + r * 0.18)), fill=(255, 120, 160, 255))
        self.overlay(fn)

    def sakura(self, n, area, size=(9, 16), color=(255, 183, 213)):
        """بتلات ساكورا متناثرة؛ طبقة واحدة لكل الزهور (أسرع بكثير من طبقة لكل زهرة)."""
        x0, y0, x1, y1 = area
        flowers = [(self.rng.uniform(x0, x1), self.rng.uniform(y0, y1), self.rng.uniform(*size), self.rng.uniform(0, math.tau))
                   for _ in range(n)]

        def fn(d):
            for x, y, r, angle in flowers:
                for k in range(5):
                    a = angle + k * math.tau / 5
                    px, py = x + r * 0.55 * math.cos(a), y + r * 0.55 * math.sin(a)
                    d.ellipse(self.B((px - r * 0.5, py - r * 0.5, px + r * 0.5, py + r * 0.5)), fill=(*color, 235))
                d.ellipse(self.B((x - r * 0.18, y - r * 0.18, x + r * 0.18, y + r * 0.18)), fill=(255, 120, 160, 255))
        self.overlay(fn)

    def grain(self, amount=0.06):
        """حبيبات ورق خفيفة تكسر النعومة الرقمية."""
        rgb = self.img.convert("RGB")
        noise = Image.effect_noise(rgb.size, 48).convert("RGB")
        self.img = Image.blend(rgb, noise, amount).convert("RGBA")
        self.d = ImageDraw.Draw(self.img)

    # ── نصوص ───────────────────────────────────────────
    def text(self, xy, s, kind="ar", size=30, fill=(255, 255, 255), stroke=0, stroke_fill=BLACK,
             anchor="mm", rotate=0.0, shadow=0, arabic=True):
        f = font(kind, size)
        txt = shape(s) if (arabic and kind == "ar") else s
        x, y = xy
        if rotate:
            bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), txt, font=f, stroke_width=int(stroke * S))
            tw, th = bbox[2] - bbox[0] + 24 * S, bbox[3] - bbox[1] + 24 * S
            layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            if shadow:
                ld.text((tw / 2 + shadow * S, th / 2 + shadow * S), txt, font=f, fill=(0, 0, 0, 110), anchor="mm",
                        stroke_width=int(stroke * S), stroke_fill=(0, 0, 0, 110))
            ld.text((tw / 2, th / 2), txt, font=f, fill=fill, anchor="mm", stroke_width=int(stroke * S), stroke_fill=stroke_fill)
            layer = layer.rotate(rotate, resample=Image.BICUBIC, expand=True)
            self.img.alpha_composite(layer, (int(x * S - layer.width / 2), int(y * S - layer.height / 2)))
            self.d = ImageDraw.Draw(self.img)
            return
        if shadow:
            self.d.text((x * S + shadow * S, y * S + shadow * S), txt, font=f, fill=(0, 0, 0, 110), anchor=anchor,
                        stroke_width=int(stroke * S), stroke_fill=(0, 0, 0, 110))
        self.d.text((x * S, y * S), txt, font=f, fill=fill, anchor=anchor, stroke_width=int(stroke * S), stroke_fill=stroke_fill)

    def text_width(self, s, kind="ar", size=30, stroke=0):
        f = font(kind, size)
        return ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(shape(s) if kind == "ar" else s, font=f) / S

    def fit(self, s, kind, size, max_w):
        """يصغّر الخط حتى يتسع النص."""
        while size > 12 and self.text_width(s, kind, size) > max_w:
            size -= 2
        return size

    # ── ختم هانكو ─────────────────────────────────────
    def hanko(self, center, r, main, sub=None, angle=-12, color=(205, 38, 52)):
        cx, cy = center
        size = int(r * 2 + 16)

        def fn(d):
            m = size / 2
            wob = lambda k: k + self.rng.uniform(-0.8, 0.8)    # noqa: E731
            d.ellipse(self.B((m - wob(r), m - wob(r), m + wob(r), m + wob(r))), outline=(*color, 235), width=int(5 * S))
            d.ellipse(self.B((m - r + 8, m - r + 8, m + r - 8, m + r - 8)), outline=(*color, 235), width=int(2 * S))
        layer_img = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
        fn(ImageDraw.Draw(layer_img))
        ld = ImageDraw.Draw(layer_img)
        f = font("display", r * 1.05 if len(main) <= 2 else r * 0.8)
        ld.text((size * S / 2, size * S / 2 - (4 * S if sub else 0)), main, font=f, fill=(*color, 240), anchor="mm")
        if sub:
            ld.text((size * S / 2, size * S / 2 + r * 0.62 * S), shape(sub) if any("\u0600" <= ch <= "\u06ff" for ch in sub) else sub,
                    font=font("ar", max(11, r * 0.26)), fill=(*color, 240), anchor="mm")
        # بقع حبر خشنة (الختم الحقيقي لا يطبع بشكل مثالي)
        specks = Image.effect_noise(layer_img.size, 70).point(lambda v: 0 if v < 62 else 255)
        alpha = ImageChops.multiply(layer_img.getchannel("A"), specks)
        layer_img.putalpha(alpha)
        layer_img = layer_img.rotate(angle, resample=Image.BICUBIC, expand=True)
        self.img.alpha_composite(layer_img, (int(cx * S - layer_img.width / 2), int(cy * S - layer_img.height / 2)))
        self.d = ImageDraw.Draw(self.img)

    # ── شريط لاصق (washi tape) ─────────────────────────
    def tape(self, center, w=70, h=22, angle=-8, color=(255, 214, 102)):
        cx, cy = center
        layer = Image.new("RGBA", (int((w + 8) * S), int((h + 8) * S)), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rectangle((4 * S, 4 * S, (w + 4) * S, (h + 4) * S), fill=(*color, 215))
        for i in range(-int(h), int(w), 10):                      # خطوط مائلة خفيفة على الشريط
            ld.line(((4 + i) * S, (h + 4) * S, (4 + i + h) * S, 4 * S), fill=(255, 255, 255, 80), width=int(2 * S))
        layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
        self.img.alpha_composite(layer, (int(cx * S - layer.width / 2), int(cy * S - layer.height / 2)))
        self.d = ImageDraw.Draw(self.img)

    # ── إخراج ──────────────────────────────────────────
    def jpeg(self, grain=0.05, quality=88) -> bytes:
        """JPEG عالي الجودة (~100KB) بدل PNG: أسرع كثيرًا في الرفع على الاستضافات الضعيفة."""
        if grain:
            self.grain(grain)
        out = self.img.convert("RGB").resize((self.w, self.h), Image.LANCZOS)
        buf = io.BytesIO()
        out.save(buf, format="JPEG", quality=quality, optimize=True, subsampling=0)
        return buf.getvalue()
