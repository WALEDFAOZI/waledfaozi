import json
import random
from pathlib import Path

from otaku_bot.config import LEVELS, PER_LEVEL
from otaku_bot.db import DB
from otaku_bot.quiz import (Answer, Question, category_breakdown, compute_score,
                            effective_difficulty, level_of, pick_questions, shuffle_options,
                            title_for)

QPATH = Path(__file__).resolve().parent.parent / "data" / "questions.json"


def load():
    db = DB(":memory:")
    db.load_questions(str(QPATH))
    return db


def test_bank_integrity():
    data = json.loads(QPATH.read_text(encoding="utf-8"))
    ids = [d["id"] for d in data]
    assert len(ids) == len(set(ids))
    assert len({d["q"] for d in data}) == len(data)
    for d in data:
        assert len(d["options"]) == 4 and len(set(d["options"])) == 4
        assert 0 <= d["answer"] < 4
        assert 1 <= d["base_difficulty"] <= 10
    for lv in range(1, LEVELS + 1):
        assert sum(1 for d in data if d["base_difficulty"] == lv) >= PER_LEVEL


def test_difficulty_calibration():
    assert effective_difficulty(5, 0, 0) == 5
    # الجميع يجيبه صح -> يصير أسهل
    assert effective_difficulty(8, 500, 500) < 2
    # لا أحد يجيبه صح -> يصير أصعب
    assert effective_difficulty(2, 500, 0) > 9
    # قلة العينات: رأيك يتحكم
    assert abs(effective_difficulty(5, 2, 0) - 5) < 1
    assert level_of(0.2) == 1 and level_of(11) == 10


def test_pick_gives_50_sorted_easy_to_hard():
    db = load()
    picked = pick_questions(db.all_questions(), {}, random.Random(1))
    assert len(picked) == LEVELS * PER_LEVEL
    assert len({q.id for q in picked}) == len(picked)
    levels = [q.level for q in picked]
    assert levels == sorted(levels)
    assert all(levels.count(lv) == PER_LEVEL for lv in range(1, LEVELS + 1))


def test_no_repeats_until_exhausted_and_oldest_first():
    db = load()
    qs = db.all_questions()
    seen: dict[int, float] = {}
    first = pick_questions(qs, seen, random.Random(1))
    seen.update({q.id: 100.0 for q in first})
    second = pick_questions(qs, seen, random.Random(2))
    # كل مستوى فيه 10+ أسئلة فلا يجب أن يتكرر شيء في المستويات الكبيرة
    big = {lv for lv in range(1, 11) if sum(1 for q in qs if q.level == lv) >= 2 * PER_LEVEL}
    for q in second:
        if q.level in big:
            assert q.id not in {x.id for x in first}
    assert len(second) == 50


def test_pick_when_all_seen_still_returns_50():
    db = load()
    qs = db.all_questions()
    seen = {q.id: float(i) for i, q in enumerate(qs)}
    assert len(pick_questions(qs, seen, random.Random(3))) == 50


def test_borrow_from_neighbour_level():
    qs = [Question(i, f"q{i}", ["a", "b", "c", "d"], 0, "anime", 1 + (i % 2)) for i in range(60)]
    out = pick_questions(qs, {}, random.Random(0), per_level=5, levels=10)
    assert len(out) == 50 and len({q.id for q in out}) == 50


def test_shuffle_keeps_correct_answer():
    q = Question(1, "x", ["a", "b", "c", "d"], 2, "anime", 1)
    for s in range(20):
        order, cpos = shuffle_options(q, random.Random(s))
        assert q.options[order[cpos]] == "c"


def test_score_weighting_and_titles():
    all_right = [Answer(lv, "anime", True) for lv in range(1, 11)]
    assert compute_score(all_right) == 10
    assert compute_score([Answer(lv, "anime", False) for lv in range(1, 11)]) == 0
    only_easy = [Answer(lv, "anime", lv <= 3) for lv in range(1, 11)]
    only_hard = [Answer(lv, "anime", lv >= 8) for lv in range(1, 11)]
    assert compute_score(only_hard) > compute_score(only_easy)
    assert "ملك الأوتاكو" in title_for(10)
    assert "ملك الأوتاكو" in title_for(9.5)
    assert "سينسي" in title_for(9.49)
    assert "نوب" in title_for(0)
    assert category_breakdown([Answer(1, "a", True), Answer(2, "a", False)]) == {"a": (1, 2)}


def test_db_session_flow_and_stats_update():
    db = load()
    db.upsert_user(1, "tester")
    picked = []
    rng = random.Random(5)
    for q in pick_questions(db.all_questions(), db.seen_map(1), rng):
        order, cpos = shuffle_options(q, rng)
        picked.append((q, order, cpos))
    sid = db.create_session(1, picked)
    assert db.session_len(sid) == 50
    assert db.record_answer(sid, 0, picked[0][2]) is True          # صحيح
    assert db.record_answer(sid, 0, picked[0][2]) is None           # لا تُسجَّل مرتين
    wrong = (picked[1][2] + 1) % 4
    assert db.record_answer(sid, 1, wrong) is False
    assert db.record_answer(sid, 2, 0, timed_out=True) is False
    q0 = db.get_question(picked[0][0].id)
    assert (q0.asked, q0.correct) == (1, 1)
    assert len(db.seen_map(1)) == 50
    for pos in range(3, 50):
        db.record_answer(sid, pos, picked[pos][2])
    score = compute_score(db.session_answers(sid))
    db.finish_session(sid, 1, score)
    u = db.get_user(1)
    assert u["tests_taken"] == 1 and u["best_score"] == score
    assert db.active_session(1) is None
    assert db.user_rank(1) == 1
    assert db.leaderboard()[0]["name"] == "tester"


def test_suspicious_result_does_not_raise_best():
    db = load()
    db.upsert_user(2, "cheater")
    sid = db.create_session(2, [(q, [0, 1, 2, 3], q.answer) for q in db.all_questions()[:50]])
    db.finish_session(sid, 2, 10.0, mode="full", counted=False)
    assert db.get_user(2)["best_score"] == 0


def test_card_renders_jpeg():
    import pytest
    from otaku_bot import card
    if not card.find_font():
        pytest.skip("no font")
    png = card.make_card("اختبار", 9.7, "ملك الأوتاكو 👑", 99, {"anime": (4, 5)})
    assert png[:2] == b"\xff\xd8"
