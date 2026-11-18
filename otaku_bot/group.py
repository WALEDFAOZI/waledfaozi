"""ألعاب المجموعات: يُضاف البوت لمجموعة، يكتب أحدهم /play، تفتح غرفة انتظار 30 ثانية، ثم تبدأ الأسئلة بعدّاد.

قواعد ثابتة:
• كل رسالة جديدة يرسلها البوت في المجموعة تكون «رد» على رسالة صاحب الأمر (مع دعم المواضيع Topics).
• المرسل باسم قناة أو كأدمن مخفي يُسجَّل باسم القناة/المجموعة. الأدمن/المالك يظهر «مجهول 🎭» ولا يدخل لوحات الترتيب.
• تليجرام يحدّ رسائل البوت (~20/دقيقة لكل مجموعة): لا عدّاد كل ثانية؛ رسالة لكل سؤال + تعديلان (منتصف الوقت ثم الكشف).
• حالة اللعبة في الذاكرة (تنتهي مع إعادة التشغيل)، أما النتائج فتُحفظ في القاعدة.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message, ReplyParameters

from .bot import btn, esc, kb
from .ctx import Ctx
from .games import load_games, order_rounds, quote_rounds, char_rounds, song_rounds, tf_rounds
from .names import loc, loc_opt
from .quiz import pick_questions, shuffle_options
from .texts import t
from .timeutil import week_start

log = logging.getLogger(__name__)

# قابلة للتعديل (والاختبارات تقلّلها)
LOBBY_SECONDS = 30
Q_SECONDS = 15
PAUSE = 3
MIN_PLAYERS = 2
MAX_PLAYERS = 40
CHAT_COOLDOWN = 30          # بعد انتهاء لعبة في المجموعة
START_COOLDOWN = 45         # لكل من يبدأ ألعابًا
ANON_ADMIN_ID = 1087968824  # GroupAnonymousBot
KINDS = ("quiz", "sudden", "tf", "song", "char", "quote", "ord", "images")
CMD_KIND = {"quiz": "quiz", "sudden": "sudden", "tf": "tf", "song": "song", "char": "char", "quote": "quote",
            "order": "ord", "images": "images"}
GROUP_TYPES = {"group", "supergroup"}
ANON = "مجهول 🎭"
LETTERS = ["A", "B", "C", "D"]


@dataclass
class Player:
    id: int
    name: str
    points: int = 0
    alive: bool = True
    correct: int = 0
    out_round: int = 0


@dataclass
class Rnd:
    text: str
    options: list[str]
    answer: int
    photo: str | None = None
    note: str = ""
    tf: bool = False
    html: bool = False          # النص جاهز كـ HTML (لا يُهرَّب ثانية)


@dataclass
class Game:
    gid: int
    chat_id: int
    thread: int | None
    reply_to: int
    host_id: int
    host_name: str
    kind: str
    lang: str
    players: dict = field(default_factory=dict)
    state: str = "lobby"
    lobby_msg: int | None = None
    rounds: list = field(default_factory=list)
    idx: int = -1
    q_msg: int | None = None
    answers: dict = field(default_factory=dict)
    closed: bool = True
    deadline: float = 0.0
    event: asyncio.Event = field(default_factory=asyncio.Event)
    wake: asyncio.Event = field(default_factory=asyncio.Event)
    start_now: bool = False
    dirty: bool = True
    task: asyncio.Task | None = None


def identity(m: Message) -> tuple[int, str]:
    """(المعرّف, الاسم) لصاحب الرسالة: القناة/المجموعة إن كان يرسل باسمها، وإلا المستخدم."""
    if m.sender_chat is not None:
        return m.sender_chat.id, (m.sender_chat.title or "قناة")
    if m.from_user is not None and m.from_user.id == ANON_ADMIN_ID:
        return m.chat.id, (m.chat.title or "المجموعة")
    u = m.from_user
    return (u.id, u.full_name) if u else (0, "؟")


def build_group_router(ctx: Ctx) -> Router:
    r = Router(name="group")
    r.message.filter(F.chat.type.in_(GROUP_TYPES))
    r.callback_query.filter(F.message.chat.type.in_(GROUP_TYPES))
    db, rng = ctx.db, ctx.rng
    games: dict[int, Game] = {}               # chat_id → اللعبة الجارية
    cooldown: dict[int, float] = {}           # chat_id → وقت انتهاء آخر لعبة
    start_at: dict[int, float] = {}           # من بدأ → وقت آخر بدء
    seen: dict[int, dict[int, float]] = {}    # chat_id → أسئلة شوهدت مؤخرًا
    counter = [0]

    # ── أدوات ──────────────────────────────────────────────
    def enabled() -> bool:
        return db.get_setting("grp_enabled", "1") == "1"

    def clean(name: str) -> str:
        return (name or "?").strip()[:24] or "?"

    def shown(uid: int, name: str) -> str:
        return ANON if db.is_admin(uid) else clean(name)

    async def is_group_admin(bot: Bot, chat_id: int, uid: int) -> bool:
        if ctx.is_admin(uid):
            return True
        try:
            m = await bot.get_chat_member(chat_id, uid)
        except TelegramAPIError:
            return False
        return m.status in ("creator", "administrator")

    async def can_control(bot: Bot, g: Game, uid: int) -> bool:
        return uid == g.host_id or await is_group_admin(bot, g.chat_id, uid)

    async def send(bot: Bot, g: Game, text: str, markup=None, photo: str | None = None) -> int | None:
        return await send_to(bot, g.chat_id, g.reply_to, g.thread, text, markup, photo)

    async def send_to(bot: Bot, chat_id: int, reply_to: int, thread: int | None, text: str, markup=None,
                      photo: str | None = None) -> int | None:
        """كل رسالة جديدة في المجموعة = رد على رسالة صاحب الأمر."""
        kw = dict(chat_id=chat_id, reply_parameters=ReplyParameters(message_id=reply_to, allow_sending_without_reply=True),
                  parse_mode="HTML", reply_markup=markup)
        if thread:
            kw["message_thread_id"] = thread
        for attempt in (1, 2):
            try:
                if photo:
                    m = await bot.send_photo(photo=photo, caption=text, **kw)
                else:
                    m = await bot.send_message(text=text, **kw)
                return m.message_id
            except TelegramRetryAfter as e:
                await asyncio.sleep(min(e.retry_after, 10))
            except TelegramBadRequest as e:
                if photo:                                   # صورة معطوبة: نرسل النص فقط
                    photo = None
                    continue
                log.warning("group send failed in %s: %s", chat_id, e)
                return None
            except (TelegramForbiddenError, TelegramAPIError) as e:
                log.warning("group send failed in %s: %s", chat_id, e)
                return None
        return None

    async def edit(bot: Bot, g: Game, mid: int | None, text: str, markup=None, caption: bool = False) -> None:
        if not mid:
            return
        try:
            if caption:
                await bot.edit_message_caption(chat_id=g.chat_id, message_id=mid, caption=text, parse_mode="HTML",
                                               reply_markup=markup)
            else:
                await bot.edit_message_text(text, chat_id=g.chat_id, message_id=mid, parse_mode="HTML", reply_markup=markup)
        except TelegramRetryAfter as e:
            if e.retry_after <= 3:
                await asyncio.sleep(e.retry_after)
        except TelegramAPIError:
            pass                                             # «not modified» أو الرسالة اختفت: لا يهم

    async def reply(m: Message, text: str, markup=None) -> None:
        kw = {"message_thread_id": m.message_thread_id} if getattr(m, "is_topic_message", False) and m.message_thread_id else {}
        try:
            await m.bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=markup,
                                     reply_parameters=ReplyParameters(message_id=m.message_id, allow_sending_without_reply=True),
                                     **kw)
        except TelegramAPIError as e:
            log.warning("group reply failed: %s", e)

    # ── بناء الجولات ───────────────────────────────────────
    def games_data() -> dict:
        data = load_games()
        for _, row in db.extras("tf"):
            data["tf"].append(row)
        return data

    def build_rounds(kind: str, L: str, chat_id: int) -> list[Rnd]:
        hidden = db.game_hidden()
        out: list[Rnd] = []
        if kind in ("quiz", "sudden", "images"):
            pool = [q for q in db.all_questions() if (q.q_en if L == "en" else True)]
            sn = seen.setdefault(chat_id, {})
            if kind == "images":
                imgs = [q for q in pool if q.category == "images" and q.image]
                qs = sorted(rng.sample(imgs, min(10, len(imgs))), key=lambda q: q.difficulty)
            else:
                qs = pick_questions(pool, sn, rng, per_level=3 if kind == "sudden" else 1)
            for q in qs:
                order, cpos = shuffle_options(q, rng)
                opts = q.opts(L)
                photo = (q.image[3:] if q.image.startswith("tg:") else q.image) if q.image else None
                out.append(Rnd(q.text(L), [opts[i] for i in order], cpos, photo))
                sn[q.id] = time.time()
            if len(sn) > 400:
                for k in sorted(sn, key=sn.get)[:150]:
                    sn.pop(k, None)
            return out
        data = games_data()
        if kind == "tf":
            for i in tf_rounds(data, rng, 10, hidden):
                s = data["tf"][i]
                stmt = s[1] if L == "en" else loc(s[0], L)
                out.append(Rnd(stmt, [t(L, "g_true"), t(L, "g_false")], 0 if s[2] else 1,
                               note=("" if s[2] else (s[4] if L == "en" else loc(s[3], L))), tf=True))
        elif kind == "song":
            for rd in song_rounds(data, rng, 10, hidden):
                out.append(Rnd(t(L, "gp_song_q", s=esc(rd["song"])), [loc_opt(o, L) for o in rd["options"]], rd["answer"], html=True))
        elif kind in ("char", "quote"):
            fn = char_rounds if kind == "char" else quote_rounds
            for rd in fn(data, rng, 10, hidden):
                text = loc(rd["text"].get(L) or rd["text"]["ar"], L)
                out.append(Rnd(t(L, f"gp_{kind}_q", s=esc(text)), [loc_opt(o, L) for o in rd["options"]], rd["answer"], html=True))
        elif kind == "ord":
            for rd in order_rounds(data, rng, 8, hidden):
                items = rd["items"]
                first = min(range(len(items)), key=lambda i: items[i]["year"])
                note = " · ".join(f"{loc_opt(i['name'], L)}: {i['year']}" for i in sorted(items, key=lambda i: i["year"]))
                out.append(Rnd(t(L, "gp_ord_q"), [loc_opt(i["name"], L) for i in items], first, note=note, html=True))
        return out

    # ── النصوص ─────────────────────────────────────────────
    def pnames(g: Game, limit: int = 12) -> str:
        names = [esc(p.name) for p in g.players.values()]
        extra = f" +{len(names) - limit}" if len(names) > limit else ""
        return "، ".join(names[:limit]) + extra if names else "—"

    def lobby_text(g: Game, left: int) -> str:
        return t(g.lang, "gp_lobby", kind=t(g.lang, f"gpk_{g.kind}"), host=esc(g.host_name), left=max(0, left),
                 n=len(g.players), names=pnames(g), min=MIN_PLAYERS)

    def lobby_markup(g: Game):
        return kb([btn(t(g.lang, "gp_join"), f"gp:j:{g.gid}")],
                  [btn(t(g.lang, "gp_start_now"), f"gp:s:{g.gid}"), btn(t(g.lang, "gp_cancel"), f"gp:x:{g.gid}")])

    def round_text(g: Game, rnd: Rnd, left: int, answered: int = 0, total: int = 0) -> str:
        n, tot = g.idx + 1, len(g.rounds)
        head = t(g.lang, "gp_round", n=n, t=tot, s=left)
        if answered:
            head += " · " + t(g.lang, "gp_answered", a=answered, n=total)
        q = rnd.text if rnd.html else f"<b>{esc(rnd.text)}</b>"
        if rnd.tf:
            body = q
        else:
            lines = "\n".join(f"<b>{LETTERS[i]})</b> {esc(o)}" for i, o in enumerate(rnd.options))
            body = f"{q}\n\n{lines}"
        return f"{head}\n\n{body}"

    def answer_markup(g: Game, rnd: Rnd):
        if rnd.tf:
            return kb([btn(t(g.lang, "g_true"), f"gp:a:{g.gid}:{g.idx}:0"), btn(t(g.lang, "g_false"), f"gp:a:{g.gid}:{g.idx}:1")])
        btns = [btn(LETTERS[i], f"gp:a:{g.gid}:{g.idx}:{i}") for i in range(len(rnd.options))]
        return kb(btns[:2], btns[2:])

    # ── سير اللعبة ─────────────────────────────────────────
    async def lobby_phase(bot: Bot, g: Game) -> None:
        end = time.monotonic() + LOBBY_SECONDS
        last = 0.0
        while not g.start_now:
            left = end - time.monotonic()
            if left <= 0:
                break
            now = time.monotonic()
            if g.dirty and now - last >= 2.5:
                g.dirty = False
                last = now
                await edit(bot, g, g.lobby_msg, lobby_text(g, int(left + 0.5)), lobby_markup(g))
            g.wake.clear()
            try:
                await asyncio.wait_for(g.wake.wait(), timeout=min(2.5, max(left, 0.02)))
            except asyncio.TimeoutError:
                pass

    async def play_round(bot: Bot, g: Game, rnd: Rnd) -> bool:
        alive = [p for p in g.players.values() if p.alive]
        g.answers = {}
        g.event.clear()
        g.closed = False
        start = time.monotonic()
        g.deadline = start + Q_SECONDS
        mid = await send(bot, g, round_text(g, rnd, Q_SECONDS), answer_markup(g, rnd), rnd.photo)
        if mid is None:
            return False
        g.q_msg = mid
        is_photo = bool(rnd.photo)
        try:
            await asyncio.wait_for(g.event.wait(), timeout=Q_SECONDS / 2)
        except asyncio.TimeoutError:
            await edit(bot, g, mid, round_text(g, rnd, int(Q_SECONDS / 2 + 0.5), len(g.answers), len(alive)),
                       answer_markup(g, rnd), caption=is_photo)
            try:
                await asyncio.wait_for(g.event.wait(), timeout=max(0.01, g.deadline - time.monotonic()))
            except asyncio.TimeoutError:
                pass
        g.closed = True
        # ── الحساب ──
        winners = []
        out_now = []
        for p in alive:
            got = g.answers.get(p.id)
            if got and got[0] == rnd.answer:
                remain = max(0.0, g.deadline - got[1])
                pts = 100 + int(100 * remain / Q_SECONDS)
                p.points += pts
                p.correct += 1
                winners.append((got[1], p, pts))
            elif g.kind == "sudden":
                p.alive = False
                p.out_round = g.idx + 1
                out_now.append(p)
        winners.sort(key=lambda x: x[0])
        right = rnd.options[rnd.answer]
        lines = [t(g.lang, "gp_reveal", n=g.idx + 1, t=len(g.rounds), a=esc(right))]
        if rnd.note:
            lines.append(f"ℹ️ {esc(rnd.note)}")
        if winners:
            medals = ["🥇", "🥈", "🥉"]
            lines.append("")
            lines += [f"{medals[i] if i < 3 else '✅'} {esc(p.name)} +{pts}" for i, (_, p, pts) in enumerate(winners[:5])]
            if len(winners) > 5:
                lines.append(t(g.lang, "gp_and_more", n=len(winners) - 5))
        else:
            lines += ["", t(g.lang, "gp_nobody")]
        if g.kind == "sudden" and out_now:
            lines.append("💀 " + t(g.lang, "gp_out") + ": " + "، ".join(esc(p.name) for p in out_now[:8]))
        await edit(bot, g, mid, "\n".join(lines), None, caption=is_photo)
        return True

    def ranking(g: Game) -> list[Player]:
        ps = list(g.players.values())
        if g.kind == "sudden":
            return sorted(ps, key=lambda p: (p.alive, p.out_round, p.points), reverse=True)
        return sorted(ps, key=lambda p: p.points, reverse=True)

    async def finish(bot: Bot, g: Game) -> None:
        rk = ranking(g)
        if g.kind == "sudden":
            top = rk[0]
            champs = [p for p in rk if (p.alive, p.out_round) == (top.alive, top.out_round)]
        else:
            champs = [p for p in rk if p.points == rk[0].points] if rk and rk[0].points > 0 else []
        medals = ["🥇", "🥈", "🥉"]
        lines = [f"{medals[i] if i < 3 else str(i + 1) + '.'} {esc(p.name)} — <b>{p.points}</b>" for i, p in enumerate(rk[:10])]
        win = ("🏆 " + t(g.lang, "gp_winner", w=" + ".join(esc(p.name) for p in champs))) if champs else t(g.lang, "gp_nowinner")
        await send(bot, g, t(g.lang, "gp_final", w=win, rows="\n".join(lines)),
                   kb([btn(t(g.lang, "gp_top_btn"), "gp:t")]))
        for p in g.players.values():                                       # الأدمن لا يدخل الترتيب
            if not db.is_admin(p.id):
                db.add_group_result(g.chat_id, p.id, p.points, g.kind, p in champs)

    async def run(bot: Bot, g: Game) -> None:
        try:
            await lobby_phase(bot, g)
            if len(g.players) < MIN_PLAYERS:
                await edit(bot, g, g.lobby_msg, t(g.lang, "gp_too_few", min=MIN_PLAYERS), None)
                return
            g.state = "running"
            await edit(bot, g, g.lobby_msg, t(g.lang, "gp_started", n=len(g.players), names=pnames(g)), None)
            g.rounds = build_rounds(g.kind, g.lang, g.chat_id)
            if not g.rounds:
                await send(bot, g, t(g.lang, "gp_no_rounds"))
                return
            for i, rnd in enumerate(g.rounds):
                if g.kind == "sudden" and i > 0 and sum(p.alive for p in g.players.values()) <= 1:
                    break
                g.idx = i
                if not await play_round(bot, g, rnd):
                    return                                                    # لا نستطيع الإرسال (صلاحيات)
                await asyncio.sleep(PAUSE)
            await finish(bot, g)
        except asyncio.CancelledError:
            await send(bot, g, t(g.lang, "gp_stopped"))
            raise
        except Exception:  # noqa: BLE001
            log.exception("group game crashed in %s", g.chat_id)
        finally:
            g.state = "done"
            if games.get(g.chat_id) is g:
                games.pop(g.chat_id, None)
            cooldown[g.chat_id] = time.monotonic()

    # ── الأوامر ────────────────────────────────────────────
    async def open_game(m: Message, kind: str, host: tuple[int, str] | None = None, presser=None) -> None:
        bot = m.bot
        L = db.group_lang(m.chat.id)
        if not enabled():
            await reply(m, t(L, "gp_disabled"))
            return
        hid, hname = host or identity(m)
        starter = presser or m.from_user
        if starter and db.is_admin(starter.id):
            hname = ANON
        db.touch_group(m.chat.id, m.chat.title)
        cur = games.get(m.chat.id)
        if cur and cur.state != "done":
            await reply(m, t(L, "gp_busy"))
            return
        wait = CHAT_COOLDOWN - (time.monotonic() - cooldown.get(m.chat.id, -1e9))
        if wait > 0:
            await reply(m, t(L, "gp_cooldown", s=int(wait) + 1))
            return
        w2 = START_COOLDOWN - (time.monotonic() - start_at.get(hid, -1e9))
        if w2 > 0 and not (starter and ctx.is_admin(starter.id)):
            await reply(m, t(L, "gp_cooldown", s=int(w2) + 1))
            return
        start_at[hid] = time.monotonic()
        counter[0] += 1
        thread = m.message_thread_id if getattr(m, "is_topic_message", False) else None
        g = Game(gid=counter[0], chat_id=m.chat.id, thread=thread, reply_to=m.message_id, host_id=hid, host_name=hname,
                 kind=kind, lang=L)
        games[m.chat.id] = g
        g.lobby_msg = await send(bot, g, lobby_text(g, LOBBY_SECONDS), lobby_markup(g))
        if g.lobby_msg is None:                                               # لا صلاحية للإرسال
            games.pop(m.chat.id, None)
            return
        g.task = asyncio.create_task(run(bot, g))

    @r.message(Command(*CMD_KIND.keys()))
    async def cmd_kind(m: Message, command: CommandObject):
        await open_game(m, CMD_KIND[command.command])

    def menu_markup(L: str):
        rows = [[btn(t(L, f"gpk_{k}"), f"gp:n:{k}")] for k in KINDS]
        return kb(*rows, [btn(t(L, "gp_top_btn"), "gp:t")])

    @r.message(Command("play"))
    async def cmd_play(m: Message):
        L = db.group_lang(m.chat.id)
        if not enabled():
            await reply(m, t(L, "gp_disabled"))
            return
        await reply(m, t(L, "gp_menu"), menu_markup(L))

    @r.callback_query(F.data.regexp(r"^gp:n:(quiz|sudden|tf|song|char|quote|ord|images)$"))
    async def cb_pick(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        cmd = c.message.reply_to_message
        if cmd is not None:
            hid, _ = identity(cmd)
            if c.from_user.id != hid and not await is_group_admin(c.bot, c.message.chat.id, c.from_user.id):
                await c.answer(t(L, "gp_host_only"), show_alert=True)
                return
        await c.answer()
        try:
            await c.message.delete()
        except TelegramAPIError:
            pass
        host = identity(cmd) if cmd is not None else (c.from_user.id, c.from_user.full_name)
        await open_game(cmd or c.message, c.data.split(":")[2], host=host, presser=c.from_user)

    @r.callback_query(F.data.regexp(r"^gp:j:\d+$"))
    async def cb_join(c: CallbackQuery):
        g = games.get(c.message.chat.id)
        L = db.group_lang(c.message.chat.id)
        if not g or g.gid != int(c.data.split(":")[2]) or g.state != "lobby":
            await c.answer(t(L, "gp_gone"), show_alert=True)
            return
        uid = c.from_user.id
        if uid in g.players:
            await c.answer(t(L, "gp_already"))
            return
        if len(g.players) >= MAX_PLAYERS:
            await c.answer(t(L, "gp_full"), show_alert=True)
            return
        db.upsert_user(uid, c.from_user.full_name)
        g.players[uid] = Player(uid, shown(uid, c.from_user.full_name))
        g.dirty = True
        g.wake.set()
        await c.answer(t(L, "gp_joined"))

    @r.callback_query(F.data.regexp(r"^gp:s:\d+$"))
    async def cb_start_now(c: CallbackQuery):
        g = games.get(c.message.chat.id)
        L = db.group_lang(c.message.chat.id)
        if not g or g.gid != int(c.data.split(":")[2]) or g.state != "lobby":
            await c.answer(t(L, "gp_gone"), show_alert=True)
            return
        if not await can_control(c.bot, g, c.from_user.id):
            await c.answer(t(L, "gp_host_only"), show_alert=True)
            return
        g.start_now = True
        g.wake.set()
        await c.answer()

    @r.callback_query(F.data.regexp(r"^gp:x:\d+$"))
    async def cb_cancel(c: CallbackQuery):
        g = games.get(c.message.chat.id)
        L = db.group_lang(c.message.chat.id)
        if not g or g.gid != int(c.data.split(":")[2]) or g.state == "done":
            await c.answer(t(L, "gp_gone"), show_alert=True)
            return
        if not await can_control(c.bot, g, c.from_user.id):
            await c.answer(t(L, "gp_host_only"), show_alert=True)
            return
        await c.answer()
        if g.task:
            g.task.cancel()

    @r.callback_query(F.data.regexp(r"^gp:a:\d+:\d+:\d$"))
    async def cb_answer(c: CallbackQuery):
        _, _, gid, rid, choice = c.data.split(":")
        g = games.get(c.message.chat.id)
        L = db.group_lang(c.message.chat.id)
        if not g or g.gid != int(gid) or g.state != "running" or g.idx != int(rid) or g.closed:
            await c.answer(t(L, "gp_late"))
            return
        p = g.players.get(c.from_user.id)
        if not p:
            await c.answer(t(L, "gp_not_in"), show_alert=True)
            return
        if not p.alive:
            await c.answer(t(L, "gp_you_out"))
            return
        if p.id in g.answers:
            await c.answer(t(L, "gp_changed_no"))
            return
        g.answers[p.id] = (int(choice), time.monotonic())
        await c.answer(t(L, "gp_got"))
        if len(g.answers) >= sum(x.alive for x in g.players.values()):
            g.event.set()

    @r.message(Command("gstop"))
    async def cmd_stop(m: Message):
        L = db.group_lang(m.chat.id)
        g = games.get(m.chat.id)
        if not g or g.state == "done":
            await reply(m, t(L, "gp_gone"))
            return
        uid, _ = identity(m)
        ok = uid == g.host_id or (m.from_user and (m.from_user.id == ANON_ADMIN_ID or await can_control(m.bot, g, m.from_user.id))) \
            or (m.sender_chat is not None and m.sender_chat.id == m.chat.id)
        if not ok:
            await reply(m, t(L, "gp_host_only"))
            return
        if g.task:
            g.task.cancel()

    def top_text(chat_id: int, L: str, plain: bool = False, n: int = 10) -> str:
        medals = ["🥇", "🥈", "🥉"]

        def fmt(rows):
            return "\n".join(f"{medals[i] if i < 3 else str(i + 1) + '.'} {x['name'] if plain else esc(x['name'] or '?')} — "
                             f"🏆{x['wins']} · 🎮{x['games']} · ⭐{x['pts']}" for i, x in enumerate(rows[:n])) or t(L, "lb_empty")
        week, allt = fmt(db.group_top(chat_id, week_start(), n)), fmt(db.group_top(chat_id, 0.0, n))
        return t(L, "gp_top_plain" if plain else "gp_top", week=week, all=allt)

    @r.message(Command("gtop"))
    async def cmd_top(m: Message):
        L = db.group_lang(m.chat.id)
        await reply(m, top_text(m.chat.id, L))

    top_at: dict[int, float] = {}

    @r.callback_query(F.data == "gp:t")
    async def cb_group_top(c: CallbackQuery):
        """زر «ترتيب المجموعة»: رسالة (رد على صاحب الأمر) أو نافذة منبثقة إن ضُغط بكثرة (حماية من الإزعاج)."""
        chat = c.message.chat.id
        L = db.group_lang(chat)
        now = time.monotonic()
        if now - top_at.get(chat, -1e9) < 15:
            await c.answer(top_text(chat, L, plain=True, n=5)[:195], show_alert=True)
            return
        top_at[chat] = now
        await c.answer()
        base = c.message.reply_to_message.message_id if c.message.reply_to_message else c.message.message_id
        thread = c.message.message_thread_id if getattr(c.message, "is_topic_message", False) else None
        await send_to(c.bot, chat, base, thread, top_text(chat, L))

    @r.message(Command("glang"))
    async def cmd_lang(m: Message):
        L = db.group_lang(m.chat.id)
        uid = m.from_user.id if m.from_user else 0
        if not (uid == ANON_ADMIN_ID or m.sender_chat or await is_group_admin(m.bot, m.chat.id, uid)):
            await reply(m, t(L, "gp_host_only"))
            return
        db.touch_group(m.chat.id, m.chat.title)
        new = "en" if L == "ar" else "ar"
        db.set_group_lang(m.chat.id, new)
        await reply(m, t(new, "gp_lang_set"))

    @r.message(Command("start", "help", "ghelp"))
    async def cmd_help(m: Message, command: CommandObject):
        L = db.group_lang(m.chat.id)
        if command.command == "start" and (command.args or "").strip() == "play":      # جاء من زر «تحدٍّ في مجموعة»
            db.touch_group(m.chat.id, m.chat.title)
            if enabled():
                await reply(m, t(L, "gp_menu"), menu_markup(L))
                return
        me = await m.bot.get_me()
        await reply(m, t(L, "gp_help"), kb([btn(t(L, "gp_open_private"), url=f"https://t.me/{me.username}")]))

    @r.my_chat_member()
    async def on_member(ev: ChatMemberUpdated):
        if ev.chat.type in GROUP_TYPES and ev.new_chat_member.status in ("left", "kicked"):
            g = games.get(ev.chat.id)
            if g and g.task:
                g.task.cancel()

    @r.callback_query()
    async def cb_fallback(c: CallbackQuery):
        await c.answer()
    return r
