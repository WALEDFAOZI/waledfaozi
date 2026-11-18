"""اقتراح أنمي: قائمة منتقاة بمعيار أمان صارم (انظر tools/build_anime.py)، مع فلاتر وإبلاغ وإخفاء من الأدمن."""
from __future__ import annotations

import json
import random

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from .bot import btn, chan_row, esc, kb
from .config import ROOT
from .ctx import Ctx
from .games import item_key
from .texts import GENRE_NAMES, t

LENGTHS = ("film", "short", "medium", "long")


def load_anime() -> list[dict]:
    p = ROOT / "data" / "anime.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def hkey(a: dict) -> str:
    return item_key("anime|" + a["key"])


def pick(items: list[dict], hidden: set[str], genre: str, length: str, aud: str, seen: set[str], rng) -> dict | None:
    pool = [a for a in items if hkey(a) not in hidden
            and (genre == "x" or genre in a["genres"])
            and (length == "x" or a["len"] == length)
            and (aud == "x" or a["rating"] == "all")]
    fresh = [a for a in pool if a["key"] not in seen]
    if pool and not fresh:
        seen.clear()
        fresh = pool
    return rng.choice(fresh) if fresh else None


def render(a: dict, L: str) -> str:
    ar = L == "ar"
    title = f"<b>{esc(a['ar'] if ar else a['en'])}</b>\n<i>{esc(a['en'] if ar else a['ar'])}</i>"
    genres = " · ".join(GENRE_NAMES[g][0 if ar else 1] for g in a["genres"])
    if a["kind"] == "film":
        info = t(L, "an_film", m=a["minutes"])
    else:
        note = a["eps_ar"] if ar else a["eps_en"]
        if note:
            eps = note
        else:
            eps = t(L, "an_eps", n=a["episodes"])
        seas = t(L, "an_seasons", n=a["seasons"]) if a["seasons"] else ""
        info = t(L, "an_series", s=seas or "—", e=eps) if seas else f"📺 {eps}"
    lines = [title, "",
             f"{t(L, 'an_f_genre')}: {genres}",
             f"{t(L, 'an_f_rate')}: {t(L, 'an_rate_' + a['rating'])}",
             f"{t(L, 'an_f_info')}: {info} · {a['year']} · {esc(a['studio'])}"]
    note = a["note_ar"] if ar else a["note_en"]
    if note:
        lines.append(f"{t(L, 'an_f_note')}: {esc(note)}")
    lines += ["", esc(a["syn_ar"] if ar else a["syn_en"]), "", t(L, "an_foot")]
    return "\n".join(lines)


def build_recommend_router(ctx: Ctx) -> Router:
    r = Router(name="recommend")
    db = ctx.db
    items = load_anime()
    by_hash = {hkey(a): a for a in items}
    rng = random.Random()
    extra_seen = [0]

    def sync() -> None:
        """أنمي أضافه الأدمن من اللوحة."""
        for eid, a in db.extras("anime", extra_seen[0]):
            extra_seen[0] = eid
            if a["key"] not in {x["key"] for x in items}:
                items.append(a)
                by_hash[hkey(a)] = a
    seen: dict[int, set[str]] = {}

    def lang(uid: int) -> str:
        return db.get_lang(uid)

    def menu_markup(L: str):
        return kb([btn(t(L, "an_surprise"), "an:r:x:x:x"), btn(t(L, "an_family"), "an:r:x:x:a")],
                  [btn(t(L, "an_genre"), "an:gm"), btn(t(L, "an_len"), "an:lm")],
                  [btn(t(L, "an_back"), "menu")])

    @r.message(Command("anime"))
    async def cmd_anime(m: Message):
        db.upsert_user(m.from_user.id, m.from_user.full_name)
        L = lang(m.from_user.id)
        await m.answer(t(L, "an_menu"), parse_mode="HTML", reply_markup=menu_markup(L))

    @r.callback_query(F.data == "an:m")
    async def cb_menu(c: CallbackQuery):
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        L = lang(c.from_user.id)
        await c.answer()
        await c.message.answer(t(L, "an_menu"), parse_mode="HTML", reply_markup=menu_markup(L))

    @r.callback_query(F.data == "an:gm")
    async def cb_genres(c: CallbackQuery):
        L = lang(c.from_user.id)
        await c.answer()
        sync()
        used = sorted({g for a in items for g in a["genres"]})
        rows, row = [], []
        for g in used:
            row.append(btn(GENRE_NAMES[g][0 if L == "ar" else 1], f"an:r:{g}:x:x"))
            if len(row) == 2:
                rows.append(row); row = []
        if row:
            rows.append(row)
        await c.message.answer(t(L, "an_pick_genre"), reply_markup=kb(*rows, [btn(t(L, "an_back"), "an:m")]))

    @r.callback_query(F.data == "an:lm")
    async def cb_lengths(c: CallbackQuery):
        L = lang(c.from_user.id)
        await c.answer()
        await c.message.answer(t(L, "an_pick_len"), reply_markup=kb(
            *[[btn(t(L, f"an_len_{x}"), f"an:r:x:{x}:x")] for x in LENGTHS], [btn(t(L, "an_back"), "an:m")]))

    @r.callback_query(F.data.regexp(r"^an:r:([a-z]+):([a-z]+):([ax])$"))
    async def cb_result(c: CallbackQuery):
        _, _, g, ln, aud = c.data.split(":")
        uid = c.from_user.id
        L = lang(uid)
        await c.answer()
        sync()
        a = pick(items, db.game_hidden(), g, ln, aud, seen.setdefault(uid, set()), rng)
        if not a:
            await c.message.answer(t(L, "an_empty"), reply_markup=menu_markup(L))
            return
        seen[uid].add(a["key"])
        await c.message.answer(render(a, L), parse_mode="HTML", reply_markup=kb(
            [btn(t(L, "an_next"), f"an:r:{g}:{ln}:{aud}"), btn(t(L, "btn_report_q"), f"an:q:{hkey(a)}")],
            *chan_row(L), [btn(t(L, "an_back"), "an:m")]))

    @r.callback_query(F.data.regexp(r"^an:q:[0-9a-f]{12}$"))
    async def cb_report(c: CallbackQuery):
        L = lang(c.from_user.id)
        h = c.data.split(":")[2]
        sync()
        if h not in by_hash:
            await c.answer(t(L, "rp_closed"))
            return
        await c.answer()
        await c.message.answer(t(L, "rp_reason"), reply_markup=kb(
            *[[btn(t(L, f"rr_{i}"), f"an:z:{h}:{i}")] for i in range(4)]))

    @r.callback_query(F.data.regexp(r"^an:z:[0-9a-f]{12}:[0-3]$"))
    async def cb_report_send(c: CallbackQuery):
        _, _, h, ri = c.data.split(":")
        L = lang(c.from_user.id)
        a = by_hash.get(h)
        if not a:
            await c.answer(t(L, "rp_closed"))
            return
        label = f"🎬 {a['ar']} / {a['en']}"
        res = db.add_game_report("anime", h, label, c.from_user.id, t("ar", f"rr_{int(ri)}"), ctx.reports_per_day())
        if res == "dup":
            await c.answer(t(L, "rp_dup"), show_alert=True)
        elif res == "limit":
            await c.answer(t(L, "rp_limit", n=ctx.reports_per_day()), show_alert=True)
        else:
            await c.answer(t(L, "an_rp_ok"))
            if db.game_open_count("anime", h) == ctx.report_threshold():
                for admin in ctx.admin_ids():
                    try:
                        await c.bot.send_message(admin, f"🚩 أنمي وصل {ctx.report_threshold()} بلاغات مستقلة:\n{label}")
                    except Exception:  # noqa: BLE001
                        pass
    return r
