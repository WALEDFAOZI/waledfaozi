"""برا السالفة (بطابع أنمي) داخل المجموعات فقط.

الجميع يعرف شخصية الأنمي إلا لاعب واحد هو برا السالفة. الجولات تُدار بالمجموعة:
المضيف يضغط "التالي"، والبوت يختار السائل والمجيب، وبعد 10 جولات يصوّت الجميع (في الخاص).
ثم برا السالفة يخمّن الشخصية من قائمة في المجموعة.
"""
from __future__ import annotations

import asyncio
import math
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
from . import live
from .links import back_rows, open_private_rows
from .texts import t
from .thread_anchor import anchor_id, reply_anchored

log = logging.getLogger(__name__)

MIN_PLAYERS, MAX_PLAYERS = 3, 12
ROUNDS = 10
VOTE_REQ_BASE = 7         # زر «نبي التصويت» (التخطي) يظهر من هذه الجولة لـ 3 لاعبين
VOTE_REQ_MIN_PLAYERS = 3


def vote_req_from(g) -> int:
    """كل لاعب زيادة يؤخّر الزر جولة واحدة (3 لاعبين = الجولة 7، 4 = الجولة 8...)، والحد الأقصى عدد الجولات."""
    return min(ROUNDS, VOTE_REQ_BASE + max(0, len(g.players) - VOTE_REQ_MIN_PLAYERS))
EXTRA_MAX = 10
LOBBY_SECS = 180
SPY_IDLE_SECS = 900      # بدون أي نشاط لهذه المدة تُغلق اللعبة المتروكة
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
    vote_req: set = field(default_factory=set)   # من طلب التصويت من بعد السؤال السابع
    vote_now: bool = False                       # الأغلبية طلبت التصويت: تنتهي الجولة وتبدأ مرحلة التصويت
    targeted: set = field(default_factory=set)   # من أجاب حتى الآن: يتناوب الجميع على الإجابة قبل أن يعود أحد
    live_transient: bool = False        # الرسالة الحالية حالة مؤقتة (تصويت/تخمين): تُحذف لما تظهر المرحلة التالية
    last_activity: float = 0.0          # آخر نشاط (سؤال، إجابة، «التالي»، تصويت): لإغلاق اللعبة المتروكة
    idle: bool = False
    choices: dict = field(default_factory=dict)     # uid -> "vote" | "more"
    votes: dict = field(default_factory=dict)       # uid -> uid مُصوَّت عليه
    tie_pool: list = field(default_factory=list)
    guess_opts: list = field(default_factory=list)
    caught: int | None = None
    guessed: str | None = None
    dirty: bool = True
    start_now: bool = False
    task: asyncio.Task | None = None


games: dict[int, Game] = {}
cooldown: dict[int, float] = {}
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


def touch(g: Game) -> None:
    g.last_activity = time.monotonic()


def is_idle(g: Game) -> bool:
    return time.monotonic() - g.last_activity > SPY_IDLE_SECS


def mentions(text: str, char: dict) -> bool:
    t_ = normalize(text)
    return any(normalize(a) and normalize(a) in t_ for a in char["aliases"])


def build_spy_router(ctx: Ctx) -> Router:
    db, rng = ctx.db, ctx.rng
    chars = load_characters()
    root = Router(name="spy")
    msgs = Router(name="spy_msgs")
    msgs.message.filter(F.chat.type.in_({"group", "supergroup"}))
    cbs = Router(name="spy_cbs")
    cbs.callback_query.filter(F.message.chat.type.in_({"group", "supergroup"}))
    pm = Router(name="spy_pm")
    pm.callback_query.filter(F.message.chat.type == "private")

    # ── إرسال وتعديل ────────────────────────────────────────
    async def stop_hook(bot, chat_id: int, uid: int):
        """/stop: إيقاف برا السالفة الجارية في هذه المجموعة (المضيف أو أدمن البوت)."""
        g = games.get(chat_id)
        if not g or g.task is None or g.task.done():
            return None
        if uid != g.host_id and not ctx.is_admin(uid):
            return "forbidden"
        g.task.cancel()
        return "stopped"
    ctx.stop_hooks.append(stop_hook)

    async def send(bot: Bot, g: Game, text: str, markup=None) -> int | None:
        """الرسالة الحيّة الوحيدة للعبة: تبدأ بلافتة وتُعدَّل بعد ذلك."""
        return await live.send(bot, g.chat_id, text, markup, lang=g.lang, reply_to=g.reply_to, thread=g.thread, kind="spy")

    async def show(bot: Bot, g: Game, text: str, markup=None) -> None:
        """الرسالة الحيّة الواحدة: تُعدَّل فلا تتراكم."""
        if g.live is None:
            g.live = await send(bot, g, text, markup)
            return
        await live.edit(bot, g.chat_id, g.live, text, markup)

    async def post(bot: Bot, g: Game, text: str, markup=None, transient: bool = False) -> None:
        """مرحلة جديدة = رسالة جديدة تحت. الرسالة السابقة: المؤقتة تُحذف، والباقية تُزال أزرارها (لا تُضغط بالغلط)."""
        if g.live is not None:
            try:
                if g.live_transient:
                    await bot.delete_message(g.chat_id, g.live)
                else:
                    await bot.edit_message_reply_markup(chat_id=g.chat_id, message_id=g.live, reply_markup=None)
            except TelegramAPIError:
                pass
        g.live_transient = transient
        kw = {"reply_markup": markup}
        if g.reply_to:
            kw["reply_parameters"] = ReplyParameters(message_id=g.reply_to, allow_sending_without_reply=True)
        if g.thread:
            kw["message_thread_id"] = g.thread
        try:
            sent = await bot.send_message(g.chat_id, text, parse_mode="HTML", **kw)
            g.live = sent.message_id
        except TelegramAPIError:
            g.live = None                                       # يحاول show() إرسال رسالة جديدة في المرة القادمة

    async def dm(bot: Bot, uid: int, text: str, markup=None) -> bool:
        try:
            await bot.send_message(uid, text, parse_mode="HTML", protect_content=True, reply_markup=markup)
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
        names = [esc(p.name) for p in g.players.values()]
        return "\n" + "\n".join(f"• {n}" for n in names) if names else "—"

    # ── النصوص ──────────────────────────────────────────────
    def lobby_text(g: Game, left: int) -> str:
        L = g.lang
        return "\n".join([
            t(L, "sp_title"), "",
            t(L, "sp_players", n=len(g.players), names=names(g)),
            t(L, "sp_countdown", s=max(0, left), min=MIN_PLAYERS, max=MAX_PLAYERS),
            "", t(L, "sp_howto"),
        ])

    def lobby_markup(g: Game):
        L = g.lang
        return kb([btn(t(L, "sp_join"), f"sp:j:{g.gid}", style="success"), btn(t(L, "sp_leave"), f"sp:l:{g.gid}", style="danger")],
                  [btn(t(L, "sp_start"), f"sp:s:{g.gid}"), btn(t(L, "sp_cancel"), f"sp:x:{g.gid}")], *chan_row(L, bot_link=True))

    async def lobby_phase(bot: Bot, g: Game) -> None:
        end = time.monotonic() + LOBBY_SECS
        last = 0.0
        while not g.start_now and g.state == "lobby":
            left = end - time.monotonic()
            if left <= 0:
                return
            now = time.monotonic()
            if (g.dirty and now - last >= EDIT_GAP) or now - last >= 10:    # العداد ينزل كل 10 ثوانٍ
                g.dirty, last = False, now
                await show(bot, g, lobby_text(g, math.ceil(left)), lobby_markup(g))
            await asyncio.sleep(0.5)

    # ── الجولات ─────────────────────────────────────────────
    async def ask_round(bot: Bot, g: Game) -> None:
        """يختار البوت السائل والمجيب عشوائيًا، ثم يسأل السائل ويجيب المجيب في المجموعة."""
        L = g.lang
        if len(g.asked) >= len(g.players):
            g.asked = set()
        pool = [u for u in g.players if u not in g.asked]
        asker = rng.choice(pool)
        others = [u for u in g.players if u != asker]
        fresh = [u for u in others if u not in g.targeted]          # المجيب: من لم يجب بعد في هذه الدورة
        if not fresh:
            g.targeted = set()
            fresh = others
        target = rng.choice(fresh)
        g.targeted.add(target)
        g.asked.add(asker)
        g.cur = (asker, target)
        g.question = g.answer = None
        g.next_go = False
        touch(g)
        an = (g.players[asker].name or "").strip() or "👤"           # اسم فارغ (رموز فقط): لا يترك السطر فارغًا
        tn = (g.players[target].name or "").strip() or "👤"
        rows = [[btn(t(L, "sp_next_btn"), f"sp:n:{g.gid}")]]
        if g.round >= vote_req_from(g):                            # حسب عدد اللاعبين: زر «نبي التصويت»
            rows.append([btn(t(L, "sp_vote_req_btn"), f"sp:wv:{g.gid}")])
        rows.append([btn(t(L, "sp_end_btn"), f"sp:x:{g.gid}")])    # «إلغاء اللعبة» دائمًا في الجولة
        next_kb = kb(*rows)
        await post(bot, g, t(L, "sp_ask_live", r=g.round, a=esc(an), b=esc(tn)), next_kb)
        while g.question is None and not g.next_go and not g.vote_now:   # لا عداد: الجولة تنتقل بضغط «التالي» أو طلب التصويت
            if is_idle(g):
                g.idle = True
                return
            await asyncio.sleep(0.5)
        if g.next_go or g.question is None:                 # «التالي» أو انتهى الوقت بلا سؤال: الجولة التالية
            return
        await show(bot, g, t(L, "sp_answer_live", a=esc(an), b=esc(tn)), next_kb)      # الجواب يعدّل رسالة الجولة نفسها
        while g.answer is None and not g.next_go and not g.vote_now:
            if is_idle(g):
                g.idle = True
                return
            await asyncio.sleep(0.5)
        # لا رسالة عند انتهاء وقت الإجابة: العداد يكفي، والمضيف يضغط «التالي»

    async def vote_prompt(bot: Bot, g: Game) -> bool:
        """بعد الجولة العاشرة (والإضافية): هل يصوّتون أم يكملون؟ يرجع True للتصويت."""
        g.state, g.choices = "choose", {}
        L = g.lang
        await post(bot, g, t(L, "sp_choose_live", n=len(g.players), extra=g.extra, max=EXTRA_MAX),
                   kb([btn(t(L, "sp_vote_btn"), f"sp:c:{g.gid}:vote"), btn(t(L, "sp_more_btn"), f"sp:c:{g.gid}:more")]), transient=True)
        n = len(g.players)

        def decided() -> bool:                                     # الأغلبية حسمت: لا ننتظر الباقين
            votes = sum(1 for c in g.choices.values() if c == "vote")
            return votes * 2 > n or (len(g.choices) - votes) * 2 >= n
        end = time.monotonic() + VOTE_SECS
        while time.monotonic() < end and not decided() and len(g.choices) < n:
            await asyncio.sleep(0.5)
        votes = sum(1 for c in g.choices.values() if c == "vote")
        return votes * 2 > n

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
                    if g.extra >= EXTRA_MAX:                # الحد الأقصى: تصويت إجباري بدون سؤال
                        break
                    more = not await vote_prompt(bot, g)    # الأغلبية تختار: تصويت الآن، أو جولة واحدة إضافية
                    if not more:
                        break
                    g.extra += 1
                g.round += 1
                g.state = "play"                            # الجولة جارية: لا أزرار تصويت الآن
                await ask_round(bot, g)
                if g.idle or g.vote_now:
                    break
            if g.idle:
                await show(bot, g, t(L, "sp_idle"), None)
                return
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
        await post(bot, g, t(L, "sp_vote_dm_live"), kb(*await open_private_rows(bot, L)), transient=True)
        if not await dm_votes(bot, g, uids, VOTE_SECS):
            await finish(bot, g, winner="outsider", guessed=None)      # تعذّر إرسال التصويت لأحدهم
            return
        picks = tally(g)
        if len(picks) != 1:                                  # تعادل أو لا أصوات: إعادة تصويت واحدة
            if not picks:
                picks = uids
            await post(bot, g, t(L, "sp_revote_live"), kb(*await open_private_rows(bot, L)), transient=True)
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
        await post(bot, g, t(L, "sp_caught", name=esc(g.players[caught].name), s=GUESS_SECS), None, transient=True)
        opts = [g.char] + g.decoys
        rng.shuffle(opts)
        g.state = "guess"
        g.guess_opts = opts
        await post(bot, g, t(L, "sp_guess_live", name=esc(g.players[caught].name), s=GUESS_SECS), kb(
            *[[btn(loc(o["en"], L)[:40], f"sp:g:{g.gid}:{i}")] for i, o in enumerate(opts)]), transient=True)
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
        await post(bot, g, "\n".join(lines), kb(*chan_row(L, bot_link=True)) or None)
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
            await reply_anchored(m, t(L, "sp_busy" if why == "busy" else "sp_cool"))
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
            touch(g)
        elif uid == target and g.question is not None and g.answer is None:
            g.answer = m.text.strip()[:200]
            touch(g)

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

    @cbs.callback_query(F.data.regexp(r"^sp:wv:\d+$"))
    async def cb_want_vote_btn(c: CallbackQuery):
        await cb_want_vote(c)

    @cbs.callback_query(F.data.regexp(r"^sp:n:\d+$"))
    async def cb_want_vote(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        g = get_game(c, int(c.data.split(":")[2]))
        if not g or g.state != "play" or g.round < vote_req_from(g) or c.from_user.id not in g.players or g.vote_now:
            await c.answer(t(L, "sp_gone"), show_alert=True)
            return
        g.vote_req.add(c.from_user.id)
        touch(g)
        if len(g.vote_req) * 2 > len(g.players):                  # الأغلبية: تنتهي الجولة وتبدأ مرحلة التصويت
            g.vote_now = True
            g.next_go = True
        await c.answer(t(L, "sp_vote_req_ok"))

    async def cb_next(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        g = get_game(c, int(c.data.split(":")[2]))
        if not g or not await is_admin(c.bot, g, c.from_user.id):
            await c.answer(t(L, "sp_host_only"), show_alert=True)
            return
        g.next_go = True
        touch(g)
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
        touch(g)
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
