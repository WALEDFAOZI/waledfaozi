"""بطاقة نتيجة الألعاب الثنائية: اللوحة النهائية واسم الفائز، كصورة قابلة للمشاركة.

تُرسم بـ Pillow (نفس أسلوب باقي البطاقات). إن فشل الرسم لأي سبب ترجع None، ولا تتأثر اللعبة.
"""
from __future__ import annotations

from .art import BLACK, PAPER, S, Canvas, find_font
from .card import strip_emoji

W, H = 900, 520
RED = (226, 58, 70)
YELLOW = (255, 200, 60)
EMPTY = (235, 228, 240)
X_COLOR = (40, 40, 60)
O_COLOR = (230, 70, 110)


def _xo(c: Canvas, board: list) -> None:
    x0, y0, cell = 330, 96, 92
    for i in range(1, 3):
        c.d.line([((x0 + cell * i) * S, y0 * S), ((x0 + cell * i) * S, (y0 + 3 * cell) * S)], fill=BLACK, width=6 * S)
        c.d.line([(x0 * S, (y0 + cell * i) * S), ((x0 + 3 * cell) * S, (y0 + cell * i) * S)], fill=BLACK, width=6 * S)
    for i, v in enumerate(board):
        cx = x0 + (i % 3) * cell + cell / 2
        cy = y0 + (i // 3) * cell + cell / 2
        r = cell * 0.32
        if v == "X":
            c.d.line([((cx - r) * S, (cy - r) * S), ((cx + r) * S, (cy + r) * S)], fill=X_COLOR, width=12 * S)
            c.d.line([((cx + r) * S, (cy - r) * S), ((cx - r) * S, (cy + r) * S)], fill=X_COLOR, width=12 * S)
        elif v == "O":
            c.d.ellipse([((cx - r) * S, (cy - r) * S), ((cx + r) * S, (cy + r) * S)], outline=O_COLOR, width=12 * S)


def _c4(c: Canvas, grid: list) -> None:
    cell = 58
    x0, y0 = (W - 7 * cell) / 2, 84
    for r in range(6):
        for col in range(7):
            v = grid[r][col]
            cx = x0 + col * cell + cell / 2
            cy = y0 + (5 - r) * cell + cell / 2
            color = RED if v == "R" else YELLOW if v == "Y" else EMPTY
            rad = cell * 0.4
            c.d.ellipse([((cx - rad) * S, (cy - rad) * S), ((cx + rad) * S, (cy + rad) * S)], fill=color,
                        outline=BLACK, width=3 * S)


def make_match_card(kind: str, board, names: list[str], title: str, result: str, scores: str | None = None,
                    handle: str = "@Otaku1GalaxyBot") -> bytes | None:
    """بطاقة نتيجة مباراة. names = [اللاعب الأول، الثاني]. يرجع JPEG أو None عند الفشل."""
    try:
        if not find_font():
            return None
        c = Canvas(W, H, "result-" + kind)
        c.gradient((30, 14, 60), (255, 70, 120))
        c.text((W / 2, 42), strip_emoji(title), "ar", 46, fill=PAPER, stroke=5, stroke_fill=BLACK)
        if kind == "xo":
            _xo(c, board)
        elif kind == "c4":
            _c4(c, board)
        else:                                               # حجرة ورقة مقص: نتيجة نصية والنقاط
            c.text((W / 2, 230), scores or "", "ar", 90, fill=PAPER, stroke=6, stroke_fill=BLACK)
        left, right = (names + ["", ""])[:2]
        c.text((120 if kind == "c4" else 160, 250 if kind != "rps" else 330), strip_emoji(left)[:18], "ar", 34, fill=PAPER, stroke=4, stroke_fill=BLACK)
        c.text((W - (120 if kind == "c4" else 160), 250 if kind != "rps" else 330), strip_emoji(right)[:18], "ar", 34, fill=PAPER, stroke=4, stroke_fill=BLACK)
        c.text((W / 2, H - 66), strip_emoji(result), "ar", 50, fill=(255, 235, 140), stroke=6, stroke_fill=BLACK)
        c.text((W / 2, H - 22), handle, "display", 24, fill=PAPER, stroke=3, stroke_fill=BLACK, arabic=False)
        return c.jpeg(grain=0.03, quality=90)
    except Exception:  # noqa: BLE001 - البطاقة ميزة إضافية؛ لا تكسر اللعبة
        return None
