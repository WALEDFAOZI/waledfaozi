"""سلامة المحتوى بعد المضاعفة: عدد، بنية، عدم تكرار، وأمان قائمة الأنمي."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from merge_new import check_question, norm  # noqa: E402


def test_questions_doubled_valid_and_unique():
    qs = json.loads((ROOT / "data" / "questions.json").read_text(encoding="utf-8"))
    assert len(qs) >= 1300
    assert len({q["id"] for q in qs}) == len(qs)
    assert len({norm(q["q"]) for q in qs}) == len(qs) and len({norm(q["q_en"]) for q in qs}) == len(qs)
    for q in qs:
        if q["id"] > 670:
            assert check_question(q) is None, (q["id"], check_question(q))
        assert len(q["options"]) == 4 and 0 <= q["answer"] < 4 and q["q_en"] and len(q["options_en"]) == 4
    levels = {}
    for q in qs:
        levels[round(q["base_difficulty"])] = levels.get(round(q["base_difficulty"]), 0) + 1
    assert all(levels.get(i, 0) >= 80 for i in range(1, 11)), levels      # كل مستوى فيه مخزون كبير


def test_games_and_anime_lists_grew_and_stay_safe():
    g = json.loads((ROOT / "data" / "games.json").read_text(encoding="utf-8"))
    assert len(g["tf"]) >= 85 and len(g["songs"]) >= 60 and len(g["anime"]) >= 55 and len(g["chars"]) >= 50 and len(g["quotes"]) >= 40
    years = [y for _, y in g["anime"]]
    assert len(g["anime"]) == len({n.lower() for n, _ in g["anime"]}) and all(1950 <= y <= 2026 for y in years)
    anime = json.loads((ROOT / "data" / "anime.json").read_text(encoding="utf-8"))
    assert len(anime) >= 115 and len({a["key"] for a in anime}) == len(anime)
    banned = ("steins", "champloo", "dororo", "yu yu hakusho", "konosuba", "berserk", "chainsaw", "evangelion", "tokyo ghoul",
              "naruto", "one piece", "bleach", "dragon ball", "fairy tail", "sword art")
    assert not [x["en"] for x in anime if any(b in x["en"].lower() for b in banned)]
    for x in anime:
        assert not any(w in (x["en"] + x["syn_en"]).lower() for w in ("ecchi", "hentai", "harem", "erotic"))
