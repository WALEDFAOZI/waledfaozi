"""مافيا أونلاين: طابور ثم غرفة خاصة لكل لعبة، كلها في الخاص مع البوت، بلا مجموعة ولا قناة.

محرّك المجموعة والقناة (mafia_game.py) لا يُمسّ. هنا نفس القواعد الأساسية (من mafia.py) مع
عرض يناسب الأونلاين: كل لاعب يتلقى الحالة في الخاص، والنقاش نصّ يصل للجميع باسم المرسل.
الأدوار المتاحة: قاتل، طبيب، محقق، مواطن. (العمدة والمجنون للمجموعة فقط.)
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message

from . import mafia as M
from .bot import btn, esc, kb
from .ctx import Ctx
from .texts import t

log = logging.getLogger(__name__)
MIN_PLAYERS = 5
START_AT = 8          # يبدأ فورًا عند اكتمال هذا العدد
MAX_PLAYERS = 15
QUEUE_SECS = 180      # إن لم يكتمل START_AT: يبدأ بعد هذه المدة إن وُجد MIN_PLAYERS
NIGHT_SECS = 60
TALK_SECS = 180
VOTE_SECS = 60
MSG_GAP = 3.0         # ثوانٍ بين رسالتين من اللاعب نفسه
MSG_MAX = 300         # أقصى طول للرسالة
ICON = {"killer": "🔪", "citizen": "🧑", "detective": "🔍", "doctor": "🩺"}


@dataclass
class Seat:
    uid: int
    name: str
    role: str = "citizen"
    alive: bool = True


@dataclass
class Room:
    rid: int
    seats: dict[int, Seat]
    round: int = 0
    state: str = "night"                       # night | talk | vote | done
    night_picks: dict = field(default_factory=dict)     # قاتل -> هدف
    night_actions: dict = field(default_factory=dict)   # دور -> هدف
    last_protect: int | None = None
    votes: dict = field(default_factory=dict)
    last_sent: dict = field(default_factory=dict)       # uid -> وقت آخر رسالة نقاش
    task: asyncio.Task | None = None


queue: list[tuple[int, str]] = []        # (uid, الاسم)
queue_token = [0]                         # يتغيّر كلما فرغ الطابور، فتتوقف مؤقتات قديمة
rooms: dict[int, Room] = {}
user_room: dict[int, int] = {}
counter = [0]


def build_mafia_online_router(ctx: Ctx) -> Router:
    db, rng = ctx.db, ctx.rng
    r = Router(name="mafia_online")
    r.callback_query.filter(F.message.chat.type == "private")
    r.message.filter(F.chat.type == "private")

    def L_(uid: int) -> str:
        return db.get_lang(uid)

    async def say(bot: Bot, uid: int, text: str, markup=None) -> bool:
        try:
            await bot.send_message(uid, text, parse_mode="HTML", reply_markup=markup)
            return True
        except TelegramAPIError:
            return False

    async def broadcast(bot: Bot, room: Room, key: str, alive_only: bool = False, **kw) -> None:
        for s in list(room.seats.values()):
            if alive_only and not s.alive:
                continue
            await say(bot, s.uid, t(L_(s.uid), key, **kw))

    def alive(room: Room) -> list[Seat]:
        return [s for s in room.seats.values() if s.alive]

    def role_of(room: Room) -> dict[int, str]:
        return {s.uid: s.role for s in room.seats.values()}

    # ── الطابور ──────────────────────────────────────────
    def start_watch(bot: Bot) -> None:
        queue_token[0] += 1
        asyncio.get_event_loop().create_task(_watch(bot, queue_token[0]))

    async def _watch(bot: Bot, token: int) -> None:
        await asyncio.sleep(QUEUE_SECS)
        if token != queue_token[0] or not queue:
            return
        if len(queue) >= MIN_PLAYERS:
            take = queue[:MAX_PLAYERS]
            del queue[:len(take)]
            queue_token[0] += 1
            start_room(bot, take)
        else:
            for uid, _ in queue:
                await say(bot, uid, t(L_(uid), "mo_timeout", min=MIN_PLAYERS))
            queue.clear()
            queue_token[0] += 1

    @r.callback_query(F.data == "mo:j")
    async def cb_join(c: CallbackQuery):
        uid, L = c.from_user.id, L_(c.from_user.id)
        db.upsert_user(uid, c.from_user.full_name)
        if uid in user_room:
            await c.answer(t(L, "mo_busy"), show_alert=True)
            return
        if any(u == uid for u, _ in queue):
            await c.answer(t(L, "mo_already"), show_alert=True)
            return
        await c.answer()
        was_empty = not queue
        queue.append((uid, esc(c.from_user.full_name)))
        if was_empty:
            start_watch(c.bot)
        if len(queue) >= START_AT:
            take = queue[:START_AT]
            del queue[:START_AT]
            queue_token[0] += 1
            start_room(c.bot, take)
            return
        await c.message.answer(t(L, "mo_queued", n=len(queue), s=QUEUE_SECS, min=MIN_PLAYERS), parse_mode="HTML",
                               reply_markup=kb([btn(t(L, "mo_cancel_btn"), "mo:c")]))

    @r.callback_query(F.data == "mo:c")
    async def cb_cancel(c: CallbackQuery):
        queue[:] = [x for x in queue if x[0] != c.from_user.id]
        if not queue:
            queue_token[0] += 1
        await c.answer(t(L_(c.from_user.id), "mo_cancelled"))

    # ── بدء الغرفة وتوزيع الأدوار ───────────────────────
    def start_room(bot: Bot, take: list[tuple[int, str]]) -> None:
        counter[0] += 1
        rid = counter[0]
        n = len(take)
        killers = M.auto_config(max(MIN_PLAYERS, n))[0]
        specials = ["detective"] + (["doctor"] if n >= 6 else [])
        cfg = M.Config(killers=killers, specials=specials)
        uids = [uid for uid, _ in take]
        roles = M.assign(uids, cfg, rng)
        seats = {uid: Seat(uid, name, roles[uid]) for uid, name in take}
        room = Room(rid=rid, seats=seats)
        rooms[rid] = room
        for uid in uids:
            user_room[uid] = rid
        room.task = asyncio.get_event_loop().create_task(run_room(bot, room))

    async def send_roles(bot: Bot, room: Room) -> None:
        mates = [s.name for s in room.seats.values() if s.role == "killer"]
        for s in room.seats.values():
            L = L_(s.uid)
            text = t(L, "mf_role_dm", icon=ICON[s.role], role=t(L, "mf_r_" + s.role),
                     desc=t(L, "mf_desc_" + s.role), team=t(L, "mf_team_" + M.ROLES[s.role][1]))
            if s.role == "killer" and len(mates) > 1:
                text += "\n" + t(L, "mo_killer_mates", names="، ".join(m for m in mates if m != s.name))
            await say(bot, s.uid, text)

    # ── الليل ─────────────────────────────────────────────
    async def night(bot: Bot, room: Room) -> None:
        room.state = "night"
        room.night_picks, room.night_actions = {}, {}
        ids_alive = alive(room)
        await broadcast(bot, room, "mo_night", alive_only=False, r=room.round, s=NIGHT_SECS)
        for s in ids_alive:
            L = L_(s.uid)
            if s.role == "killer":
                opts = [x for x in ids_alive if x.role != "killer"]
            elif s.role == "doctor":
                opts = [x for x in ids_alive if x.uid != room.last_protect]
            elif s.role == "detective":
                opts = [x for x in ids_alive if x.uid != s.uid]
            else:
                await say(bot, s.uid, t(L, "mo_night_wait"))
                continue
            rows = [[btn(x.name[:24], f"mo:n:{room.rid}:{s.role}:{x.uid}")] for x in opts]
            await say(bot, s.uid, t(L, "mo_pick_" + s.role), kb(*rows))
        deadline = time.monotonic() + NIGHT_SECS
        while time.monotonic() < deadline and not _night_complete(room):
            await asyncio.sleep(0.5)

    def _night_complete(room: Room) -> bool:
        """كل قاتل اختار، والطبيب والمحقق (إن كانا أحياء) اختارا."""
        for s in alive(room):
            if s.role == "killer" and s.uid not in room.night_picks:
                return False
            if s.role in ("doctor", "detective") and s.role not in room.night_actions:
                return False
        return True

    def resolve_night(room: Room) -> tuple[M.Result, dict]:
        alive_ids = {s.uid for s in alive(room)}
        roles = role_of(room)
        counts: dict[int, int] = {}
        for k, tgt in room.night_picks.items():
            if k in alive_ids and tgt in alive_ids:
                counts[tgt] = counts.get(tgt, 0) + 1
        killers_alive = any(s.role == "killer" for s in alive(room))
        if not counts and killers_alive:                  # لم يختر القتلة أحدًا: يختار البوت
            pool = [s.uid for s in alive(room) if s.role != "killer"]
            if pool:
                counts[rng.choice(sorted(pool))] = 1
        kill = None
        if counts:
            top = max(counts.values())
            kill = rng.choice(sorted(u for u, c in counts.items() if c == top))
        protect = {}
        doc = room.night_actions.get("doctor")
        if doc in alive_ids and any(s.role == "doctor" and s.alive for s in room.seats.values()):
            protect["doctor"] = doc
        check = room.night_actions.get("detective")
        res = M.resolve_night(roles, alive_ids, M.Night(kill=kill, protect=protect, check=check))
        room.last_protect = doc
        return res, roles

    @r.callback_query(F.data.regexp(r"^mo:n:\d+:(killer|doctor|detective):\d+$"))
    async def cb_night(c: CallbackQuery):
        _, _, rid, role, tid = c.data.split(":")
        room = rooms.get(int(rid))
        uid, L = c.from_user.id, L_(c.from_user.id)
        if not room or room.state != "night":
            await c.answer(t(L, "mo_late"), show_alert=True)
            return
        me = room.seats.get(uid)
        if not me or not me.alive or me.role != role:
            await c.answer(t(L, "mo_not_yours"), show_alert=True)
            return
        target = room.seats.get(int(tid))
        if not target or not target.alive:
            await c.answer(t(L, "mo_bad_target"), show_alert=True)
            return
        if role == "killer":
            if target.role == "killer":
                await c.answer(t(L, "mo_bad_target"), show_alert=True)
                return
            room.night_picks[uid] = target.uid
        elif role == "doctor":
            if target.uid == room.last_protect:
                await c.answer(t(L, "mf_protect_repeat"), show_alert=True)
                return
            room.night_actions["doctor"] = target.uid
        else:
            if target.uid == uid:
                await c.answer(t(L, "mo_bad_target"), show_alert=True)
                return
            room.night_actions["detective"] = target.uid
            team = t(L, "mf_team_" + M.ROLES[target.role][1])
            await c.answer(t(L, "mo_detect_alert", name=target.name, team=team), show_alert=True)
            return
        await c.answer(t(L, "mo_picked"))

    # ── النقاش ───────────────────────────────────────────
    async def talk(bot: Bot, room: Room) -> None:
        room.state = "talk"
        await broadcast(bot, room, "mo_talk", r=room.round, s=TALK_SECS)
        deadline = time.monotonic() + TALK_SECS
        while time.monotonic() < deadline:
            await asyncio.sleep(0.5)
        room.state = "vote"

    @r.message(F.text)
    async def on_talk(m: Message):
        text = m.text or ""
        uid = m.from_user.id
        room = rooms.get(user_room.get(uid, -1))
        if text.startswith("/") or not room or room.state != "talk":
            raise SkipHandler()
        L = L_(uid)
        me = room.seats[uid]
        if not me.alive:
            await m.answer(t(L, "mo_dead_talk"))
            return
        now = time.monotonic()
        if now - room.last_sent.get(uid, 0) < MSG_GAP:
            await m.answer(t(L, "mo_talk_rate"))
            return
        if len(text) > MSG_MAX:
            await m.answer(t(L, "mo_talk_long", n=MSG_MAX))
            return
        room.last_sent[uid] = now
        for s in list(room.seats.values()):
            await say(m.bot, s.uid, t(L_(s.uid), "mo_say", name=esc(me.name), text=esc(text)))

    # ── التصويت ──────────────────────────────────────────
    async def vote(bot: Bot, room: Room) -> int | None:
        room.state = "vote"
        room.votes = {}
        alive_now = alive(room)
        await broadcast(bot, room, "mo_vote_start", alive_only=True, s=VOTE_SECS)
        for s in alive_now:
            L = L_(s.uid)
            rows = [[btn(x.name[:22], f"mo:v:{room.rid}:{x.uid}")] for x in alive_now if x.uid != s.uid]
            rows.append([btn(t(L, "mf_skip"), f"mo:v:{room.rid}:0")])
            await say(bot, s.uid, t(L, "mo_vote_pick"), kb(*rows))
        deadline = time.monotonic() + VOTE_SECS
        while time.monotonic() < deadline and len(room.votes) < len(alive_now):
            await asyncio.sleep(0.5)
        ids = {s.uid for s in alive_now}
        ballots = {v: tgt for v, tgt in room.votes.items() if tgt}
        out = M.vote(ids, ballots)
        for uid in ids:
            room.votes.setdefault(uid, uid)                 # من لم يصوّت: صوته على نفسه
        return out

    @r.callback_query(F.data.regexp(r"^mo:v:\d+:\d+$"))
    async def cb_vote(c: CallbackQuery):
        _, _, rid, tid = c.data.split(":")
        room = rooms.get(int(rid))
        uid, L = c.from_user.id, L_(c.from_user.id)
        if not room or room.state != "vote":
            await c.answer(t(L, "mo_late"), show_alert=True)
            return
        me = room.seats.get(uid)
        if not me or not me.alive:
            await c.answer(t(L, "mo_not_alive"), show_alert=True)
            return
        tgt = int(tid)
        if tgt and (tgt not in room.seats or not room.seats[tgt].alive or tgt == uid):
            await c.answer(t(L, "mo_bad_target"), show_alert=True)
            return
        room.votes[uid] = tgt
        await c.answer(t(L, "mf_voted"))

    # ── سير اللعبة ───────────────────────────────────────
    async def run_room(bot: Bot, room: Room) -> None:
        try:
            await broadcast(bot, room, "mo_started", n=len(room.seats))
            await send_roles(bot, room)
            while True:
                room.round += 1
                await night(bot, room)
                res, _roles = resolve_night(room)
                if res.victim is not None:
                    room.seats[res.victim].alive = False
                    await broadcast(bot, room, "mf_morning_dead", name=esc(room.seats[res.victim].name))
                elif res.saved:
                    await broadcast(bot, room, "mf_morning_saved")
                else:
                    await broadcast(bot, room, "mf_morning_quiet")
                if _finished(room):
                    return await finish(bot, room)
                await talk(bot, room)
                out = await vote(bot, room)
                if out is not None:
                    room.seats[out].alive = False
                    await broadcast(bot, room, "mf_executed", name=esc(room.seats[out].name))
                else:
                    await broadcast(bot, room, "mf_no_exec")
                if _finished(room):
                    return await finish(bot, room)
        except Exception:  # noqa: BLE001
            log.exception("online mafia room %s failed", room.rid)
        finally:
            for uid in room.seats:
                user_room.pop(uid, None)
            room.state = "done"
            rooms.pop(room.rid, None)

    def _finished(room: Room) -> bool:
        return M.winner(role_of(room), {s.uid for s in alive(room)}) is not None

    async def finish(bot: Bot, room: Room) -> None:
        w = M.winner(role_of(room), {s.uid for s in alive(room)})
        reveal = "\n".join(f"• {esc(s.name)}: {ICON[s.role]} {t(L_(s.uid), 'mf_r_' + s.role)}"
                           for s in room.seats.values())
        for s in room.seats.values():
            key = "mo_end_town" if w == M.TOWN else "mo_end_mafia"
            await say(bot, s.uid, t(L_(s.uid), key) + "\n━━━━━━━━━━━━━━━━\n" + reveal)
        room.state = "done"

    # ── قائمة الأونلاين: الزر يُضاف من online.py ────────
    return r
