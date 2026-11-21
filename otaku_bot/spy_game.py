"""برا السالفة (بطابع أنمي) داخل المجموعات فقط.

الجميع يعرف شخصية الأنمي إلا لاعب واحد هو برا السالفة. الجولات تُدار بالمجموعة:
المضيف يضغط "التالي"، والبوت يختار السائل والمجيب، وبعد 10 جولات يصوّت الجميع (في الخاص).
ثم برا السالفة يخمّن الشخصية من قائمة في المجموعة.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, ReplyParameters

from . import progress
from .bot import btn, chan_row, esc, kb
from .config import ROOT
from .ctx import Ctx
from .names import loc
from .links import back_rows, open_private_rows
from .state import STATE
from .texts import t
from .thread_anchor import anchor_id

log = logging.getLogger(__name__)

MIN_PLAYERS, MAX_PLAYERS = 4, 12
ROUNDS = 10
EXTRA_MAX = 10
LOBBY_SECS = 150
NEXT_SECS = 60
ASK_SECS = 60
ANSWER_SECS = 60
VOTE_SECS = 90
REVOTE_SECS = 60
GUESS_SECS = 60
COOLDOWN_SECS = 60
EDIT_GAP = 3.0
GUESS_CHOICES = 7                  # الخيارات كلها (الصحيح + 6 بدائل قريبة)
PTS_WIN = 100


@dataclass
class Player:
    uid: int
    name: str
    outsider: bool = False


@dataclass
class Game:
    gid: int
    chat_id: int
    host_id: int
    host_name: str
    lang: str
    reply_to: int | None
    thread: int | None = None
    players: dict = field(default_factory=dict)
    state: str = "lobby"
    live: int | None = None
    char: dict | None = None            # {"en","ar","aliases"}
    decoys: list = field(default_factory=list)
    round: int = 0
    extra: int = 0
    asked: set = field(default_factory=set)
    cur: tuple | None = None            # (السائل، المجيب)
    question: str | None = None
    answer: str | None = None
    next_go: bool = False
    choices: dict = field(default_factory=dict)     # uid -> "vote" | "more"
    votes: dict = field(default_factory=dict)       # uid -> uid مُصوَّت عليه
    tie_pool: list = field(default_factory=list)
    guess_opts: list = field(default_factory=list)
    caught: int | None = None
    guessed: str | None = None
    dirty: bool = True
    start_now: bool = False
    task: asyncio.Task | None = None


games: dict[int, Game] = STATE.spy_games
cooldown: dict[int, float] = STATE.spy_cooldown
counter = [0]


def load_characters() -> list[dict]:
    data = json.loads((ROOT / "data" / "games.json").read_text(encoding="utf-8"))
    levels = json.loads((ROOT / "data" / "char_levels.json").read_text(encoding="utf-8"))
    mbti = json.loads((ROOT / "data" / "char_mbti.json").read_text(encoding="utf-8"))
    out = []
    names = json.loads((ROOT / "data" / "names_ar.json").read_text(encoding="utf-8")).get("names", {})
    for desc_ar, desc_en, en in data["chars"]:
        ar = names.get(en) or loc(en, "ar")
        aliases = {en.lower(), re.sub(r"\s+", " ", ar).strip()}
        aliases |= {w.lower() for w in en.split() if len(w) >= 5}      # الاسم الأول/الأخير لو طويل
        out.append({"en": en, "ar": ar if ar != en else en, "aliases": {a for a in aliases if a},
                    "level": levels.get(en, 2), "mbti": mbti.get(en)})
    return out


def pick_decoys(char: dict, chars: list[dict], rng: random.Random, n: int) -> list[dict]:
    """بدائل قريبة في الصفات: أولًا نفس نمط الشخصية (MBTI) بأكبر تشابه في الحروف، ثم نفس المستوى.
    نختار عشوائيًا من أفضل المرشحين حتى لا تتكرر نفس البدائل."""
    cands = [c for c in chars if c["en"] != char["en"]]

    def score(c: dict) -> int:
        s = 0
        if char.get("mbti") and c.get("mbti"):
            s += sum(1 for x, y in zip(char["mbti"], c["mbti"]) if x == y) * 10
        if c.get("level") == char.get("level"):
            s += 3
        return s

    ranked = sorted(cands, key=lambda c: (-score(c), rng.random()))
    pool = ranked[: max(n * 2, n)]
    return rng.sample(pool, n)


def normalize(text: str) -> str:
    return re.sub(r"[\s\-_.]+", " ", text.lower()).strip()


def mentions(text: str, char: dict) -> bool:
    t_ = normalize(text)
    return any(normalize(a) and normalize(a) in t_ for a in char["aliases"])


def build_spy_router(ctx: Ctx) -> Router:
    db, rng = ctx.db, ctx.rng
    games, cooldown = ctx.state.spy_games, ctx.state.spy_cooldown
    chars = load_characters()
    root = Router(name="spy")
    msgs = Router(name="spy_msgs")
    msgs.message.filter(F.chat.type.in_({"group", "supergroup"}))
    cbs = Router(name="spy_cbs")
    cbs.callback_query.filter(F.message.chat.type.in_({"group", "supergroup"}))
    pm = Router(name="spy_pm")
    pm.callback_query.filter(F.message.chat.type == "private")

    # ── إرسال وتعديل ────────────────────────────────────────
    async def send(bot: Bot, g: Game, text: str, markup=None) -> int | None:
        kw = {"chat_id": g.chat_id, "parse_mode": "HTML", "reply_markup": markup}
        if g.reply_to:
            kw["reply_parameters"] = ReplyParameters(message_id=g.reply_to, allow_sending_without_reply=True)
        if g.thread:
            kw["message_thread_id"] = g.thread
        for _ in range(2):
            try:
                return (await bot.send_message(text=text, **kw)).message_id
            except TelegramRetryAfter as e:
                await asyncio.sleep(min(e.retry_after, 10))
            except TelegramAPIError as e:
                log.warning("spy send failed in %s: %s", g.chat_id, e)
                return None
        return None

    async def show(bot: Bot, g: Game, text: str, markup=None) -> None:
        """الرسالة الحيّة الواحدة: تُعدَّل فلا تتراكم."""
        if g.live is None:
            g.live = await send(bot, g, text, markup)
            return
        try:
            await bot.edit_message_text(text, chat_id=g.chat_id, message_id=g.live, parse_mode="HTML", reply_markup=markup)
        except TelegramRetryAfter as e:
            if e.retry_after <= 3:
                await asyncio.sleep(e.retry_after)
        except TelegramAPIError:
            pass

    async def dm(bot: Bot, uid: int, text: str, markup=None) -> bool:
        try:
            await bot.send_message(uid, text, parse_mode="HTML", reply_markup=markup)
            return True
        except TelegramAPIError:
            return False

    async def is_admin(bot: Bot, g: Game, uid: int) -> bool:
        if uid == g.host_id or ctx.is_admin(uid):
            return True
        try:
            m = await bot.get_chat_member(g.chat_id, uid)
            return m.status in ("creator", "administrator")
        except TelegramAPIError:
            return False

    def names(g: Game) -> str:
        return "، ".join(esc(p.name) for p in g.players.values()) or "—"

    # ── النصوص ──────────────────────────────────────────────
    def lobby_text(g: Game, left: int) -> str:
        L = g.lang
        return "\n".join([
            t(L, "sp_title"), "",
            t(L, "sp_host", h=esc(g.host_name)),
            t(L, "sp_players", n=len(g.players), names=names(g)),
            t(L, "sp_left", s=max(0, left), min=MIN_PLAYERS, max=MAX_PLAYERS),
            "", t(L, "sp_howto"),
        ])

    def lobby_markup(g: Game):
        L = g.lang
        return kb([btn(t(L, "sp_join"), f"sp:j:{g.gid}"), btn(t(L, "sp_leave"), f"sp:l:{g.gid}")],
                  [btn(t(L, "sp_start"), f"sp:s:{g.gid}"), btn(t(L, "sp_cancel"), f"sp:x:{g.gid}")], *chan_row(L))

    async def lobby_phase(bot: Bot, g: Game) -> None:
        end = time.monotonic() + LOBBY_SECS
        last = 0.0
        while not g.start_now and g.state == "lobby":
            left = end - time.monotonic()
            if left <= 0:
                return
            if g.dirty and time.monotonic() - last >= EDIT_GAP:
                g.dirty, last = False, time.monotonic()
                await show(bot, g, lobby_text(g, int(left)), lobby_markup(g))
            await asyncio.sleep(0.5)

    # ── الجولات ─────────────────────────────────────────────
    async def wait_next(bot: Bot, g: Game, label: str) -> None:
        """المضيف يضغط «التالي»، أو تنتقل الجولة تلقائيًا بعد مهلة."""
        g.next_go = False
        L = g.lang
        await show(bot, g, t(L, "sp_next_live", r=g.round, total=ROUNDS, label=label), kb(
            [btn(t(L, "sp_next_btn"), f"sp:n:{g.gid}")]))
        end = time.monotonic() + NEXT_SECS
        while time.monotonic() < end and not g.next_go:
            await asyncio.sleep(0.5)

    async def ask_round(bot: Bot, g: Game) -> None:
        """يختار البوت السائل والمجيب عشوائيًا، ثم يسأل السائل ويجيب المجيب في المجموعة."""
        L = g.lang
        if len(g.asked) >= len(g.players):
            g.asked = set()
        pool = [u for u in g.players if u not in g.asked]
        asker = rng.choice(pool)
        others = [u for u in g.players if u != asker]
        target = rng.choice(others)
        g.asked.add(asker)
        g.cur = (asker, target)
        g.question = g.answer = None
        an, tn = g.players[asker].name, g.players[target].name
        await show(bot, g, t(L, "sp_ask_live", r=g.round, a=esc(an), b=esc(tn), s=ASK_SECS), None)
        end = time.monotonic() + ASK_SECS
        while time.monotonic() < end and g.question is None:
            await asyncio.sleep(0.5)
        if g.question is None:
            await send(bot, g, t(L, "sp_no_question", a=esc(an)))
            return
        await show(bot, g, t(L, "sp_answer_live", b=esc(tn), s=ANSWER_SECS), None)
        end = time.monotonic() + ANSWER_SECS
        while time.monotonic() < end and g.answer is None:
            await asyncio.sleep(0.5)
        if g.answer is None:
            await send(bot, g, t(L, "sp_no_answer", b=esc(tn)))

    async def vote_prompt(bot: Bot, g: Game) -> bool:
        """بعد الجولة العاشرة (والإضافية): هل يصوّتون أم يكملون؟ يرجع True للتصويت."""
        g.state, g.choices = "choose", {}
        L = g.lang
        await show(bot, g, t(L, "sp_choose_live", n=len(g.players), extra=g.extra, max=EXTRA_MAX),
                   kb([btn(t(L, "sp_vote_btn"), f"sp:c:{g.gid}:vote"), btn(t(L, "sp_more_btn"), f"sp:c:{g.gid}:more")]))
        end = time.monotonic() + VOTE_SECS
        while time.monotonic() < end and len(g.choices) < len(g.players):
            await asyncio.sleep(0.5)
        votes = sum(1 for c in g.choices.values() if c == "vote")
        return votes * 2 > len(g.players)

    async def dm_votes(bot: Bot, g: Game, candidates: list[int], secs: int) -> bool:
        """يرسل التصويت في الخاص لكل لاعب (يصوّت على المرشحين عدا نفسه). False إن فشل إرسال لأحدهم."""
        L = g.lang
        back = await back_rows(bot, g.chat_id, g.live, L)               # زر العودة إلى رسالة اللعبة
        g.votes, g.tie_pool = {}, list(candidates)
        required = set()
        for p in g.players.values():
            opts = [[btn(g.players[c].name[:24], f"sp:v:{g.gid}:{c}")] for c in candidates if c != p.uid]
            if not opts:
                continue
            if not await dm(bot, p.uid, t(L, "sp_vote_dm"), kb(*opts, *back) if back else kb(*opts)):
                return False
            required.add(p.uid)
        end = time.monotonic() + secs
        while time.monotonic() < end and not required <= set(g.votes):
            await asyncio.sleep(0.5)
        return True

    def tally(g: Game) -> list[int]:
        counts: dict[int, int] = {}
        for voter, target in g.votes.items():
            counts[target] = counts.get(target, 0) + 1
        if not counts:
            return []
        top = max(counts.values())
        return [u for u, c in counts.items() if c == top]

    # ── الحلقة الرئيسية ─────────────────────────────────────
    async def run(bot: Bot, g: Game) -> None:
        L = g.lang
        try:
            await lobby_phase(bot, g)
            if g.state != "lobby":
                return
            if len(g.players) < MIN_PLAYERS:
                await show(bot, g, t(L, "sp_too_few", min=MIN_PLAYERS), None)
                return
            g.char = rng.choice(chars)
            g.decoys = pick_decoys(g.char, chars, rng, GUESS_CHOICES - 1)
            uids = list(g.players)
            outsider = rng.choice(uids)
            g.players[outsider].outsider = True
            g.state = "play"
            failed = []
            back = await back_rows(bot, g.chat_id, g.live, L)               # زر العودة إلى رسالة اللعبة
            for p in g.players.values():
                text = t(L, "sp_out_dm") if p.outsider else t(L, "sp_in_dm", char=esc(loc(g.char["en"], L)))
                if not await dm(bot, p.uid, text, kb(*back) if back else None):
                    failed.append(esc(p.name))
            if failed:
                g.state = "done"
                await show(bot, g, t(L, "sp_dm_fail", names="، ".join(failed)), None)
                return
            await show(bot, g, t(L, "sp_roles_done", n=len(g.players)), None)
            while True:
                if g.round >= ROUNDS + g.extra:
                    more = not await vote_prompt(bot, g)
                    if not more or g.extra >= EXTRA_MAX:
                        break
                    g.extra += 1
                g.round += 1
                label = t(L, "sp_round_label") if g.round <= ROUNDS else t(L, "sp_extra_label", e=g.extra)
                await wait_next(bot, g, label)
                await ask_round(bot, g)
                g.state = "play"
            await voting(bot, g)
        except asyncio.CancelledError:
            await show(bot, g, t(L, "sp_stopped"), None)
            raise
        except Exception:  # noqa: BLE001
            log.exception("spy crashed in %s", g.chat_id)
        finally:
            g.state = "done"
            if games.get(g.chat_id) is g:
                games.pop(g.chat_id, None)
            cooldown[g.chat_id] = time.monotonic()

    async def voting(bot: Bot, g: Game) -> None:
        L = g.lang
        g.state = "vote"
        uids = list(g.players)
        await show(bot, g, t(L, "sp_vote_dm_live"), kb(*await open_private_rows(bot, L)))
        if not await dm_votes(bot, g, uids, VOTE_SECS):
            await finish(bot, g, winner="outsider", guessed=None)      # تعذّر إرسال التصويت لأحدهم
            return
        picks = tally(g)
        if len(picks) != 1:                                  # تعادل أو لا أصوات: إعادة تصويت واحدة
            if not picks:
                picks = uids
            await show(bot, g, t(L, "sp_revote_live"), kb(*await open_private_rows(bot, L)))
            await dm_votes(bot, g, picks, REVOTE_SECS)
            picks = tally(g)
            if len(picks) != 1:
                await finish(bot, g, winner="outsider", guessed=None)
                return
        caught = picks[0]
        out_uid = next(p.uid for p in g.players.values() if p.outsider)
        if caught != out_uid:
            await finish(bot, g, winner="outsider", guessed=None)
            return
        g.caught = caught
        await show(bot, g, t(L, "sp_caught", name=esc(g.players[caught].name), s=GUESS_SECS), None)
        opts = [g.char] + g.decoys
        rng.shuffle(opts)
        g.state = "guess"
        g.guess_opts = opts
        await show(bot, g, t(L, "sp_guess_live", name=esc(g.players[caught].name), s=GUESS_SECS), kb(
            *[[btn(loc(o["en"], L)[:40], f"sp:g:{g.gid}:{i}")] for i, o in enumerate(opts)]))
        end = time.monotonic() + GUESS_SECS
        while time.monotonic() < end and g.guessed is None:
            await asyncio.sleep(0.5)
        if g.guessed is None:
            await finish(bot, g, winner="team", guessed=None)
            return
        await finish(bot, g, winner="outsider" if g.guessed == g.char["en"] else "team", guessed=g.guessed)

    async def finish(bot: Bot, g: Game, winner: str, guessed: str | None) -> None:
        L = g.lang
        g.state = "done"
        out = next(p for p in g.players.values() if p.outsider)
        real = loc(g.char["en"], L)
        if winner == "outsider":
            head = t(L, "sp_end_out_win")
            won = {out.uid}
        else:
            head = t(L, "sp_end_team_win")
            won = {u for u in g.players if u != out.uid and g.votes.get(u) == out.uid}
        lines = [
            t(L, "sp_end", head=head, char=esc(real), out=esc(out.name)),
        ]
        if guessed:
            lines.append(t(L, "sp_guessed", g=esc(loc(guessed, L))))
        await show(bot, g, "\n".join(lines), kb(*chan_row(L)) or None)
        for p in g.players.values():
            if db.is_admin(p.uid):
                continue
            pts = PTS_WIN if p.uid in won else 0
            db.add_group_result(g.chat_id, p.uid, pts, "spy", p.uid in won)
            progress.record(db, p.uid, "group", correct=g.round, won=p.uid in won)

    def new_game(chat_id: int, host_id: int, host_name: str, reply_to: int, thread, lang: str) -> Game:
        counter[0] += 1
        return Game(gid=counter[0], chat_id=chat_id, host_id=host_id, host_name=host_name, lang=lang,
                    reply_to=reply_to, thread=thread)

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

    @cbs.callback_query(F.data == "sp:new")
    async def cb_new_from_menu(c: CallbackQuery):
        """زر برا السالفة من قائمة /play في المجموعة."""
        L = db.group_lang(c.message.chat.id)
        why = busy_or_cool(c.message.chat.id)
        if why:
            await c.answer(t(L, "sp_busy" if why == "busy" else "sp_cool"), show_alert=True)
            return
        await c.answer()
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        g = new_game(c.message.chat.id, c.from_user.id, c.from_user.full_name, anchor_id(c.message),
                     c.message.message_thread_id if getattr(c.message, "is_topic_message", False) else None, L)
        g.players[c.from_user.id] = Player(c.from_user.id, c.from_user.full_name)
        games[c.message.chat.id] = g
        g.live = await send(c.bot, g, lobby_text(g, LOBBY_SECS), lobby_markup(g))
        if g.live is None:
            games.pop(c.message.chat.id, None)
            return
        g.task = asyncio.create_task(run(c.bot, g))

    # ── الأوامر والرسائل ────────────────────────────────────
    @msgs.message(Command("spy"))
    async def cmd_spy(m: Message):
        L = db.group_lang(m.chat.id)
        if not m.from_user or m.sender_chat is not None:
            return
        db.touch_group(m.chat.id, m.chat.title)
        why = busy_or_cool(m.chat.id)
        if why:
            await m.reply(t(L, "sp_busy" if why == "busy" else "sp_cool"))
            return
        db.upsert_user(m.from_user.id, m.from_user.full_name)
        thread = m.message_thread_id if getattr(m, "is_topic_message", False) else None
        g = new_game(m.chat.id, m.from_user.id, m.from_user.full_name, anchor_id(m), thread, L)
        g.players[m.from_user.id] = Player(m.from_user.id, m.from_user.full_name)
        games[m.chat.id] = g
        g.live = await send(m.bot, g, lobby_text(g, LOBBY_SECS), lobby_markup(g))
        if g.live is None:
            games.pop(m.chat.id, None)
            return
        g.task = asyncio.create_task(run(m.bot, g))

    @msgs.message(F.text, ~F.text.startswith("/"))
    async def game_text(m: Message):
        """أسئلة وأجوبة الجولة: الرسالة من السائل أو المجيب فقط، ومع فحص اسم الشخصية."""
        g = games.get(m.chat.id)
        if not g or g.state != "play" or g.cur is None or not m.from_user:
            raise SkipHandler()
        uid = m.from_user.id
        asker, target = g.cur
        if uid not in (asker, target):
            raise SkipHandler()
        if g.char and mentions(m.text, g.char):
            try:
                await m.delete()
                await send(m.bot, g, t(g.lang, "sp_no_name", a=esc(g.players[uid].name)))
            except TelegramAPIError:
                await send(m.bot, g, t(g.lang, "sp_no_delete"))
            return
        if uid == asker and g.question is None:
            g.question = m.text.strip()[:200]
        elif uid == target and g.question is not None and g.answer is None:
            g.answer = m.text.strip()[:200]

    @cbs.callback_query(F.data.regexp(r"^sp:j:\d+$"))
    async def cb_join(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        g = get_game(c, int(c.data.split(":")[2]))
        if not g or g.state != "lobby":
            await c.answer(t(L, "sp_gone"), show_alert=True)
            return
        uid = c.from_user.id
        if uid in g.players:
            await c.answer(t(L, "sp_already"))
            return
        if len(g.players) >= MAX_PLAYERS:
            await c.answer(t(L, "sp_full"), show_alert=True)
            return
        db.upsert_user(uid, c.from_user.full_name)
        g.players[uid] = Player(uid, c.from_user.full_name)
        g.dirty = True
        await c.answer(t(L, "sp_joined"))

    @cbs.callback_query(F.data.regexp(r"^sp:l:\d+$"))
    async def cb_leave(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        g = get_game(c, int(c.data.split(":")[2]))
        if not g or g.state != "lobby" or c.from_user.id not in g.players:
            await c.answer(t(L, "sp_gone"), show_alert=True)
            return
        g.players.pop(c.from_user.id)
        g.dirty = True
        await c.answer(t(L, "sp_left"))

    @cbs.callback_query(F.data.regexp(r"^sp:s:\d+$"))
    async def cb_start(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        g = get_game(c, int(c.data.split(":")[2]))
        if not g or g.state != "lobby" or not await is_admin(c.bot, g, c.from_user.id):
            await c.answer(t(L, "sp_host_only"), show_alert=True)
            return
        if len(g.players) < MIN_PLAYERS:
            await c.answer(t(L, "sp_too_few", min=MIN_PLAYERS), show_alert=True)
            return
        g.start_now = True
        await c.answer()

    @cbs.callback_query(F.data.regexp(r"^sp:x:\d+$"))
    async def cb_cancel(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        g = get_game(c, int(c.data.split(":")[2]))
        if not g or not await is_admin(c.bot, g, c.from_user.id):
            await c.answer(t(L, "sp_host_only"), show_alert=True)
            return
        await c.answer()
        if g.task:
            g.task.cancel()

    @cbs.callback_query(F.data.regexp(r"^sp:n:\d+$"))
    async def cb_next(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        g = get_game(c, int(c.data.split(":")[2]))
        if not g or not await is_admin(c.bot, g, c.from_user.id):
            await c.answer(t(L, "sp_host_only"), show_alert=True)
            return
        g.next_go = True
        await c.answer()

    @cbs.callback_query(F.data.regexp(r"^sp:c:\d+:(vote|more)$"))
    async def cb_choose(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        _, _, gid, choice = c.data.split(":")
        g = get_game(c, int(gid))
        if not g or g.state != "choose" or c.from_user.id not in g.players:
            await c.answer(t(L, "sp_gone"), show_alert=True)
            return
        g.choices[c.from_user.id] = choice
        await c.answer(t(L, "sp_chosen"))

    @cbs.callback_query(F.data.regexp(r"^sp:g:\d+:\d$"))
    async def cb_guess(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        _, _, gid, idx = c.data.split(":")
        g = get_game(c, int(gid))
        if not g or g.state != "guess" or c.from_user.id != g.caught:
            await c.answer(t(L, "sp_not_outsider"), show_alert=True)
            return
        g.guessed = g.guess_opts[int(idx)]["en"]
        await c.answer(t(L, "sp_guess_saved"))

    @pm.callback_query(F.data.regexp(r"^sp:v:\d+:\d+$"))
    async def cb_vote(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        _, _, gid, tgt = c.data.split(":")
        g = next((x for x in games.values() if x.gid == int(gid)), None)
        if not g or g.state != "vote":
            await c.answer(t(L, "sp_gone"), show_alert=True)
            return
        if c.from_user.id not in g.players or int(tgt) not in g.tie_pool or int(tgt) == c.from_user.id:
            await c.answer(t(L, "sp_bad_vote"), show_alert=True)
            return
        g.votes[c.from_user.id] = int(tgt)
        await c.answer(t(L, "sp_voted", name=esc(g.players[int(tgt)].name)[:20]), show_alert=True)

    root.include_router(msgs)
    root.include_router(cbs)
    root.include_router(pm)
    return root
