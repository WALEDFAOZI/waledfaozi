"""إضافة محتوى من لوحة الأدمن: تحليل القوالب والتحقق (عبارات صح/غلط، أنمي) بنفس معايير الأمان."""
from __future__ import annotations

from .texts import GENRE_NAMES

BANNED = ("ecchi", "hentai", "harem", "إيتشي", "هنتاي", "حريم", "sex", "nude", "porn", "جنس", "عاري", "إباحي")

TF_HELP = ("➕ <b>عبارة صح/غلط</b>\nأرسل 3 أسطر (والرابع والخامس اختياري):\n"
           "1) العبارة بالعربي\n2) العبارة بالإنجليزي\n3) صح أو غلط\n4) تصحيح بالعربي (إن كانت غلط)\n5) تصحيح بالإنجليزي")

ANIME_HELP = ("➕ <b>أنمي جديد</b>\nأرسل الحقول، كل حقل في سطر بصيغة <code>اسم: قيمة</code>:\n"
              "<code>ar: الاسم العربي\nen: English name\ntype: film أو series\nyear: 2010\nstudio: Madhouse\n"
              "genres: action, drama\nrating: all أو teen أو mature\nseasons: 2\nepisodes: 50\nminutes: 100 (للفيلم)\n"
              "syn_ar: نبذة عربية\nsyn_en: English synopsis\nnote_ar / note_en: ملاحظة محتوى (إجبارية لـ mature)\n"
              "eps_ar / eps_en: وصف الحلقات إن كانت مستمرة (اختياري)\nongoing: yes (اختياري)</code>\n"
              f"الأنواع المسموحة: {', '.join(sorted(GENRE_NAMES))}")


def _unsafe(*texts: str) -> bool:
    blob = " ".join(texts).lower()
    return any(b in blob for b in BANNED)


def parse_tf(text: str):
    """→ ([ar, en, bool, exp_ar, exp_en], None) أو (None, رسالة خطأ)."""
    lines = [x.strip() for x in text.strip().splitlines() if x.strip()]
    if len(lines) < 3:
        return None, "لازم 3 أسطر على الأقل (عربي، إنجليزي، صح/غلط)."
    ans = lines[2].lower()
    if ans in ("صح", "true", "yes", "✅"):
        val = True
    elif ans in ("غلط", "خطأ", "false", "no", "❌"):
        val = False
    else:
        return None, "السطر الثالث لازم يكون «صح» أو «غلط»."
    if _unsafe(*lines):
        return None, "العبارة فيها كلمات غير مناسبة."
    exp_ar = lines[3] if len(lines) > 3 else ""
    exp_en = lines[4] if len(lines) > 4 else ""
    if not val and not (exp_ar and exp_en):
        return None, "العبارة الغلط تحتاج تصحيحًا بالعربي والإنجليزي (السطر 4 و5)."
    return [lines[0], lines[1], val, exp_ar, exp_en], None


def parse_anime(text: str, existing_keys: set[str]):
    f: dict[str, str] = {}
    for line in text.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            f[k.strip().lower()] = v.strip()
    for req in ("ar", "en", "type", "year", "studio", "genres", "rating", "syn_ar", "syn_en"):
        if not f.get(req):
            return None, f"ينقص الحقل: {req}"
    kind = f["type"].lower()
    if kind not in ("film", "series"):
        return None, "type لازم film أو series."
    if f["rating"].lower() not in ("all", "teen", "mature"):
        return None, "rating لازم all أو teen أو mature."
    genres = [g.strip().lower() for g in f["genres"].replace("،", ",").split(",") if g.strip()]
    bad = [g for g in genres if g not in GENRE_NAMES]
    if not genres or bad:
        return None, f"أنواع غير مسموحة: {', '.join(bad) or '—'}"
    if _unsafe(f["ar"], f["en"], f["syn_ar"], f["syn_en"], f["genres"]):
        return None, "العنوان أو النبذة فيها كلمات غير مناسبة — القائمة للأعمال النظيفة فقط."
    if not f["year"].isdigit() or not 1950 <= int(f["year"]) <= 2100:
        return None, "year غير صحيح."
    rating = f["rating"].lower()
    if rating == "mature" and not (f.get("note_ar") and f.get("note_en")):
        return None, "تصنيف mature يحتاج note_ar و note_en."

    def num(k):
        return int(f[k]) if f.get(k, "").isdigit() else None
    seasons, eps, minutes = num("seasons"), num("episodes"), num("minutes")
    ongoing = f.get("ongoing", "").lower() in ("yes", "نعم", "1", "true")
    if kind == "film":
        if not minutes:
            return None, "الفيلم يحتاج minutes."
        bucket = "film"
    else:
        if not (eps or f.get("eps_ar")):
            return None, "المسلسل يحتاج episodes أو eps_ar."
        bucket = "long" if (eps or 0) > 100 else "medium" if (eps or 0) > 26 else "short"
        if ongoing and not eps:
            bucket = "long"
    key = "x" + str(abs(hash(f["en"].lower())) % 10**8)
    base = "".join(ch for ch in f["en"].lower() if ch.isalnum())[:20] or key
    key = base
    while key in existing_keys:
        key += "x"
    return {"key": key, "ar": f["ar"], "en": f["en"], "kind": kind, "year": int(f["year"]), "studio": f["studio"],
            "genres": genres, "rating": rating, "seasons": seasons, "episodes": eps, "minutes": minutes,
            "ongoing": ongoing, "eps_ar": f.get("eps_ar", ""), "eps_en": f.get("eps_en", ""),
            "note_ar": f.get("note_ar", ""), "note_en": f.get("note_en", ""),
            "syn_ar": f["syn_ar"], "syn_en": f["syn_en"], "len": bucket}, None
