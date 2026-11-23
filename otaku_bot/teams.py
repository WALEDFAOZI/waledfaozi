"""العشائر (فرق): ينشئ اللاعب عشيرة أو ينضم إليها، وتتنافس بمجموع خبرة أعضائها أسبوعيًا وكليًا. الأدمن لا ينضم (إخفاء الهوية)."""
from __future__ import annotations

from urllib.parse import quote

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .bot import btn, chan_row, esc, kb
from .content import BANNED
from .ctx import Ctx
from .texts import t
from .timeutil import week_start

NAME_MIN, NAME_MAX = 3, 20


class TeamFlow(StatesGroup):
    name = State()


def valid_name(name: str) -> str | None:
    """يرجع سبب الرفض أو None."""
    n = name.strip()
    if not NAME_MIN <= len(n) <= NAME_MAX:
        return "len"
    low = n.lower()
    if any(x in low for x in ("@", "http", "t.me", ".com", "www")) or any(b in low for b in BANNED):
        return "bad"
    return None


def build_teams_router(ctx: Ctx) -> Router:
    r = Router(name="teams")
    r.message.filter(F.chat.type == "private")
    r.callback_query.filter(F.message.chat.type == "private")
    db = ctx.db

    def lang(uid: int) -> str:
        return db.get_lang(uid)

    def team_view(uid: int, L: str):
        u = db.get_user(uid)
        tid = u["team_id"]
        team = db.get_team(tid)
        since = week_start()
        members = db.team_members(tid, since, 8)
        leader = db.get_user(team["leader"])
        rows = "\n".join(f"{i}. {esc(t(db.get_lang(m['tg_id']), 'anon_name') if db.is_admin(m['tg_id']) else (m['name'] or '?'))} — ⭐{m['wxp']}"
                         for i, m in enumerate(members, 1))
        week_xp = sum(m["wxp"] for m in db.team_members(tid, since, 100))
        text = t(L, "tm_view", name=esc(team["name"]), n=db.team_size(tid), mx=db.TEAM_MAX,
                 leader=esc(leader["name"] if leader and not db.is_admin(leader["tg_id"]) else "—"),
                 wxp=week_xp, rank=db.team_rank(tid, since) or "—", rows=rows or "—")
        return text, tid

    async def home(target: Message, uid: int):
        L = lang(uid)
        u = db.get_user(uid)
        if u and u["team_id"] and db.get_team(u["team_id"]) and not db.get_team(u["team_id"])["hidden"]:
            text, tid = team_view(uid, L)
            me = (await target.bot.get_me()).username
            link = f"https://t.me/{me}?start=tm_{tid}"
            await target.answer(text, parse_mode="HTML", reply_markup=kb(
                [btn(t(L, "tm_invite"), url=f"https://t.me/share/url?url={quote(link)}&text={quote(t(L, 'tm_invite_text', name=db.get_team(tid)['name']))}")],
                [btn(t(L, "tm_rank_btn"), "lb:T:w"), btn(t(L, "tm_leave"), "tm:l")],
                [btn(t(L, "btn_menu"), "menu")]))
            return
        if db.is_admin(uid):
            await target.answer(t(L, "tm_admin_no"), reply_markup=kb([btn(t(L, "btn_menu"), "menu")]))
            return
        await target.answer(t(L, "tm_none"), parse_mode="HTML", reply_markup=kb(
            [btn(t(L, "tm_create"), "tm:new")], [btn(t(L, "tm_join_list"), "tm:list")],
            [btn(t(L, "tm_rank_btn"), "lb:T:w")], [btn(t(L, "btn_menu"), "menu")]))

    @r.callback_query(F.data == "tm:m")
    async def cb_home(c: CallbackQuery, state: FSMContext):
        await c.answer()
        await state.clear()
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        await home(c.message, c.from_user.id)

    @r.callback_query(F.data == "tm:new")
    async def cb_new(c: CallbackQuery, state: FSMContext):
        L = lang(c.from_user.id)
        if db.is_admin(c.from_user.id) or (db.get_user(c.from_user.id) or {})["team_id"]:
            await c.answer(t(L, "tm_cant"), show_alert=True)
            return
        await c.answer()
        await state.set_state(TeamFlow.name)
        await c.message.answer(t(L, "tm_ask_name", a=NAME_MIN, b=NAME_MAX), reply_markup=kb([btn(t(L, "fb_cancel"), "tm:m")]))

    @r.message(TeamFlow.name, F.text, ~F.text.startswith("/"))
    async def on_name(m: Message, state: FSMContext):
        uid, L = m.from_user.id, lang(m.from_user.id)
        bad = valid_name(m.text)
        if bad:
            await m.answer(t(L, "tm_name_" + bad, a=NAME_MIN, b=NAME_MAX))
            return
        tid = db.create_team(m.text.strip(), uid)
        await state.clear()
        if not tid:
            await m.answer(t(L, "tm_taken"))
            return
        await m.answer(t(L, "tm_created", name=esc(m.text.strip())), parse_mode="HTML")
        await home(m, uid)

    @r.callback_query(F.data == "tm:list")
    async def cb_list(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        rows = [r_ for r_ in db.team_board(week_start(), 20) if r_["members"] < db.TEAM_MAX][:8]
        if not rows:
            await c.message.answer(t(L, "tm_none_yet"), reply_markup=kb([btn(t(L, "tm_create"), "tm:new")], [btn(t(L, "btn_menu"), "menu")]))
            return
        btns = [[btn(f"🛡 {x['name']} · 👥{x['members']} · ⭐{x['pts']}", f"tm:j:{x['id']}")] for x in rows]
        await c.message.answer(t(L, "tm_pick"), reply_markup=kb(*btns, [btn(t(L, "btn_menu"), "menu")]))

    @r.callback_query(F.data.regexp(r"^tm:j:\d+$"))
    async def cb_join(c: CallbackQuery):
        uid, L = c.from_user.id, lang(c.from_user.id)
        db.upsert_user(uid, c.from_user.full_name)
        res = db.join_team(uid, int(c.data.split(":")[2]))
        if res != "ok":
            await c.answer(t(L, "tm_join_" + res), show_alert=True)
            return
        await c.answer(t(L, "tm_joined"))
        await home(c.message, uid)

    @r.callback_query(F.data == "tm:l")
    async def cb_leave(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        await c.message.answer(t(L, "tm_leave_ask"), reply_markup=kb([btn(t(L, "tm_leave_yes"), "tm:l2")], [btn(t(L, "fb_cancel"), "tm:m")]))

    @r.callback_query(F.data == "tm:l2")
    async def cb_leave2(c: CallbackQuery):
        db.leave_team(c.from_user.id)
        await c.answer(t(lang(c.from_user.id), "tm_left"), show_alert=True)
        await home(c.message, c.from_user.id)

    return r
