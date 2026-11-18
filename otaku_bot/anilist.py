"""توليد أسئلة «من هذه الشخصية؟» بالصور من AniList (وJikan كبديل).

لماذا الصور صحيحة؟ لأن الاسم والصورة يأتيان من **سجل واحد** في المصدر نفسه (الشخصية ↔ صورتها)،
فلا يمكن أن يختلّا. ونُرسل رابط الصورة لتليجرام ليجلبها بنفسه، فلا نحفظ ولا نعدّل شيئًا.
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Awaitable, Callable

ANILIST_URL = "https://graphql.anilist.co"
JIKAN_URL = "https://api.jikan.moe/v4/top/characters?page={page}"
ANILIST_BASE, JIKAN_BASE = 200_000_000, 300_000_000

QUERY = """
query($page:Int){Page(page:$page, perPage:50){
  characters(sort:FAVOURITES_DESC){
    id name{full} image{large} favourites
    media(sort:POPULARITY_DESC, perPage:1){nodes{id title{romaji english}}}
  }}}
"""

Post = Callable[[str, dict], Awaitable[dict]]
Get = Callable[[str], Awaitable[dict]]


@dataclass
class Char:
    id: int
    name: str
    image: str
    media: str | None = None


async def default_post(url: str, payload: dict) -> dict:
    import aiohttp
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
        async with s.post(url, json=payload) as r:
            r.raise_for_status()
            return await r.json()


async def default_get(url: str) -> dict:
    import aiohttp
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
        async with s.get(url) as r:
            r.raise_for_status()
            return await r.json()


def _clean(name: str) -> str:
    name = " ".join(name.split())
    if "," in name:                       # «Last, First» → «First Last»
        a, b = name.split(",", 1)
        name = f"{b.strip()} {a.strip()}".strip()
    return name


def _ok(name: str, image: str | None) -> bool:
    return bool(name and 2 <= len(name) <= 40 and image and image.startswith("https://")
                and "default" not in image and "questionmark" not in image)


async def fetch_anilist(post: Post = default_post, pages: int = 5) -> list[Char]:
    out: list[Char] = []
    for page in range(1, pages + 1):
        data = await post(ANILIST_URL, {"query": QUERY, "variables": {"page": page}})
        for c in data["data"]["Page"]["characters"]:
            name, img = _clean(c["name"]["full"] or ""), (c.get("image") or {}).get("large")
            nodes = (c.get("media") or {}).get("nodes") or []
            media = None
            if nodes:
                t = nodes[0]["title"]
                media = t.get("english") or t.get("romaji")
            if _ok(name, img):
                out.append(Char(c["id"], name, img, media))
        await asyncio.sleep(0.7)          # احترام حد الطلبات
    return out


async def fetch_jikan(get: Get = default_get, pages: int = 8) -> list[Char]:
    out: list[Char] = []
    for page in range(1, pages + 1):
        data = await get(JIKAN_URL.format(page=page))
        for c in data["data"]:
            name, img = _clean(c.get("name") or ""), ((c.get("images") or {}).get("jpg") or {}).get("image_url")
            if _ok(name, img):
                out.append(Char(c["mal_id"], name, img, None))
        await asyncio.sleep(1.0)
    return out


def _dedupe(chars: list[Char]) -> list[Char]:
    seen_n, seen_i, out = set(), set(), []
    for c in chars:
        k = c.name.lower()
        if k in seen_n or c.image in seen_i:
            continue
        seen_n.add(k)
        seen_i.add(c.image)
        out.append(c)
    return out


def build_questions(chars: list[Char], source: str, limit: int = 200,
                    rng: random.Random | None = None) -> list[dict]:
    rng = rng or random.Random(7)
    chars = _dedupe(chars)[:limit]
    base = ANILIST_BASE if source == "anilist" else JIKAN_BASE
    out: list[dict] = []

    def clash(a: str, b: str) -> bool:
        a, b = a.lower(), b.lower()
        return a in b or b in a

    for rank, c in enumerate(chars):
        level = 1 + min(7, rank // 25)                    # الأشهر = الأسهل
        same_media = [x for x in chars if x.media and x.media == c.media and x.id != c.id]
        near = [x for x in chars[max(0, rank - 20): rank + 20] if x.id != c.id]
        pool: list[Char] = []
        for cand in rng.sample(same_media, min(2, len(same_media))) + rng.sample(near, len(near)):
            if cand.name != c.name and not clash(cand.name, c.name) and all(cand.name != p.name for p in pool):
                pool.append(cand)
            if len(pool) == 3:
                break
        if len(pool) < 3:
            continue
        options = [c.name] + [p.name for p in pool]
        rng.shuffle(options)
        out.append({
            "id": base + c.id, "q": "من هذه الشخصية؟", "q_en": "Who is this character?",
            "options": options, "options_en": options, "answer": options.index(c.name),
            "category": "images", "base_difficulty": level, "image": c.image, "source": source,
        })
    return out


async def fetch_image_questions(limit: int = 200, post: Post = default_post,
                                get: Get = default_get) -> tuple[list[dict], str]:
    """يجرّب AniList ثم Jikan. يرفع Exception برسالة واضحة إن فشل الاثنان."""
    errors = []
    try:
        chars = await fetch_anilist(post)
        qs = build_questions(chars, "anilist", limit)
        if len(qs) >= 20:
            return qs, "AniList"
        errors.append("AniList: عدد قليل من النتائج")
    except Exception as e:  # noqa: BLE001
        errors.append(f"AniList: {type(e).__name__} {e}")
    try:
        chars = await fetch_jikan(get)
        qs = build_questions(chars, "jikan", limit)
        if len(qs) >= 20:
            return qs, "Jikan"
        errors.append("Jikan: عدد قليل من النتائج")
    except Exception as e:  # noqa: BLE001
        errors.append(f"Jikan: {type(e).__name__} {e}")
    raise RuntimeError(" | ".join(errors))
