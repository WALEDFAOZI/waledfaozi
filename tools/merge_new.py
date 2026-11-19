"""يدمج المحتوى الجديد (tools/new_content/*.json) في data/ بعد تحقق صارم وإزالة التكرار. آمن لإعادة التشغيل (idempotent).

    python tools/merge_new.py --dry     # تقرير فقط
    python tools/merge_new.py           # دمج فعلي
ملفات الإدخال: q_*.json (أسئلة)، games_new.json (ألعاب)، anime_new.json (قائمة الأنمي المقترحة).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from build_anime import GENRES, RATINGS  # noqa: E402
from names_data import NAMES, OPTION_ONLY  # noqa: E402

CATS = {"anime", "characters", "studios", "creators", "music", "culture", "history", "manga"}
BANNED = ("ecchi", "hentai", "harem", "porn", "nude", "sexual", "erotic", "إيتشي", "هنتاي", "حريم", "إباحي", "عاري", "جنسي", "إيحاء")
# أعمال مستبعدة من قائمة الاقتراح (معيار الأمان: لا عنف شديد/محتوى للكبار/إيحاءات)
EXCLUDE_TITLES = {norm_t for norm_t in (
    "steins gate", "samurai champloo", "dororo", "yu yu hakusho", "konosuba", "no game no life", "sword art online", "fairy tail",
    "food wars", "chainsaw man", "berserk", "tokyo ghoul", "neon genesis evangelion", "evangelion", "made in abyss", "oshi no ko",
    "gintama", "assassination classroom", "ouran high school host club", "sailor moon", "naruto", "one piece", "bleach", "dragon ball",
    "high school dxd", "highschool of the dead", "prison school", "date a live", "rosario vampire", "to love ru", "shimoneta",
    "elfen lied", "gantz", "devilman crybaby", "akame ga kill", "hellsing", "black lagoon", "claymore", "school days")}
LAT, ARB = re.compile(r"[A-Za-z]"), re.compile(r"[؀-ۿ]")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w؀-ۿ ]+", " ", (s or "").lower())).strip()


_BAD_RE = re.compile(r"(?<![A-Za-z\u0600-\u06FF])(?:" + "|".join(re.escape(b) for b in BANNED) + r")(?![A-Za-z\u0600-\u06FF])", re.I)


def bad_words(*texts) -> bool:
    """كلمة كاملة فقط (حتى لا تُرفض أسماء يابانية مثل «إيتشيمارو» بسبب «إيتشي»)."""
    return bool(_BAD_RE.search(" ".join(map(str, texts))))


def check_question(d: dict) -> str | None:
    need = {"q", "options", "answer", "category", "base_difficulty", "q_en", "options_en"}
    if not need <= d.keys():
        return "حقول ناقصة"
    if d["category"] not in CATS:
        return "تصنيف غير صالح"
    if not isinstance(d["options"], list) or len(d["options"]) != 4 or len(d["options_en"]) != 4:
        return "لازم 4 خيارات"
    if not isinstance(d["answer"], int) or not 0 <= d["answer"] < 4:
        return "answer"
    if not isinstance(d["base_difficulty"], (int, float)) or not 1 <= d["base_difficulty"] <= 10:
        return "الصعوبة"
    if len({norm(o) for o in d["options"]}) != 4 or len({norm(o) for o in d["options_en"]}) != 4:
        return "خيارات مكررة"
    if len(d["q"]) > 180 or len(d["q_en"]) > 200 or any(len(o) > 55 for o in d["options"] + d["options_en"]):
        return "طول"
    if not ARB.search(d["q"]) or not d["q"].strip().endswith(("؟", "?", ".", "…")) and len(d["q"]) < 8:
        return "صياغة"
    if bad_words(d["q"], d["q_en"], *d["options"], *d["options_en"]):
        return "كلمات غير مناسبة"
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--dir", default=str(ROOT / "tools" / "new_content"))
    a = ap.parse_args()
    src = Path(a.dir)
    report: list[str] = []

    # ── الأسئلة ──
    qpath = ROOT / "data" / "questions.json"
    qs = json.loads(qpath.read_text(encoding="utf-8"))
    ex = src / "exclude.json"
    excluded = {norm(x) for x in json.loads(ex.read_text(encoding="utf-8")).get("q_en", [])} if ex.exists() else set()
    seen = {norm(q["q"]) for q in qs} | {norm(q.get("q_en") or "") for q in qs} | excluded
    nid = max(q["id"] for q in qs) + 1
    added, rejected = 0, {}
    for f in sorted(src.glob("q_*.json")):
        for d in json.loads(f.read_text(encoding="utf-8")):
            err = check_question(d)
            if not err and (norm(d["q"]) in seen or norm(d["q_en"]) in seen):
                err = "مكرر"
            if err:
                rejected[err] = rejected.get(err, 0) + 1
                continue
            seen |= {norm(d["q"]), norm(d["q_en"])}
            qs.append({"id": nid, "q": d["q"], "options": d["options"], "answer": d["answer"], "category": d["category"],
                       "base_difficulty": d["base_difficulty"], "q_en": d["q_en"], "options_en": d["options_en"]})
            nid += 1
            added += 1
    report.append(f"أسئلة: +{added} (المجموع {len(qs)}) | مرفوض: {rejected}")
    if not a.dry:
        qpath.write_text(json.dumps(qs, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── الألعاب ──
    gpath = ROOT / "data" / "games.json"
    g = json.loads(gpath.read_text(encoding="utf-8"))
    gf = src / "games_new.json"
    if gf.exists():
        new = json.loads(gf.read_text(encoding="utf-8"))
        cnt = {}

        def add(kind, item, key):
            ks = {key(x) for x in g[kind]}
            if key(item) in ks or bad_words(*[str(x) for x in item]):
                return
            g[kind].append(item)
            cnt[kind] = cnt.get(kind, 0) + 1
        for it in new.get("tf", []):
            if len(it) == 5 and isinstance(it[2], bool) and (it[2] or (it[3] and it[4])):
                add("tf", it, lambda x: norm(x[0]))
        for it in new.get("songs", []):
            if len(it) == 2:
                add("songs", it, lambda x: (norm(x[0]), norm(x[1])))
        for it in new.get("anime", []):
            if len(it) == 2 and isinstance(it[1], int) and 1950 <= it[1] <= 2026:
                add("anime", it, lambda x: norm(x[0]))
        for it in new.get("chars", []):
            if len(it) == 3:
                add("chars", it, lambda x: norm(x[2]))
        for it in new.get("quotes", []):
            if len(it) == 3:
                add("quotes", it, lambda x: norm(x[0]))
        for it in new.get("quote_extra", []):
            if isinstance(it, str) and norm(it) not in {norm(x) for x in g["quote_extra"]}:
                g["quote_extra"].append(it)
                cnt["quote_extra"] = cnt.get("quote_extra", 0) + 1
        report.append(f"ألعاب: +{cnt} | المجاميع { {k: len(v) for k, v in g.items()} }")
        if not a.dry:
            gpath.write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── الأنمي ──
    apath = ROOT / "data" / "anime.json"
    anime = json.loads(apath.read_text(encoding="utf-8"))
    af = src / "anime_new.json"
    if af.exists():
        keys = {x["key"] for x in anime}
        titles = {norm(x["en"]) for x in anime}
        ok, bad = 0, {}
        for d in json.loads(af.read_text(encoding="utf-8")):
            err = None
            try:
                if d["key"] in keys or norm(d["en"]) in titles:
                    err = "مكرر"
                elif norm(d["en"]) in EXCLUDE_TITLES or any(t_ in norm(d["en"]).split() for t_ in ()):
                    err = "مستبعد (معيار الأمان)"
                elif not set(d["genres"]) <= GENRES or d["rating"] not in RATINGS:
                    err = "نوع/تصنيف"
                elif not (d["syn_ar"] and d["syn_en"] and d["studio"] and d["ar"]):
                    err = "حقول ناقصة"
                elif d["rating"] == "mature" and not (d.get("note_ar") and d.get("note_en")):
                    err = "ملاحظة محتوى"
                elif d["kind"] == "film" and not d.get("minutes"):
                    err = "مدة الفيلم"
                elif d["kind"] == "series" and not (d.get("episodes") or d.get("eps_ar")):
                    err = "الحلقات"
                elif bad_words(d["en"], d["ar"], d["syn_ar"], d["syn_en"], *d["genres"]):
                    err = "كلمات غير مناسبة"
                elif d["len"] not in ("film", "short", "medium", "long"):
                    err = "len"
            except (KeyError, TypeError):
                err = "بنية"
            if err:
                bad[err] = bad.get(err, 0) + 1
                continue
            anime.append({k: d.get(k) for k in ("key", "ar", "en", "kind", "year", "studio", "genres", "rating", "seasons",
                                                "episodes", "minutes", "ongoing", "eps_ar", "eps_en", "note_ar", "note_en",
                                                "syn_ar", "syn_en", "len")})
            keys.add(d["key"]); titles.add(norm(d["en"]))
            ok += 1
        report.append(f"أنمي: +{ok} (المجموع {len(anime)}) | مرفوض: {bad}")
        if not a.dry:
            apath.write_text(json.dumps(anime, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── تغطية أسماء الأنمي/الشخصيات بالعربي ──
    miss = set()
    for q in qs:
        for o in q["options"]:
            if LAT.search(o) and not ARB.search(o) and o not in NAMES and o not in OPTION_ONLY:
                miss.add(o)
    for it in g.get("chars", []):
        if it[2] not in NAMES:
            miss.add(it[2])
    for it in g.get("songs", []):
        if it[1] not in NAMES:
            miss.add(it[1])
    for it in g.get("quotes", []):
        if it[2] not in NAMES:
            miss.add(it[2])
    for it in g.get("anime", []):
        if it[0] not in NAMES:
            miss.add(it[0])
    (ROOT / "tools" / "names_missing.txt").write_text("\n".join(sorted(miss)), encoding="utf-8")
    report.append(f"أسماء بلا ترجمة عربية في القاموس: {len(miss)} (tools/names_missing.txt)")
    print("\n".join(report))


if __name__ == "__main__":
    main()
