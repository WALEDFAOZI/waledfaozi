"""لعبة المافيا بطابع أنمي داخل المجموعات والقنوات. المنطق النقي في mafia.py، وهنا التدفق مع تليجرام.

- الرسالة الحيّة الواحدة تُعدَّل (الانتظار ← الليل ← النهار)، فلا تتراكم الرسائل.
- كل دور يتلقى رسالته الخاصة مع أزرار ما يجب فعله. النهار يُحسم بالتصويت في المنشور العام.
- الأدوار سرّية حتى نهاية اللعبة.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message, ReplyParameters

from . import mafia as M
from . import progress
from .bot import btn, chan_row, esc, kb
from .ctx import Ctx
from . import live
from .links import back_rows, msg_rows, open_private_rows, with_rows
from .texts import t
from .thread_anchor import anchor_id

log = logging.getLogger(__name__)

LOBBY_SECS = 150
NIGHT_SECS = 60
DAY_SECS = 90
MAX_ROUNDS = 15
QUIET_ROUNDS = 3        # جولات متتالية بلا قتل ولا طرد، ثم يختار النظام لاعبًا عشوائيًا للخروج
COOLDOWN_SECS = 60
EDIT_GAP = 3.0
GROUP_TYPES = {"group", "supergroup"}
SPECIAL_ORDER = ["detective", "doctor", "guard", "joker"]
ICON = {"killer": "🔪", "citizen": "🧑", "detective": "🔍", "doctor": "🩺", "guard": "🛡", "joker": "🃏"}


@dataclass
class Player:
    uid: int
    name: str
    alive: bool = True
    role: str | None = None


@dataclass
class Game:
    gid: int
    chat_id: int
    scope: str                       # group | channel
    host_id: int
    host_name: str
    lang: str
    reply_to: int | None = None
    thread: int | None = None
    killers: int = 1
    specials: list = field(default_factory=list)
    players: dict = field(default_factory=dict)
    state: str = "lobby"             # lobby | night | day | done
    live: int | None = None
    round: int = 0
    night_picks: dict = field(default_factory=dict)     # قاتل -> هدف
    night_actions: dict = field(default_factory=dict)   # doctor/guard -> هدف
    acted: set = field(default_factory=set)             # الأدوار غير القاتلة التي تصرّفت هذه الليلة
    votes: dict = field(default_factory=dict)
    task: asyncio.Task | None = None
    dirty: bool = True
    start_now: bool = False
    me: str = ""                    # اسم البوت (لرابط الانضمام)
    cfg_msg: int | None = None       # رسالة إعدادات المضيف في الخاص
    auto: bool = True                # الأدوار تلقائية حسب العدد (تنطفئ عند أي تعديل يدوي)
    lobby_secs: int = LOBBY_SECS     # أوقات قابلة للتعديل من الخاص
    night_secs: int = NIGHT_SECS
    day_secs: int = DAY_SECS
    day_mid: int | None = None        # رسالة التصويت الحالية (تُحدَّث مع كل صوت)
    day_text: str = ""
    quiet: int = 0                    # عدّاد الجولات المتتالية بلا موت
    day_markup: object = None


games: dict[int, Game] = {}
cooldown: dict[int, float] = {}
counter = [0]


def roles_line(g: Game, L: str) -> str:
    parts = [f"🔪 {t(L, 'mf_killers')}: {g.killers}"] + [f"{ICON[r]} {t(L, 'mf_r_' + r)}" for r in g.specials]
    return " · ".join(parts)


def alive_players(g: Game) -> list[Player]:
    return [p for p in g.players.values() if p.alive]


def night_complete(g: Game) -> bool:
    for k in alive_players(g):
        if k.role == "killer" and k.uid not in g.night_picks:
            return False
    for p in alive_players(g):
        if p.role in ("doctor", "guard", "detective") and p.uid not in g.acted:
            return False
    return True


def build_mafia_router(ctx: Ctx) -> Router:
    db, rng = ctx.db, ctx.rng
    root = Router(name="mafia")
    msgs = Router(name="mafia_msgs")
    msgs.message.filter(F.chat.type.in_(GROUP_TYPES))
    cbs = Router(name="mafia_cbs")
    cbs.callback_query.filter(F.message.chat.type.in_(GROUP_TYPES | {"channel"}))
    pm = Router(name="mafia_pm")
    pm.callback_query.filter(F.message.chat.type == "private")

    # ── الإرسال ───────────────────────────────────────────
    async def send(bot: Bot, g: Game, text: str, markup=None) -> int | None:
        """الرسالة الحيّة الوحيدة للعبة: تبدأ بلافتة وتُعدَّل بعد ذلك."""
        return await live.send(bot, g.chat_id, text, markup, lang=g.lang,
                               reply_to=g.reply_to if g.scope == "group" else None,
                               thread=g.thread if g.scope == "group" else None)

    async def show(bot: Bot, g: Game, text: str, markup=None) -> int | None:
        """كل مرحلة رسالة جديدة في المجموعات. في القنوات تُعدَّل رسالة واحدة (لتفادي الإغراق)."""
        if g.scope == "channel" and g.live is not None:
            await live.edit(bot, g.chat_id, g.live, text, markup)
            return g.live
        mid = await send(bot, g, text, markup)
        if g.live is None:
            g.live = mid
        return mid

    async def lobby_edit(bot: Bot, g: Game, text: str, markup=None) -> None:
        """اللوبي وحده يُعدَّل في مكانه: يعرض المنضمين والعدّاد."""
        if g.live is not None:
            await live.edit(bot, g.chat_id, g.live, text, markup)

    async def dm(bot: Bot, uid: int, text: str, markup=None) -> bool:
        try:
            await bot.send_message(uid, text, parse_mode="HTML", reply_markup=markup)
            return True
        except TelegramAPIError:
            return False

    async def can_control(bot: Bot, g: Game, uid: int) -> bool:
        if uid == g.host_id or ctx.is_admin(uid):
            return True
        if g.scope == "group":
            try:
                m = await bot.get_chat_member(g.chat_id, uid)
                return m.status in ("creator", "administrator")
            except TelegramAPIError:
                return False
        return False

    # ── النصوص ────────────────────────────────────────────
    def names(g: Game, alive_only: bool = False) -> str:
        ps = [p for p in g.players.values() if p.alive or not alive_only]
        return "، ".join(esc(p.name) for p in ps) or "—"

    def lobby_text(g: Game, left: int) -> str:
        L = g.lang
        roles = roles_line(g, L)
        return "\n".join([
            t(L, "mf_title"), "",
            roles,
            t(L, "mf_players", n=len(g.players), names=names(g)),
            t(L, "mf_left", s=max(0, left), min=M.MIN_PLAYERS),
            "", t(L, "mf_howto"),
        ])

    def lobby_markup(g: Game):
        L = g.lang
        join_url = f"https://t.me/{g.me}?start=mf_{g.gid}"
        return kb([btn(t(L, "mf_join"), url=join_url), btn(t(L, "mf_leave"), f"mf:l:{g.gid}")], *chan_row(L))

    def config_text(g: Game) -> str:
        L = g.lang
        return "\n".join([t(L, "mf_cfg_title"), "", roles_line(g, L), "", t(L, "mf_cfg_hint")])

    # حدود الأوقات (ثانية) وخطوة التعديل لكل مرحلة
    TIMES = {"lobby": (30, 600, 30), "night": (15, 300, 15), "day": (15, 300, 15)}

    def times_rows(g: Game) -> list:
        L = g.lang
        val = {"lobby": g.lobby_secs, "night": g.night_secs, "day": g.day_secs}
        rows = []
        for kind in ("lobby", "night", "day"):
            lo, hi, step = TIMES[kind]
            rows.append([btn("➖", f"mf:tm:{g.gid}:{kind}:-"),
                         btn(t(L, f"mf_tm_{kind}", s=val[kind]), f"mf:tm:{g.gid}:{kind}:0"),
                         btn("➕", f"mf:tm:{g.gid}:{kind}:+")])
        return rows

    def config_markup(g: Game):
        L = g.lang
        rows = [[btn(t(L, "mf_auto_btn") + (" ✅" if g.auto else ""), f"mf:a:{g.gid}")]]
        rows += [[btn("➖", f"mf:k:{g.gid}:-"), btn(t(L, "mf_killers_btn", k=g.killers), f"mf:k:{g.gid}:0"),
                  btn("➕", f"mf:k:{g.gid}:+")]]
        sp = [btn(("✅ " if r in g.specials else "") + t(L, "mf_r_" + r), f"mf:r:{g.gid}:{r}") for r in SPECIAL_ORDER]
        rows += [sp[:2], sp[2:]]
        rows += times_rows(g)
        rows.append([btn(t(L, "mf_start"), f"mf:s:{g.gid}"), btn(t(L, "mf_cancel"), f"mf:x:{g.gid}")])
        return kb(*rows)

    async def push_config(bot: Bot, g: Game) -> None:
        """رسالة الإعدادات للمضيف في الخاص فقط (تُعدَّل ولا تتراكم)."""
        back = await back_rows(bot, g.chat_id, g.live, g.lang)
        if g.cfg_msg:
            try:
                await bot.edit_message_text(config_text(g), chat_id=g.host_id, message_id=g.cfg_msg,
                                            parse_mode="HTML", reply_markup=with_rows(config_markup(g), back))
                return
            except TelegramAPIError:
                pass
        try:
            m = await bot.send_message(g.host_id, config_text(g), parse_mode="HTML", reply_markup=with_rows(config_markup(g), back))
            g.cfg_msg = m.message_id
        except TelegramAPIError:
            await show(bot, g, t(g.lang, "mf_host_dm_missing", me=g.me), None)

    def roles_line_placeholder():  # pragma: no cover
        return ""

    # ── الانتظار ──────────────────────────────────────────
    async def lobby_phase(bot: Bot, g: Game) -> None:
        start = time.monotonic()
        last = 0.0
        while not g.start_now and g.state == "lobby":
            left = g.lobby_secs - (time.monotonic() - start)     # المضيف قد يزيد الوقت أثناء الانتظار
            if left <= 0:
                return
            if g.dirty and time.monotonic() - last >= EDIT_GAP:
                g.dirty = False
                last = time.monotonic()
                await lobby_edit(bot, g, lobby_text(g, int(left)), lobby_markup(g))
            await asyncio.sleep(0.5)

    # ── الليل ─────────────────────────────────────────────
    async def night_phase(bot: Bot, g: Game) -> None:
        g.state = "night"
        g.round += 1
        g.night_picks, g.night_actions, g.acted = {}, {}, set()
        L = g.lang
        back = await back_rows(bot, g.chat_id, g.live, L)               # زر العودة إلى رسالة اللعبة
        alive = alive_players(g)
        for p in alive:
            if p.role == "killer":
                opts = [q for q in alive if q.role != "killer"]
                rows = [[btn(q.name[:24], f"mf:n:{g.gid}:killer:{q.uid}")] for q in opts]
            elif p.role == "doctor":
                rows = [[btn(q.name[:24], f"mf:n:{g.gid}:doctor:{q.uid}")] for q in alive]
            elif p.role in ("guard", "detective"):
                rows = [[btn(q.name[:24], f"mf:n:{g.gid}:{p.role}:{q.uid}")] for q in alive if q.uid != p.uid]
            else:
                continue
            await dm(bot, p.uid, t(L, f"mf_n_{p.role}"), kb(*rows, *back))
        await show(bot, g, t(L, "mf_night_live", r=g.round, s=g.night_secs, n=len(alive), names=names(g, True)),
                   kb(*await open_private_rows(bot, L)))
        deadline = time.monotonic() + g.night_secs
        while time.monotonic() < deadline and g.state == "night" and not night_complete(g):
            await asyncio.sleep(0.5)

    def resolve_night(g: Game):
        roles = {p.uid: p.role for p in g.players.values()}
        alive = {p.uid for p in alive_players(g)}
        counts: dict[int, int] = {}
        for tgt in g.night_picks.values():
            counts[tgt] = counts.get(tgt, 0) + 1
        kill = None
        if counts:
            top = max(counts.values())
            kill = rng.choice(sorted(u for u, c in counts.items() if c == top))
        protect = {r: g.night_actions[r] for r in ("doctor", "guard") if r in g.night_actions}
        return M.resolve_night(roles, alive, M.Night(kill=kill, protect=protect))

    # ── النهار ────────────────────────────────────────────
    async def day_phase(bot: Bot, g: Game) -> int | None:
        g.state = "day"
        g.votes = {}
        L = g.lang
        alive = alive_players(g)
        btns = [[btn(f"🗳 {p.name[:22]}", f"mf:v:{g.gid}:{p.uid}")] for p in alive]
        btns.append([btn(t(L, "mf_skip"), f"mf:v:{g.gid}:0")])
        g.day_text = t(L, "mf_day_live", r=g.round, s=g.day_secs, names=names(g, True))
        g.day_markup = kb(*btns)
        g.day_mid = await show(bot, g, g.day_text, g.day_markup)
        await notify_vote_start(bot, g, alive)
        deadline = time.monotonic() + g.day_secs
        while time.monotonic() < deadline and g.state == "day":
            if all(p.uid in g.votes for p in alive_players(g)):
                break
            await asyncio.sleep(0.5)
        missed = [p for p in alive_players(g) if p.uid not in g.votes]
        if missed:                                          # من لم يصوّت: صوته يُحسب على نفسه (لا يطرد أحدًا)
            names_missed = "، ".join(esc(p.name) for p in missed)
            await show(bot, g, t(L, "mf_self_votes", names=names_missed), None)
        ballots = {v: tgt for v, tgt in g.votes.items() if tgt}
        return M.vote({p.uid for p in alive_players(g)}, ballots)

    async def notify_vote_start(bot: Bot, g: Game, alive: list) -> None:
        """رسالة خاصة لكل حي فيها زر يفتح رسالة التصويت مباشرة (في التعليقات إن كانت اللعبة فيها)."""
        for p in alive:
            Lp = db.get_lang(p.uid)
            rows = await msg_rows(bot, g.chat_id, g.day_mid, "btn_go_vote", Lp)
            if not rows:
                return
            try:
                await bot.send_message(p.uid, t(Lp, "mf_vote_dm"), parse_mode="HTML", reply_markup=kb(*rows))
            except TelegramAPIError:
                pass                                        # لم يبدأ البوت بالخاص

    # ── إعلانات ───────────────────────────────────────────
    async def announce_morning(bot: Bot, g: Game, res: M.Result) -> None:
        L = g.lang
        if res.victim is not None:
            text = t(L, "mf_morning_dead", name=esc(g.players[res.victim].name))
        elif res.saved:
            text = t(L, "mf_morning_saved")
        else:
            text = t(L, "mf_morning_quiet")
        await show(bot, g, text, None)

    async def finish(bot: Bot, g: Game, w: str | None) -> None:
        L = g.lang
        g.state = "done"
        if w == M.TOWN:
            won = {p.uid for p in g.players.values() if p.role not in ("killer", "joker")}
        elif w == M.MAFIA:
            won = {p.uid for p in g.players.values() if p.role == "killer"}
        elif w == M.SOLO:
            won = {p.uid for p in g.players.values() if p.role == "joker"}
        else:
            won = set()
        head = t(L, f"mf_end_{w}") if w else t(L, "mf_end_draw")
        reveal = "\n".join(
            f"{ICON[p.role]} {esc(p.name)} — {t(L, 'mf_r_' + p.role)}{' ✅' if p.uid in won else ''}"
            for p in g.players.values())
        await show(bot, g, t(L, "mf_end", head=head, reveal=reveal, rounds=g.round), kb(*chan_row(L)) or None)
        for p in g.players.values():
            if db.is_admin(p.uid):
                continue
            db.add_group_result(g.chat_id, p.uid, 100 if p.uid in won else 30, "mafia", p.uid in won)
            progress.record(db, p.uid, "group", correct=g.round, won=p.uid in won)

    # ── الحلقة الرئيسية ───────────────────────────────────
    async def run(bot: Bot, g: Game) -> None:
        L = g.lang
        try:
            await lobby_phase(bot, g)
            if g.state != "lobby":
                return
            if len(g.players) < M.MIN_PLAYERS:
                await show(bot, g, t(L, "mf_too_few", min=M.MIN_PLAYERS), None)
                return
            if g.auto:
                g.killers, g.specials = M.auto_config(len(g.players))
            cfg = M.Config(killers=g.killers, specials=list(g.specials))
            try:
                roles = M.assign(list(g.players), cfg, rng)
            except M.ConfigError as e:
                await show(bot, g, t(L, "mf_config_err", e=esc(str(e))), None)
                return
            for uid, role in roles.items():
                g.players[uid].role = role
            failed = []
            for p in g.players.values():
                ok = await dm(bot, p.uid, t(L, "mf_role_dm", icon=ICON[p.role], role=t(L, "mf_r_" + p.role),
                                            desc=t(L, "mf_desc_" + p.role),
                                            team=t(L, "mf_team_" + M.ROLES[p.role][1])))
                if not ok:
                    failed.append(esc(p.name))
            if failed:
                await show(bot, g, t(L, "mf_dm_fail", names="، ".join(failed)), None)
                return
            roles_map = {p.uid: p.role for p in g.players.values()}
            while True:
                await night_phase(bot, g)
                res = resolve_night(g)
                if res.victim is not None:
                    g.players[res.victim].alive = False
                await announce_morning(bot, g, res)
                if res.detective is None:
                    pass
                w = M.winner(roles_map, {p.uid for p in alive_players(g)})
                if w:
                    await finish(bot, g, w)
                    return
                out = await day_phase(bot, g)
                last = None
                if out is not None:
                    g.players[out].alive = False
                    last = g.players[out].role
                    await show(bot, g, t(L, "mf_executed", name=esc(g.players[out].name)), None)
                else:
                    await show(bot, g, t(L, "mf_no_exec"), None)
                if res.victim is not None or out is not None:
                    g.quiet = 0
                else:
                    g.quiet += 1
                    if g.quiet >= QUIET_ROUNDS and alive_players(g):
                        pick = rng.choice(sorted(p.uid for p in alive_players(g)))
                        g.players[pick].alive = False
                        g.quiet = 0
                        await show(bot, g, t(L, "mf_quiet_death", name=esc(g.players[pick].name)), None)
                w = M.winner(roles_map, {p.uid for p in alive_players(g)}, last_voted=last)
                if w:
                    await finish(bot, g, w)
                    return
                if g.round >= MAX_ROUNDS:
                    await finish(bot, g, None)
                    return
        except asyncio.CancelledError:
            await show(bot, g, t(L, "mf_stopped"), None)
            raise
        except Exception:  # noqa: BLE001
            log.exception("mafia crashed in %s", g.chat_id)
        finally:
            g.state = "done"
            if games.get(g.chat_id) is g:
                games.pop(g.chat_id, None)
            cooldown[g.chat_id] = time.monotonic()

    def new_game(chat_id: int, scope: str, host_id: int, host_name: str, reply_to, thread, lang: str) -> Game:
        counter[0] += 1
        return Game(gid=counter[0], chat_id=chat_id, scope=scope, host_id=host_id, host_name=host_name,
                    lang=lang, reply_to=reply_to, thread=thread,
                    lobby_secs=LOBBY_SECS, night_secs=NIGHT_SECS, day_secs=DAY_SECS)

    async def open_lobby(bot: Bot, g: Game) -> bool:
        games[g.chat_id] = g
        g.me = (await bot.get_me()).username
        g.live = await send(bot, g, lobby_text(g, g.lobby_secs), lobby_markup(g))
        if g.live is None:
            games.pop(g.chat_id, None)
            return False
        await push_config(bot, g)
        g.task = asyncio.create_task(run(bot, g))
        return True

    def busy_or_cool(chat_id: int) -> str | None:
        cur = games.get(chat_id)
        if cur and cur.state != "done":
            return "busy"
        if time.monotonic() - cooldown.get(chat_id, -1e9) < COOLDOWN_SECS:
            return "cool"
        return None

    def get_game(c: CallbackQuery, gid: int) -> Game | None:
        g = games.get(c.message.chat.id)
        return g if g and g.gid == gid and g.state != "done" else None

    # ── الأوامر ───────────────────────────────────────────
    @msgs.message(Command("mafia"))
    async def cmd_mafia(m: Message):
        L = db.group_lang(m.chat.id)
        if not m.from_user or m.sender_chat is not None:
            return
        db.touch_group(m.chat.id, m.chat.title)
        why = busy_or_cool(m.chat.id)
        if why:
            await m.reply(t(L, "mf_busy" if why == "busy" else "mf_cool"))
            return
        db.upsert_user(m.from_user.id, m.from_user.full_name)
        thread = m.message_thread_id if getattr(m, "is_topic_message", False) else None
        g = new_game(m.chat.id, "group", m.from_user.id, m.from_user.full_name, anchor_id(m), thread, L)
        await open_lobby(m.bot, g)

    @cbs.callback_query(F.data == "mf:new")
    async def cb_new_from_menu(c: CallbackQuery):
        """زر المافيا من قائمة /play في المجموعة."""
        L = db.group_lang(c.message.chat.id)
        why = busy_or_cool(c.message.chat.id)
        if why:
            await c.answer(t(L, "mf_busy" if why == "busy" else "mf_cool"), show_alert=True)
            return
        await c.answer()
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        g = new_game(c.message.chat.id, "group", c.from_user.id, c.from_user.full_name, anchor_id(c.message),
                     c.message.message_thread_id if getattr(c.message, "is_topic_message", False) else None, L)
        await open_lobby(c.bot, g)

    # ── أزرار الانتظار والتحكم ────────────────────────────
    @cbs.callback_query(F.data.regexp(r"^mf:l:\d+$"))
    async def cb_leave(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        g = get_game(c, int(c.data.split(":")[2]))
        if not g:
            await c.answer(t(L, "mf_gone"), show_alert=True)
            return
        uid = c.from_user.id
        if uid not in g.players:
            await c.answer(t(L, "mf_not_in"))
            return
        if g.state == "lobby":
            g.players.pop(uid)
            g.dirty = True
            await c.answer(t(L, "mf_left_toast"))
            return
        g.players[uid].alive = False                 # الانسحاب أثناء اللعب يُحسب طردًا
        await c.answer(t(L, "mf_quit_toast"))
        await show(c.bot, g, t(L, "mf_quit_live", name=esc(g.players[uid].name)), None)

    # ── الانضمام: رابط يفتح الخاص مع البوت (يثبت أن اللاعب فتح البوت) ──
    @pm.message(CommandStart(deep_link=True, magic=F.args.startswith("mf_")))
    async def on_join_start(m: Message):
        L = db.get_lang(m.from_user.id)
        db.upsert_user(m.from_user.id, m.from_user.full_name)
        try:
            gid = int((m.text or "").split("mf_", 1)[1].split()[0])
        except (IndexError, ValueError):
            await m.answer(t(L, "mf_gone"))
            return
        g = next((x for x in games.values() if x.gid == gid), None)
        if not g or g.state != "lobby":
            await m.answer(t(L, "mf_gone"))
            return
        uid = m.from_user.id
        if uid in g.players:
            await m.answer(t(L, "mf_already"))
            return
        if len(g.players) >= M.MAX_PLAYERS:
            await m.answer(t(L, "mf_full"))
            return
        g.players[uid] = Player(uid, m.from_user.full_name)
        g.dirty = True
        await m.answer(t(L, "mf_joined_dm"), parse_mode="HTML")

    # ── إعدادات المضيف في الخاص ──────────────────────────
    def host_game(c: CallbackQuery, gid: int) -> Game | None:
        g = next((x for x in games.values() if x.gid == gid), None)
        return g if g and g.state == "lobby" and c.from_user.id == g.host_id else None

    @pm.callback_query(F.data.regexp(r"^mf:k:\d+:[-+0]$"))
    async def cb_killers(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        _, _, gid, op = c.data.split(":")
        g = host_game(c, int(gid))
        if not g:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        g.auto = False
        if op == "+":
            g.killers = min(g.killers + 1, max(1, len(g.players)))
        elif op == "-":
            g.killers = max(1, g.killers - 1)
        g.dirty = True
        await c.answer()
        await push_config(c.bot, g)

    @pm.callback_query(F.data.regexp(r"^mf:r:\d+:(detective|doctor|guard|joker)$"))
    async def cb_roles(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        _, _, gid, role = c.data.split(":")
        g = host_game(c, int(gid))
        if not g:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        g.auto = False
        if role in g.specials:
            g.specials.remove(role)
        else:
            g.specials.append(role)
        g.dirty = True
        await c.answer()
        await push_config(c.bot, g)

    @pm.callback_query(F.data.regexp(r"^mf:a:\d+$"))
    async def cb_auto(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        g = host_game(c, int(c.data.split(":")[2]))
        if not g:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        g.auto = True
        g.killers, g.specials = M.auto_config(max(M.MIN_PLAYERS, len(g.players)))
        g.dirty = True
        await c.answer()
        await push_config(c.bot, g)

    @pm.callback_query(F.data.regexp(r"^mf:tm:\d+:(lobby|night|day):[-+0]$"))
    async def cb_times(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        _, _, gid, kind, op = c.data.split(":")
        g = host_game(c, int(gid))
        if not g:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        lo, hi, step = TIMES[kind]
        attr = {"lobby": "lobby_secs", "night": "night_secs", "day": "day_secs"}[kind]
        if op != "0":
            cur = getattr(g, attr)
            setattr(g, attr, max(lo, min(hi, cur + (step if op == "+" else -step))))
        g.dirty = True
        await c.answer()
        if op != "0":
            await push_config(c.bot, g)

    @pm.callback_query(F.data.regexp(r"^mf:s:\d+$"))
    async def cb_start(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        g = host_game(c, int(c.data.split(":")[2]))
        if not g:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        try:
            if g.auto:
                g.killers, g.specials = M.auto_config(len(g.players))
            M.Config(killers=g.killers, specials=list(g.specials)).validate(len(g.players))
        except M.ConfigError as e:
            await c.answer(str(e)[:190], show_alert=True)
            return
        g.start_now = True
        await c.answer(t(L, "mf_starting"))

    @pm.callback_query(F.data.regexp(r"^mf:x:\d+$"))
    async def cb_cancel(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        g = next((x for x in games.values() if x.gid == int(c.data.split(":")[2])), None)
        if not g or c.from_user.id != g.host_id:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        await c.answer()
        if g.task:
            g.task.cancel()

    @cbs.callback_query(F.data.regexp(r"^mf:v:\d+:\d+$"))
    async def cb_vote(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        _, _, gid, tgt = c.data.split(":")
        g = get_game(c, int(gid))
        if not g or g.state != "day":
            await c.answer(t(L, "mf_late"), show_alert=True)
            return
        voter = g.players.get(c.from_user.id)
        if not voter or not voter.alive:
            await c.answer(t(L, "mf_not_alive"), show_alert=True)
            return
        target = int(tgt)
        if target and (target not in g.players or not g.players[target].alive or target == voter.uid):
            await c.answer(t(L, "mf_bad_target"), show_alert=True)
            return
        g.votes[voter.uid] = target
        await c.answer(t(L, "mf_voted"))
        if g.day_mid and g.day_text:
            alive = alive_players(g)
            done = sum(1 for p in alive if p.uid in g.votes)
            status = t(L, "mf_vote_status", name=esc(voter.name), done=done, total=len(alive), left=len(alive) - done)
            status += "\n" + t(L, "mf_vote_note")
            await live.edit(c.bot, g.chat_id, g.day_mid, g.day_text + "\n\n" + status, g.day_markup)

    @cbs.callback_query(F.data.regexp(r"^mf:i:\d+$"))
    async def cb_info(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        await c.answer(t(L, "mf_info_toast")[:190], show_alert=True)

    # ── الخاص: أفعال الليل ────────────────────────────────
    @pm.callback_query(F.data.regexp(r"^mf:n:\d+:(killer|doctor|guard|detective):\d+$"))
    async def cb_night(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        _, _, gid, role, tgt = c.data.split(":")
        g = next((x for x in games.values() if x.gid == int(gid)), None)     # games مفاتيحها معرّف المجموعة
        if not g or g.state != "night":
            await c.answer(t(L, "mf_late"), show_alert=True)
            return
        p = g.players.get(c.from_user.id)
        if not p or not p.alive or p.role != role:
            await c.answer(t(L, "mf_not_yours"), show_alert=True)
            return
        target = int(tgt)
        tp = g.players.get(target)
        if not tp or not tp.alive or target == p.uid or (role == "killer" and tp.role == "killer"):
            if not (role == "doctor" and tp and tp.alive and target == p.uid):
                await c.answer(t(L, "mf_bad_target"), show_alert=True)
                return
        if role == "killer":
            g.night_picks[p.uid] = target
        else:
            g.night_actions[role] = target
            g.acted.add(p.uid)
        if role == "detective":
            team = t(L, "mf_team_" + M.ROLES[tp.role][1])
            await c.answer(t(L, "mf_pick_saved", name=esc(tp.name)[:20]), show_alert=True)
            await c.message.answer(t(L, "mf_detect_res", name=esc(tp.name), team=team), parse_mode="HTML")
            return
        await c.answer(t(L, "mf_pick_saved", name=esc(tp.name)[:20]), show_alert=True)

    # ── الخاص: بدء اللعبة في قناة يملكها ───────────────────
    @pm.callback_query(F.data == "mf:cs")
    async def cb_pick_channel(c: CallbackQuery):
        await c.answer()
        L = db.get_lang(c.from_user.id)
        rows = [[btn(f"📢 {title or chat_id}", f"mf:cs:{chat_id}")] for chat_id, title in db.user_channels(c.from_user.id)[:8]]
        if not rows:
            await c.message.answer(t(L, "mf_no_channels"))
            return
        await c.message.answer(t(L, "mf_pick_channel"), reply_markup=kb(*rows))

    @pm.callback_query(F.data.regexp(r"^mf:cs:-?\d+$"))
    async def cb_start_in_channel(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        chat_id = int(c.data.split(":")[2])
        if db.channel_owner(chat_id) != c.from_user.id:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        why = busy_or_cool(chat_id)
        if why:
            await c.answer(t(L, "mf_busy" if why == "busy" else "mf_cool"), show_alert=True)
            return
        await c.answer()
        title = next((tt for cid, tt in db.user_channels(c.from_user.id) if cid == chat_id), None)
        g = new_game(chat_id, "channel", c.from_user.id, title or "القناة", None, None, db.group_lang(chat_id))
        if await open_lobby(c.bot, g):
            await c.message.answer(t(L, "mf_channel_started"))

    root.include_router(msgs)
    root.include_router(cbs)
    root.include_router(pm)
    return root
