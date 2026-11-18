"""ألعاب منفصلة عن الاختبار الرئيسي: صح/غلط، خمّن الأنمي من الأغنية، ورتّب حسب سنة العرض."""
from __future__ import annotations

import json
import random
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from .bot import btn, esc, kb
from .config import ROOT
from .ctx import Ctx
from .texts import t

ROUNDS = {"tf": 10, "song": 10, "ord": 8}


def load_games(path: str | Path | None = None) -> dict:
    return json.loads(Path(path or ROOT / "data" / "games.json").read_text(encoding="utf-8"))


# ── المنطق الصافي (قابل للاختبار) ───────────────────────────
def tf_rounds(data: dict, rng: random.Random, n: int = 10) -> list[int]:
    return rng.sample(range(len(data["tf"])), min(n, len(data["tf"])))


def _clash(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    return a in b or b in a


def song_rounds(data: dict, rng: random.Random, n: int = 10) -> list[dict]:
    names = sorted({a for _, a in data["songs"]})
    out = []
    for song, anime in rng.sample(data["songs"], min(n, len(data["songs"]))):
        pool = [x for x in names if not _clash(x, anime)]
        options = [anime] + rng.sample(pool, 3)
        rng.shuffle(options)
        out.append({"song": song, "options": options, "answer": options.index(anime)})
    return out


def order_rounds(data: dict, rng: random.Random, n: int = 8) -> list[dict]:
    out = []
    items = data["anime"]
    for _ in range(n):
        pool = items[:]
        rng.shuffle(pool)
        chosen, years = [], set()
        for name, year in pool:
            if year not in years:
                chosen.append({"name": name, "year": year})
                years.add(year)
            if len(chosen) == 4:
                break
        out.append({"items": chosen})            # الترتيب المعروض عشوائي، والصحيح بالسنة
    return out


def order_correct(round_: dict) -> list[int]:
    items = round_["items"]
    return sorted(range(len(items)), key=lambda i: items[i]["year"])


def new_state(kind: str, data: dict, rng: random.Random) -> dict:
    rounds = {"tf": tf_rounds, "song": song_rounds, "ord": order_rounds}[kind](data, rng, ROUNDS[kind])
    return {"rounds": rounds, "pos": 0, "score": 0, "picked": []}


def build_games_router(ctx: Ctx, data: dict | None = None) -> Router:
    r = Router()
    db, rng = ctx.db, ctx.rng
    games = data or load_games()
    titles = {"tf": "g_tf", "song": "g_song", "ord": "g_ord"}

    def lang(uid: int) -> str:
        return db.get_lang(uid)

    def menu(L: str):
        return t(L, "g_menu"), kb([btn(t(L, "g_tf"), "g:tf")], [btn(t(L, "g_song"), "g:song")],
                                  [btn(t(L, "g_ord"), "g:ord")], [btn(t(L, "btn_menu"), "menu")])

    def screen(L: str, gid: int, kind: str, st: dict):
        n, total = st["pos"] + 1, len(st["rounds"])
        rd = st["rounds"][st["pos"]]
        if kind == "tf":
            s = games["tf"][rd]
            stmt = s[1] if L == "en" else s[0]
            return (t(L, "g_tf_q", n=n, t=total, s=esc(stmt)),
                    kb([btn(t(L, "g_true"), f"gt:{gid}:1"), btn(t(L, "g_false"), f"gt:{gid}:0")]))
        if kind == "song":
            return (t(L, "g_song_q", n=n, t=total, s=esc(rd["song"])),
                    kb(*[[btn(o, f"gs:{gid}:{i}")] for i, o in enumerate(rd["options"])]))
        items = rd["items"]
        picked = "\n".join(f"{k + 1}) {esc(items[i]['name'])}" for k, i in enumerate(st["picked"])) or "—"
        left = [[btn(items[i]["name"], f"go:{gid}:{i}")] for i in range(len(items)) if i not in st["picked"]]
        return (t(L, "g_ord_q", n=n, t=total, picked=picked),
                kb(*left, [btn(t(L, "g_reset"), f"gr:{gid}")]))

    async def show(c: CallbackQuery, gid: int):
        g = db.get_game(gid)
        L = lang(c.from_user.id)
        st, kind = g["state"], g["kind"]
        if st["pos"] >= len(st["rounds"]):
            best = db.finish_game(gid, c.from_user.id, kind, st["score"])
            text = t(L, "g_end", title=t(L, titles[kind]), score=st["score"], total=len(st["rounds"]), best=best)
            markup = kb([btn(t(L, "g_again"), f"g:{kind}")], [btn(t(L, "btn_menu"), "menu")])
        else:
            text, markup = screen(L, gid, kind, st)
        try:
            await c.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        except TelegramBadRequest:
            await c.message.answer(text, parse_mode="HTML", reply_markup=markup)

    def mine(c: CallbackQuery, gid: int):
        g = db.get_game(gid)
        if not g or g["tg_id"] != c.from_user.id or g["finished_at"]:
            return None
        return g

    @r.message(Command("games"))
    async def cmd_games(m: Message):
        text, markup = menu(lang(m.from_user.id))
        await m.answer(text, parse_mode="HTML", reply_markup=markup)

    @r.callback_query(F.data == "g:menu")
    async def cb_menu(c: CallbackQuery):
        await c.answer()
        text, markup = menu(lang(c.from_user.id))
        await c.message.answer(text, parse_mode="HTML", reply_markup=markup)

    @r.callback_query(F.data.regexp(r"^g:(tf|song|ord)$"))
    async def cb_start(c: CallbackQuery):
        await c.answer()
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        kind = c.data.split(":")[1]
        gid = db.new_game(c.from_user.id, kind, new_state(kind, games, rng))
        g = db.get_game(gid)
        L = lang(c.from_user.id)
        text, markup = screen(L, gid, kind, g["state"])
        await c.message.answer(text, parse_mode="HTML", reply_markup=markup)

    async def step(c: CallbackQuery, gid: int, ok: bool, toast: str):
        g = db.get_game(gid)
        st = g["state"]
        st["score"] += int(ok)
        st["pos"] += 1
        st["picked"] = []
        db.save_game(gid, st)
        await c.answer(toast[:190])
        await show(c, gid)

    @r.callback_query(F.data.startswith("gt:"))
    async def cb_tf(c: CallbackQuery):
        _, gid, ans = c.data.split(":")
        g = mine(c, int(gid))
        L = lang(c.from_user.id)
        if not g or g["kind"] != "tf" or g["state"]["pos"] >= len(g["state"]["rounds"]):
            await c.answer(t(L, "g_stale"))
            return
        s = games["tf"][g["state"]["rounds"][g["state"]["pos"]]]
        ok = bool(int(ans)) == s[2]
        expl = s[4] if L == "en" else s[3]
        await step(c, int(gid), ok, t(L, "g_ok" if ok else "g_bad") + (f"\n{expl}" if expl and not ok else ""))

    @r.callback_query(F.data.startswith("gs:"))
    async def cb_song(c: CallbackQuery):
        _, gid, idx = c.data.split(":")
        g = mine(c, int(gid))
        L = lang(c.from_user.id)
        if not g or g["kind"] != "song" or g["state"]["pos"] >= len(g["state"]["rounds"]):
            await c.answer(t(L, "g_stale"))
            return
        rd = g["state"]["rounds"][g["state"]["pos"]]
        ok = int(idx) == rd["answer"]
        await step(c, int(gid), ok, t(L, "g_ok") if ok else f"{t(L, 'g_bad')} — {rd['options'][rd['answer']]}")

    @r.callback_query(F.data.startswith("gr:"))
    async def cb_reset(c: CallbackQuery):
        gid = int(c.data.split(":")[1])
        g = mine(c, gid)
        if not g or g["kind"] != "ord":
            await c.answer(t(lang(c.from_user.id), "g_stale"))
            return
        g["state"]["picked"] = []
        db.save_game(gid, g["state"])
        await c.answer()
        await show(c, gid)

    @r.callback_query(F.data.startswith("go:"))
    async def cb_order(c: CallbackQuery):
        _, gid, idx = c.data.split(":")
        gid, idx = int(gid), int(idx)
        g = mine(c, gid)
        L = lang(c.from_user.id)
        if not g or g["kind"] != "ord" or g["state"]["pos"] >= len(g["state"]["rounds"]):
            await c.answer(t(L, "g_stale"))
            return
        st = g["state"]
        rd = st["rounds"][st["pos"]]
        if idx in st["picked"] or not 0 <= idx < len(rd["items"]):
            await c.answer()
            return
        st["picked"].append(idx)
        if len(st["picked"]) < len(rd["items"]):
            db.save_game(gid, st)
            await c.answer()
            await show(c, gid)
            return
        correct = order_correct(rd)
        ok = st["picked"] == correct
        if ok:
            toast = t(L, "g_ord_ok")
        else:
            order = " ← ".join(f"{rd['items'][i]['name']} ({rd['items'][i]['year']})" for i in correct)
            toast = t(L, "g_ord_bad", order=order)
        await step(c, gid, ok, toast)

    return r
