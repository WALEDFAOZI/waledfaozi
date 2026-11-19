"""ألعاب منفصلة عن الاختبار الرئيسي: صح/غلط، خمّن الأنمي من الأغنية، ورتّب حسب سنة العرض."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from .bot import btn, esc, kb
from .config import ROOT
from .ctx import Ctx
from . import progress
from .names import loc, loc_opt
from .texts import t

ROUNDS = {"tf": 10, "song": 10, "ord": 8, "char": 10, "quote": 10}
MC_KINDS = ("song", "char", "quote")   # أسئلة اختيار من متعدد


def item_key(content: str) -> str:
    """مفتاح ثابت لعنصر لعبة (للإبلاغ عنه وإخفائه) من نصه، فلا يتأثر بترتيب الملف."""
    return hashlib.md5(content.encode("utf-8")).hexdigest()[:12]


def round_info(kind: str, rd, data: dict) -> tuple[str, str]:
    """(المفتاح, وصف قصير) للجولة الحالية، لتُستخدم في البلاغات."""
    if kind == "tf":
        text = data["tf"][rd][0]
        return item_key(text), f"✅❌ {text}"
    if kind == "song":
        right = rd["options"][rd["answer"]]
        return item_key(f"{rd['song']}|{right}"), f"🎵 {rd['song']} → {right}"
    if kind == "char":
        return item_key(rd["text"]["ar"]), f"🕵️ {rd['text']['ar']}"
    if kind == "quote":
        return item_key(rd["text"]["en"]), f"💬 {rd['text']['en']}"
    names = ", ".join(i["name"] for i in rd["items"])
    return item_key("ord|" + names), f"📅 {names}"


def load_games(path: str | Path | None = None) -> dict:
    return json.loads(Path(path or ROOT / "data" / "games.json").read_text(encoding="utf-8"))


# ── المنطق الصافي (قابل للاختبار) ───────────────────────────
def tf_rounds(data: dict, rng: random.Random, n: int = 10, hidden=frozenset()) -> list[int]:
    ok = [i for i, s in enumerate(data["tf"]) if item_key(s[0]) not in hidden]
    return rng.sample(ok, min(n, len(ok)))


def _clash(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    if min(len(a), len(b)) < 3:        # أسماء قصيرة مثل «L»: نقارن بالتطابق فقط
        return a == b
    return a in b or b in a


def song_rounds(data: dict, rng: random.Random, n: int = 10, hidden=frozenset()) -> list[dict]:
    names = sorted({a for _, a in data["songs"]})
    visible = [x for x in data["songs"] if item_key(f"{x[0]}|{x[1]}") not in hidden]
    out = []
    for song, anime in rng.sample(visible, min(n, len(visible))):
        pool = [x for x in names if not _clash(x, anime)]
        options = [anime] + rng.sample(pool, 3)
        rng.shuffle(options)
        out.append({"song": song, "options": options, "answer": options.index(anime)})
    return out


def char_rounds(data: dict, rng: random.Random, n: int = 10, hidden=frozenset()) -> list[dict]:
    names = sorted({c[2] for c in data["chars"]})
    visible = [c for c in data["chars"] if item_key(c[0]) not in hidden]
    out = []
    for ar, en, name in rng.sample(visible, min(n, len(visible))):
        pool = [x for x in names if not _clash(x, name)]
        options = [name] + rng.sample(pool, 3)
        rng.shuffle(options)
        out.append({"text": {"ar": ar, "en": en}, "options": options, "answer": options.index(name)})
    return out


def quote_rounds(data: dict, rng: random.Random, n: int = 10, hidden=frozenset()) -> list[dict]:
    animes = sorted({q[2] for q in data["quotes"]} | set(data.get("quote_extra", [])))
    visible = [q for q in data["quotes"] if item_key(q[0]) not in hidden]
    out = []
    for en, ar, anime in rng.sample(visible, min(n, len(visible))):
        pool = [x for x in animes if not _clash(x, anime)]
        options = [anime] + rng.sample(pool, 3)
        rng.shuffle(options)
        out.append({"text": {"ar": ar, "en": en}, "options": options, "answer": options.index(anime)})
    return out


def order_rounds(data: dict, rng: random.Random, n: int = 8, hidden=frozenset()) -> list[dict]:
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


def new_state(kind: str, data: dict, rng: random.Random, hidden=frozenset()) -> dict:
    rounds = {"tf": tf_rounds, "song": song_rounds, "ord": order_rounds,
              "char": char_rounds, "quote": quote_rounds}[kind](data, rng, ROUNDS[kind], hidden)
    return {"rounds": rounds, "pos": 0, "score": 0, "picked": []}


def build_games_router(ctx: Ctx, data: dict | None = None) -> Router:
    r = Router()
    r.message.filter(F.chat.type == "private")
    r.callback_query.filter(F.message.chat.type == "private")
    db, rng = ctx.db, ctx.rng
    games = data or load_games()
    titles = {"tf": "g_tf", "song": "g_song", "ord": "g_ord", "char": "g_char", "quote": "g_quote"}

    def lang(uid: int) -> str:
        return db.get_lang(uid)

    def menu(L: str):
        return t(L, "g_menu"), kb([btn(t(L, "g_tf"), "g:tf")], [btn(t(L, "g_song"), "g:song")],
                                  [btn(t(L, "g_ord"), "g:ord")], [btn(t(L, "g_char"), "g:char")],
                                  [btn(t(L, "g_quote"), "g:quote")], [btn(t(L, "btn_menu"), "menu")])

    def screen(L: str, gid: int, kind: str, st: dict):
        text, markup = _screen(L, gid, kind, st)
        rows = list(markup.inline_keyboard) + [[btn(t(L, "btn_report_q"), f"gq:{gid}:{st['pos']}"),
                                                 btn(t(L, "g_stop"), f"gx:{gid}")]]      # إبلاغ + إنهاء في أي وقت
        return text, kb(*rows)

    def _screen(L: str, gid: int, kind: str, st: dict):
        n, total = st["pos"] + 1, len(st["rounds"])
        rd = st["rounds"][st["pos"]]
        if kind == "tf":
            s = games["tf"][rd]
            stmt = s[1] if L == "en" else loc(s[0], L)
            return (t(L, "g_tf_q", n=n, t=total, s=esc(stmt)),
                    kb([btn(t(L, "g_true"), f"gt:{gid}:1"), btn(t(L, "g_false"), f"gt:{gid}:0")]))
        if kind in MC_KINDS:
            prompt = rd["song"] if kind == "song" else loc(rd["text"].get(L) or rd["text"]["ar"], L)
            return (t(L, f"g_{kind}_q", n=n, t=total, s=esc(prompt)),
                    kb(*[[btn(loc_opt(o, L), f"gs:{gid}:{i}")] for i, o in enumerate(rd["options"])]))
        items = rd["items"]
        picked = "\n".join(f"{k + 1}) {esc(loc_opt(items[i]['name'], L))}" for k, i in enumerate(st["picked"])) or "—"
        left = [[btn(loc_opt(items[i]["name"], L), f"go:{gid}:{i}")] for i in range(len(items)) if i not in st["picked"]]
        return (t(L, "g_ord_q", n=n, t=total, picked=picked),
                kb(*left, [btn(t(L, "g_reset"), f"gr:{gid}")]))

    async def show(c: CallbackQuery, gid: int):
        g = db.get_game(gid)
        L = lang(c.from_user.id)
        st, kind = g["state"], g["kind"]
        if st["pos"] >= len(st["rounds"]):
            best = db.finish_game(gid, c.from_user.id, kind, st["score"])
            ps = progress.record(db, c.from_user.id, "game", score=st["score"])
            text = t(L, "g_end", title=t(L, titles[kind]), score=st["score"], total=len(st["rounds"]), best=best)
            if ps.xp:
                text += "\n" + t(L, "pg_xp_gain", xp=ps.xp)
            markup = kb([btn(t(L, "g_again"), f"g:{kind}")], [btn(t(L, "btn_menu"), "menu")])
        else:
            text, markup = screen(L, gid, kind, st)
        try:
            await c.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        except TelegramBadRequest:
            await c.message.answer(text, parse_mode="HTML", reply_markup=markup)
        if st["pos"] >= len(st["rounds"]):
            await progress.send_notice(c.bot, c.from_user.id, L, ps)

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

    extra_seen = [0]

    def sync_extras() -> None:
        """عبارات صح/غلط أضافها الأدمن من اللوحة: تُلحَق (فقط) بنهاية القائمة فتبقى فهارس الجولات الجارية ثابتة."""
        for eid, row in db.extras("tf", extra_seen[0]):
            games["tf"].append(row)
            extra_seen[0] = eid

    @r.callback_query(F.data.regexp(r"^g:(tf|song|ord|char|quote)$"))
    async def cb_start(c: CallbackQuery):
        await c.answer()
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        kind = c.data.split(":")[1]
        sync_extras()
        gid = db.new_game(c.from_user.id, kind, new_state(kind, games, rng, db.game_hidden()))
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
        await step(c, int(gid), ok, t(L, "g_ok" if ok else "g_bad") + (f"\n{loc(expl, L)}" if expl and not ok else ""))

    @r.callback_query(F.data.startswith("gs:"))
    async def cb_song(c: CallbackQuery):
        _, gid, idx = c.data.split(":")
        g = mine(c, int(gid))
        L = lang(c.from_user.id)
        if not g or g["kind"] not in MC_KINDS or g["state"]["pos"] >= len(g["state"]["rounds"]):
            await c.answer(t(L, "g_stale"))
            return
        rd = g["state"]["rounds"][g["state"]["pos"]]
        ok = int(idx) == rd["answer"]
        await step(c, int(gid), ok, t(L, "g_ok") if ok else f"{t(L, 'g_bad')} — {rd['options'][rd['answer']]}")

    # ── الإبلاغ عن عنصر لعبة (نفس قيود الأسئلة: لازم يكون ظهر لك، وبلاغ واحد لكل عنصر، وحد يومي) ──
    @r.callback_query(F.data.regexp(r"^gq:\d+:\d+$"))
    async def cb_game_report(c: CallbackQuery):
        _, gid, pos = c.data.split(":")
        L = lang(c.from_user.id)
        g = db.get_game(int(gid))
        if not g or g["tg_id"] != c.from_user.id or int(pos) >= len(g["state"]["rounds"]) or int(pos) > g["state"]["pos"]:
            await c.answer(t(L, "rp_closed"))
            return
        await c.answer()
        await c.message.answer(t(L, "rp_reason"), reply_markup=kb(
            *[[btn(t(L, f"rr_{i}"), f"gz:{gid}:{pos}:{i}")] for i in range(4)]))

    @r.callback_query(F.data.regexp(r"^gz:\d+:\d+:[0-3]$"))
    async def cb_game_report_send(c: CallbackQuery):
        _, gid, pos, ri = c.data.split(":")
        L = lang(c.from_user.id)
        g = db.get_game(int(gid))
        pos, ri = int(pos), int(ri)
        if not g or g["tg_id"] != c.from_user.id or pos >= len(g["state"]["rounds"]) or pos > g["state"]["pos"]:
            await c.answer(t(L, "rp_closed"))
            return
        kind = g["kind"]
        key, label = round_info(kind, g["state"]["rounds"][pos], games)
        res = db.add_game_report(kind, key, label, c.from_user.id, t("ar", f"rr_{ri}"), ctx.reports_per_day())
        if res == "dup":
            await c.answer(t(L, "rp_dup"), show_alert=True)
        elif res == "limit":
            await c.answer(t(L, "rp_limit", n=ctx.reports_per_day()), show_alert=True)
        else:
            await c.answer(t(L, "rp_ok"))
            if db.game_open_count(kind, key) == ctx.report_threshold():
                for admin in ctx.admin_ids():
                    try:
                        await c.bot.send_message(admin, f"🚩 عنصر لعبة وصل {ctx.report_threshold()} بلاغات مستقلة:\n{label}",
                                                 reply_markup=kb([btn("🔎 مراجعة", f"ad:gv:{kind}:{key}")]))
                    except TelegramAPIError:
                        pass
        try:
            await c.message.delete()                      # ننظّف رسالة الأسباب؛ اللعبة نفسها لم تتأثر
        except TelegramBadRequest:
            pass

    @r.callback_query(F.data.startswith("gx:"))
    async def cb_game_stop(c: CallbackQuery):
        gid = int(c.data.split(":")[1])
        L = lang(c.from_user.id)
        g = mine(c, gid)
        if not g:
            await c.answer(t(L, "g_stale"))
            return
        db.abort_game(gid)                           # بلا تسجيل نتيجة
        await c.answer()
        try:
            await c.message.edit_text(t(L, "g_stopped"), reply_markup=kb([btn(t(L, "btn_menu"), "menu")]))
        except TelegramBadRequest:
            await c.message.answer(t(L, "g_stopped"), reply_markup=kb([btn(t(L, "btn_menu"), "menu")]))

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
