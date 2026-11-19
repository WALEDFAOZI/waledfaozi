"""تبادل الشخصيات: تحدٍّ بين صديقين (من تحدي الصديق). كل واحد يعرف شخصية الآخر ولا يعرف شخصيته،
يسأل صاحبه في أي مكان (البوت لا يتدخل في الأسئلة)، وأول من يخمّن شخصيته الصحيحة يفوز.
الشخصيتان من نفس مستوى الصعوبة. التخمين بالكتابة في الخاص، مع فترة قصيرة بين المحاولات."""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from urllib.parse import quote

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from . import progress
from .bot import btn, esc, kb
from .config import ROOT
from .ctx import Ctx
from .names import loc
from .spy_game import load_characters, normalize
from .texts import t

GUESS_COOLDOWN = 10
counter = [0]
swaps: dict[int, dict] = {}


class SwapFlow(StatesGroup):
    guess = State()


def levels() -> dict[int, list[dict]]:
    lv = json.loads((ROOT / "data" / "char_levels.json").read_text(encoding="utf-8"))
    by_en = {c["en"]: c for c in load_characters()}
    out: dict[int, list[dict]] = {}
    for en, level in lv.items():
        if en in by_en:
            out.setdefault(level, []).append(by_en[en])
    return out


def match(text: str, char: dict) -> bool:
    """التخمين الصحيح: الاسم الإنجليزي أو العربي الكامل فقط (بعد توحيد الحروف)."""
    g = normalize(text)
    return g in {normalize(char["en"]), normalize(char["ar"])}


def build_swap_router(ctx: Ctx) -> Router:
    db = ctx.db
    rng: random.Random = ctx.rng
    r = Router(name="swap")
    r.message.filter(F.chat.type == "private")
    r.callback_query.filter(F.message.chat.type == "private")
    lv_cache: dict[int, list[dict]] = {}

    def lang(uid: int) -> str:
        return db.get_lang(uid)

    def busy(uid: int) -> bool:
        return any(s["state"] == "play" and uid in (s["a"], s["b"]) for s in swaps.values())

    def pair() -> tuple[dict, dict]:
        if not lv_cache:
            lv_cache.update(levels())
        options = [lvl for lvl, chars in lv_cache.items() if len(chars) >= 2]
        level = rng.choice(options)
        a, b = rng.sample(lv_cache[level], 2)
        return a, b

    async def dm(bot: Bot, uid: int, text: str, markup=None) -> None:
        try:
            await bot.send_message(uid, text, parse_mode="HTML", reply_markup=markup)
        except TelegramAPIError:
            pass

    def play_markup(sid: int, L: str):
        return kb([btn(t(L, "sw_guess_btn"), f"sw:g:{sid}")], [btn(t(L, "sw_quit_btn"), f"sw:x:{sid}")])

    async def start_game(bot: Bot, s: dict) -> None:
        a, b = pair()
        s["ca"], s["cb"], s["state"] = a, b, "play"
        s["started"] = time.time()
        for uid, other in ((s["a"], b), (s["b"], a)):
            L = lang(uid)
            await dm(bot, uid, t(L, "sw_start", other=esc(loc(other["en"], L))), play_markup(s["id"], L))

    @r.callback_query(F.data == "sw:new")
    async def cb_new(c: CallbackQuery):
        await c.answer()
        uid, L = c.from_user.id, lang(c.from_user.id)
        db.upsert_user(uid, c.from_user.full_name)
        if busy(uid):
            await c.message.answer(t(L, "sw_busy"))
            return
        counter[0] += 1
        sid = counter[0]
        swaps[sid] = {"id": sid, "a": uid, "b": None, "state": "invite", "last": {}}
        me = (await c.bot.get_me()).username
        link = f"https://t.me/{me}?start=sw_{sid}"
        await c.message.answer(t(L, "sw_invite_text"), parse_mode="HTML", reply_markup=kb(
            [btn(t(L, "sw_share_btn"), url=f"https://t.me/share/url?url={quote(link)}&text={quote(t(L, 'sw_share_text'))}")],
            [btn(t(L, "btn_menu"), "menu")]))

    @r.message(CommandStart(deep_link=True, magic=F.args.startswith("sw_")))
    async def on_start(m: Message):
        L = lang(m.from_user.id)
        db.upsert_user(m.from_user.id, m.from_user.full_name)
        try:
            sid = int((m.text or "").split("sw_", 1)[1].split()[0])
        except (IndexError, ValueError):
            await m.answer(t(L, "sw_gone"))
            return
        s = swaps.get(sid)
        if not s or s["state"] != "invite" or s["a"] == m.from_user.id:
            await m.answer(t(L, "sw_gone"))
            return
        if busy(m.from_user.id):
            await m.answer(t(L, "sw_busy"))
            return
        await m.answer(t(L, "sw_accept_ask", name=esc(m.from_user.full_name)), parse_mode="HTML",
                       reply_markup=kb([btn(t(L, "sw_accept_btn"), f"sw:acc:{sid}")]))

    @r.callback_query(F.data.regexp(r"^sw:acc:\d+$"))
    async def cb_accept(c: CallbackQuery):
        L = lang(c.from_user.id)
        sid = int(c.data.split(":")[2])
        s = swaps.get(sid)
        if not s or s["state"] != "invite" or s["a"] == c.from_user.id or busy(c.from_user.id):
            await c.answer(t(L, "sw_gone"), show_alert=True)
            return
        s["b"] = c.from_user.id
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        await c.answer()
        await start_game(c.bot, s)

    @r.callback_query(F.data.regexp(r"^sw:g:\d+$"))
    async def cb_guess(c: CallbackQuery, state: FSMContext):
        L = lang(c.from_user.id)
        s = swaps.get(int(c.data.split(":")[2]))
        if not s or s["state"] != "play" or c.from_user.id not in (s["a"], s["b"]):
            await c.answer(t(L, "sw_gone"), show_alert=True)
            return
        await c.answer()
        await state.set_state(SwapFlow.guess)
        await state.update_data(sid=s["id"])
        await c.message.answer(t(L, "sw_guess_ask"), parse_mode="HTML")

    @r.message(SwapFlow.guess, F.text, ~F.text.startswith("/"))
    async def on_guess(m: Message, state: FSMContext):
        L = lang(m.from_user.id)
        uid = m.from_user.id
        sid = (await state.get_data()).get("sid")
        s = swaps.get(sid)
        if not s or s["state"] != "play" or uid not in (s["a"], s["b"]):
            await state.clear()
            await m.answer(t(L, "sw_gone"))
            return
        now = time.time()
        if now - s["last"].get(uid, 0) < GUESS_COOLDOWN:
            await m.answer(t(L, "sw_cooldown", s=GUESS_COOLDOWN))
            return
        s["last"][uid] = now
        mine = s["ca"] if uid == s["a"] else s["cb"]
        if match(m.text, mine):
            await state.clear()
            await finish(m.bot, s, winner=uid)
            return
        await m.answer(t(L, "sw_wrong"))

    @r.callback_query(F.data.regexp(r"^sw:x:\d+$"))
    async def cb_quit(c: CallbackQuery):
        L = lang(c.from_user.id)
        s = swaps.get(int(c.data.split(":")[2]))
        if not s or s["state"] != "play" or c.from_user.id not in (s["a"], s["b"]):
            await c.answer(t(L, "sw_gone"), show_alert=True)
            return
        await c.answer()
        other = s["b"] if c.from_user.id == s["a"] else s["a"]
        await finish(c.bot, s, winner=other)

    async def finish(bot: Bot, s: dict, winner: int) -> None:
        s["state"] = "done"
        a, b = s["a"], s["b"]
        for uid in (a, b):
            L = lang(uid)
            own = s["ca"] if uid == a else s["cb"]
            other_char = s["cb"] if uid == a else s["ca"]
            head = t(L, "sw_win" if uid == winner else "sw_lose")
            await dm(bot, uid, t(L, "sw_end", head=head, own=esc(loc(own["en"], L)), other=esc(loc(other_char["en"], L))))
            if uid == winner:
                progress.bonus(db, uid, "duel_win", 25, "duel_wins")
            progress.record(db, uid, "duel", correct=0, won=uid == winner)
        swaps.pop(s["id"], None)

    return r
