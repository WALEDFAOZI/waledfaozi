"""منطق الاختبار الصافي (بدون تليجرام ولا قاعدة بيانات) — سهل الاختبار."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .config import CALIBRATION_WEIGHT, LEVELS, PER_LEVEL, TITLES, TITLES_EN


@dataclass
class Question:
    id: int
    q: str
    options: list[str]
    answer: int
    category: str
    base_difficulty: float
    asked: int = 0
    correct: int = 0
    image: str | None = None          # رابط أو "tg:<file_id>"
    q_en: str | None = None
    options_en: list[str] | None = None
    active: bool = True

    def text(self, lang: str = "ar") -> str:
        from .names import loc
        return self.q_en if lang == "en" and self.q_en else loc(self.q, "ar")

    def opts(self, lang: str = "ar") -> list[str]:
        from .names import loc_opt
        return self.options_en if lang == "en" and self.options_en else [loc_opt(o, "ar") for o in self.options]

    @property
    def difficulty(self) -> float:
        return effective_difficulty(self.base_difficulty, self.asked, self.correct)

    @property
    def level(self) -> int:
        return level_of(self.difficulty)


def effective_difficulty(base: float, asked: int, correct: int,
                         weight: float = CALIBRATION_WEIGHT) -> float:
    """يمزج تقديرك الأولي مع الصعوبة الحقيقية المحسوبة من إجابات اللاعبين.

    تجريبية = (1 - نسبة الصحيح) × 10، وكلما زادت الإجابات زاد وزنها.
    """
    if asked <= 0:
        return float(base)
    empirical = (1 - correct / asked) * 10
    empirical = min(10.0, max(1.0, empirical))
    return (weight * base + asked * empirical) / (weight + asked)


def level_of(difficulty: float) -> int:
    return max(1, min(LEVELS, int(round(difficulty))))


def shuffle_options(q: Question, rng: random.Random) -> tuple[list[int], int]:
    """يرجع (ترتيب الخيارات كفهارس أصلية, موضع الجواب الصحيح في الترتيب الجديد)."""
    order = list(range(len(q.options)))
    rng.shuffle(order)
    return order, order.index(q.answer)


def _spread_categories(qs: list[Question]) -> list[Question]:
    """يمنع تتالي نفس التصنيف قدر الإمكان داخل المستوى الواحد."""
    result: list[Question] = []
    pool = qs[:]
    while pool:
        pick = next((x for x in pool if not result or x.category != result[-1].category), pool[0])
        pool.remove(pick)
        result.append(pick)
    return result


def pick_questions(
    questions: list[Question],
    seen: dict[int, float],
    rng: random.Random | None = None,
    per_level: int = PER_LEVEL,
    levels: int = LEVELS,
) -> list[Question]:
    """يختار per_level سؤالًا من كل مستوى مرتبة من الأسهل للأصعب.

    seen: {question_id: وقت آخر مشاهدة} — الأسئلة غير المشاهدة لها أولوية،
    وعند النفاد نبدأ بالأقدم مشاهدة، وعند نفاد المستوى نستعير من المستويات المجاورة.
    """
    rng = rng or random.Random()
    by_level: dict[int, list[Question]] = {lv: [] for lv in range(1, levels + 1)}
    for q in questions:
        by_level[min(levels, max(1, q.level))].append(q)

    chosen: list[Question] = []
    used: set[int] = set()

    def diversify(cands: list[Question], n: int, cap: int = 2) -> list[Question]:
        """يفضّل ألا يزيد نفس التصنيف عن cap داخل المستوى الواحد (تنويع)."""
        out: list[Question] = []
        counts: dict[str, int] = {}
        for c in cands:
            if len(out) >= n:
                break
            if counts.get(c.category, 0) < cap:
                out.append(c)
                counts[c.category] = counts.get(c.category, 0) + 1
        for c in cands:
            if len(out) >= n:
                break
            if c not in out:
                out.append(c)
        return out

    def take(candidates: list[Question], n: int) -> list[Question]:
        fresh = [c for c in candidates if c.id not in seen and c.id not in used]
        rng.shuffle(fresh)
        got = diversify(fresh, n)
        if len(got) < n:
            stale = [c for c in candidates if c.id in seen and c.id not in used]
            rng.shuffle(stale)
            stale.sort(key=lambda c: seen[c.id])  # الأقدم مشاهدة أولًا
            got += stale[: n - len(got)]
        return got

    for lv in range(1, levels + 1):
        got = take(by_level[lv], per_level)
        # استعارة من المستويات الأقرب إن لم يكفِ المستوى
        dist = 1
        while len(got) < per_level and dist < levels:
            for nb in (lv - dist, lv + dist):
                if 1 <= nb <= levels and len(got) < per_level:
                    extra = take([c for c in by_level[nb] if c.id not in {g.id for g in got}],
                                 per_level - len(got))
                    got += extra
                    used.update(e.id for e in extra)
            dist += 1
        used.update(g.id for g in got)
        chosen.extend(_spread_categories(got))
    return chosen


@dataclass
class Answer:
    level: int          # وزن السؤال = مستواه عند السحب (1..10)
    category: str
    correct: bool


def compute_score(answers: list[Answer]) -> float:
    """التقييم من 10 = 10 × مجموع أوزان الصحيح / مجموع كل الأوزان."""
    total = sum(a.level for a in answers)
    if total == 0:
        return 0.0
    got = sum(a.level for a in answers if a.correct)
    return round(10 * got / total, 2)


def pick_category(questions: list[Question], seen: dict[int, float], category: str,
                  rng: random.Random | None = None, n: int = 10) -> list[Question]:
    """n سؤالًا من تصنيف واحد موزعة على مستويات 1..n ومرتبة من الأسهل للأصعب."""
    rng = rng or random.Random()
    pool = [q for q in questions if q.category == category]
    if len(pool) < n:
        return []
    result: list[Question] = []
    used: set[int] = set()
    for target in range(1, n + 1):
        cands = [q for q in pool if q.id not in used]
        cands.sort(key=lambda q: (abs(q.level - target) + (3 if q.id in seen else 0), rng.random()))
        used.add(cands[0].id)
        result.append(cands[0])
    result.sort(key=lambda q: q.level)
    return result


def title_for(score: float, lang: str = "ar") -> str:
    table = TITLES_EN if lang == "en" else TITLES
    title = table[0][1]
    for threshold, name in table:
        if score >= threshold:
            title = name
    return title


def category_breakdown(answers: list[Answer]) -> dict[str, tuple[int, int]]:
    """{التصنيف: (صحيح, الإجمالي)}"""
    out: dict[str, list[int]] = {}
    for a in answers:
        row = out.setdefault(a.category, [0, 0])
        row[1] += 1
        row[0] += int(a.correct)
    return {k: (v[0], v[1]) for k, v in out.items()}


def progress_bar(done: int, total: int, width: int = 10) -> str:
    filled = round(width * done / total) if total else 0
    return "▓" * filled + "░" * (width - filled)
