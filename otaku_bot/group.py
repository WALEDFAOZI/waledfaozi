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

from . import board, live, progress
from .bot import btn, esc, kb
from .ctx import Ctx
from .games import load_games, order_rounds, quote_rounds, char_rounds, song_rounds, tf_rounds
from .names import loc, loc_opt
from .quiz import pick_questions, shuffle_options
from .texts import t
from .thread_anchor import ANON_ADMIN_ID, anchor_id, identity
from .timeutil import week_start

log = logging.getLogger(__name__)

# قابلة للتعديل (والاختبارات تقلّلها)
LOBBY_SECONDS = 180         # غرفة الانتظار: 3 دقائق
Q_SECONDS = 15
PAUSE = 3
MIN_PLAYERS = 2
CH_MIN_PLAYERS = 1          # القنوات: يكفي مشارك واحد (التجربة والمسابقات الصغيرة)
MAX_PLAYERS = 40
CHAT_COOLDOWN = 30          # بعد انتهاء لعبة في المجموعة
START_COOLDOWN = 45         # لكل من يبدأ ألعابًا
CH_LOBBY_SECONDS = 180      # مسابقات القنوات: 3 دقائق للمشاركة
CH_Q_SECONDS = 30           # ثم 30 ثانية لكل سؤال
CH_MAX_PLAYERS = 200000
CH_KEEP = 50                # في القنوات الكبيرة نحفظ أفضل 50 فقط في القاعدة
KINDS = ("quiz", "sudden", "tf", "char", "quote", "ord", "images")
CMD_KIND = {"quiz": "quiz", "sudden": "sudden", "tf": "tf", "char": "char", "quote": "quote",
            "order": "ord", "images": "images"}
GROUP_TYPES = {"group", "supergroup"}
ANY_TYPES = GROUP_TYPES | {"channel"}
ANON = "مجهول 🎭 · Anonymous"
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
    reply_to: int | None
    host_id: int
    host_name: str
    kind: str
    lang: str
    players: dict = field(default_factory=dict)
    state: str = "lobby"
    scope: str = "group"            # group | channel
    live: int | None = None         # الرسالة الحيّة الوحيدة: غرفة الانتظار ثم الأسئلة (تُعدَّل ولا تتراكم)
    live_photo: bool = False
    live_media: str | None = None      # ما تعرضه الرسالة الحيّة الآن: "banner" أو معرّف/رابط الصورة
    lobby_secs: float = 30
    q_secs: float = 15
    max_players: int = 40
    min_players: int = 2
    edit_gap: float = 2.5
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


_BG_TASKS: set = set()   # مهام خلفية قصيرة (حذف رسائل مؤقتة) نحتفظ بمراجعها
NOTICE_SECS = 15         # ردود البوت على الأوامر والتنبيهات تُحذف بعد هذه المدة (لا تبقى في المجموعة)


def expire_later(bot: Bot, chat_id: int, mid: int | None, secs: float = NOTICE_SECS) -> None:
    """يحذف الرسالة بعد مدة. يفشل بصمت إن لم تعد موجودة أو ليس للبوت صلاحية."""
    if not mid:
        return

    async def later():
        await asyncio.sleep(secs)
        try:
            await bot.delete_message(chat_id, mid)
        except TelegramAPIError:
            pass
    task = asyncio.create_task(later())
    _BG_TASKS.add(task)                          # نحتفظ بمرجع حتى ينتهي
    task.add_done_callback(_BG_TASKS.discard)


def build_group_router(ctx: Ctx) -> Router:
    root = Router(name="groups")

    r = Router(name="group_msgs")                       # أوامر المجموعات
    r.message.filter(F.chat.type.in_(GROUP_TYPES))
    cb = Router(name="group_cbs")                       # أزرار المجموعات والقنوات
    cb.callback_query.filter(F.message.chat.type.in_(ANY_TYPES))
    pm = Router(name="group_pm")                        # الخاص: اختيار القناة ونوع المسابقة
    pm.callback_query.filter(F.message.chat.type == "private")
    db, rng = ctx.db, ctx.rng
    games: dict[int, Game] = {}               # chat_id → اللعبة الجارية
    cooldown: dict[int, float] = {}           # chat_id → وقت انتهاء آخر لعبة
    start_at: dict[int, float] = {}           # من بدأ → وقت آخر بدء
    seen: dict[int, dict[int, float]] = {}    # chat_id → أسئلة شوهدت مؤخرًا
    counter = [0]
    send_errors: dict[int, str] = {}          # chat_id → آخر سبب فشل نشر (يُعرض للمنظّم)

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
        """الرسالة الحيّة الوحيدة للعبة: تبدأ بلافتة وتُعدَّل بعد ذلك (لا رسائل جديدة)."""
        return await live.send(bot, g.chat_id, text, markup, lang=g.lang, reply_to=g.reply_to, thread=g.thread,
                               on_error=lambda e: send_errors.__setitem__(g.chat_id, e[:120]), kind=g.kind)

    async def send_to(bot: Bot, chat_id: int, reply_to: int | None, thread: int | None, text: str, markup=None,
                      photo: str | None = None) -> int | None:
        """كل رسالة جديدة في المجموعة = رد على رسالة صاحب الأمر (القنوات: رسالة عادية بلا رد)."""
        kw = dict(chat_id=chat_id, parse_mode="HTML", reply_markup=markup)
        if reply_to:
            kw["reply_parameters"] = ReplyParameters(message_id=reply_to, allow_sending_without_reply=True)
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
                send_errors[chat_id] = str(e)[:120]
                return None
            except (TelegramForbiddenError, TelegramAPIError) as e:
                log.warning("group send failed in %s: %s", chat_id, e)
                send_errors[chat_id] = str(e)[:120]
                return None
        return None

    async def edit(bot: Bot, g: Game, mid: int | None, text: str, markup=None, caption: bool = False) -> None:
        """تعديل التعليق والأزرار للرسالة الحيّة (الصورة تبقى كما هي)."""
        if mid:
            await live.edit(bot, g.chat_id, mid, text, markup)

    async def delete_msg(bot: Bot, g: Game, mid: int | None) -> None:
        if mid:
            try:
                await bot.delete_message(g.chat_id, mid)
            except TelegramAPIError:
                pass

    async def live_show(bot: Bot, g: Game, text: str, markup=None, photo: str | None = None) -> bool:
        """الرسالة الحيّة الوحيدة: تُعدَّل دائمًا. تتغير صورتها فقط عند الحاجة (صورة جولة، أو العودة للافتة)."""
        if g.live is None:
            mid = await send(bot, g, text, markup)
            if mid is None:
                return False
            g.live, g.live_photo, g.live_media = mid, True, "banner"
        want = photo or "banner"
        media = None
        if want != g.live_media:
            media = photo or await live.banner_media(g.lang, g.kind)
        if await live.edit(bot, g.chat_id, g.live, text, markup, media=media):
            g.live_media = want
        return True

    async def reply(m: Message, text: str, markup=None, expire: float | None = None) -> None:
        kw = {"message_thread_id": m.message_thread_id} if getattr(m, "is_topic_message", False) and m.message_thread_id else {}
        try:
            sent = await m.bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=markup,
                                            reply_parameters=ReplyParameters(message_id=anchor_id(m), allow_sending_without_reply=True),   # داخل تعليقات المنشور: نرد على نسخة المنشور
                                            **kw)
        except TelegramAPIError as e:
            log.warning("group reply failed: %s", e)
            return
        if expire:                                # تنبيه مؤقت: يُحذف وحده
            expire_later(m.bot, m.chat.id, sent.message_id, expire)

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
        return t(g.lang, "gp_lobby" if g.scope == "group" else "gp_lobby_ch", kind=t(g.lang, f"gpk_{g.kind}"), host=esc(g.host_name), left=max(0, left),
                 n=len(g.players), names=pnames(g), min=g.min_players)

    def sub_row(L: str) -> list:
        """زر «اشترك في قناة البوت» تحت الخيارات والنتيجة (إن كانت قناة الاشتراك مضبوطة)."""
        ch = (ctx.channel() or "").lstrip("@")
        return [[btn(t(L, "btn_channel"), url=f"https://t.me/{ch}")]] if ch else []

    sub_sem = asyncio.Semaphore(20)           # لا نغرق تليجرام بفحوص الاشتراك عند الانضمام الجماعي

    async def is_subscribed(bot: Bot, uid: int) -> bool:
        """الاشتراك إجباري. تعذّر التحقق (البوت ليس أدمن بقناة الاشتراك) يُعامل كمشترك كما في بقية البوت."""
        if not ctx.channel() or not ctx.subscribed or ctx.is_admin(uid):
            return True
        async with sub_sem:
            try:
                return (await ctx.subscribed(bot, uid)) is not False
            except Exception:  # noqa: BLE001
                return True

    def lobby_markup(g: Game):
        leave = btn(t(g.lang, "gp_leave"), f"gp:u:{g.gid}")
        if g.scope == "channel":                          # في القناة: مشاركة/انسحاب فقط؛ التحكم من الخاص
            return kb([btn(t(g.lang, "gp_join_ch"), f"gp:j:{g.gid}"), leave], *sub_row(g.lang))
        return kb([btn(t(g.lang, "gp_join"), f"gp:j:{g.gid}"), leave],
                  [btn(t(g.lang, "gp_start_now"), f"gp:s:{g.gid}"), btn(t(g.lang, "gp_cancel"), f"gp:x:{g.gid}")],
                  *sub_row(g.lang))

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
            return kb([btn(t(g.lang, "g_true"), f"gp:a:{g.gid}:{g.idx}:0"), btn(t(g.lang, "g_false"), f"gp:a:{g.gid}:{g.idx}:1")],
                      *sub_row(g.lang))
        btns = [btn(LETTERS[i], f"gp:a:{g.gid}:{g.idx}:{i}") for i in range(len(rnd.options))]
        return kb(btns[:2], btns[2:], *sub_row(g.lang))

    # ── سير اللعبة ─────────────────────────────────────────
    async def lobby_phase(bot: Bot, g: Game) -> None:
        end = time.monotonic() + g.lobby_secs
        last = 0.0
        while not g.start_now:
            left = end - time.monotonic()
            if left <= 0:
                break
            now = time.monotonic()
            # العدّاد يتحدّث كل مرة (لا يبقى ثابتًا): نعدّل الرسالة كل edit_gap ثانية بالوقت المتبقي الفعلي
            if now - last >= g.edit_gap:
                g.dirty = False
                last = now
                await edit(bot, g, g.live, lobby_text(g, int(left + 0.5)), lobby_markup(g))
            g.wake.clear()
            try:
                await asyncio.wait_for(g.wake.wait(), timeout=min(g.edit_gap, max(left, 0.02)))
            except asyncio.TimeoutError:
                pass

    async def play_round(bot: Bot, g: Game, rnd: Rnd) -> bool:
        alive = [p for p in g.players.values() if p.alive]
        g.answers = {}
        g.event.clear()
        g.closed = False
        start = time.monotonic()
        g.deadline = start + g.q_secs
        if not await live_show(bot, g, round_text(g, rnd, int(g.q_secs)), answer_markup(g, rnd), rnd.photo):
            return False
        mid, is_photo = g.live, g.live_photo
        try:
            await asyncio.wait_for(g.event.wait(), timeout=g.q_secs / 2)
        except asyncio.TimeoutError:
            await edit(bot, g, mid, round_text(g, rnd, int(g.q_secs / 2 + 0.5), len(g.answers), len(alive)),
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
                pts = 100 + int(100 * remain / g.q_secs)
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
        sr = sub_row(g.lang)
        await edit(bot, g, mid, "\n".join(lines), kb(*sr) if sr else None, caption=is_photo)
        return True

    def ranking(g: Game) -> list[Player]:
        ps = list(g.players.values())
        if g.kind == "sudden":
            return sorted(ps, key=lambda p: (p.alive, p.out_round, p.points), reverse=True)
        return sorted(ps, key=lambda p: p.points, reverse=True)

    async def finish(bot: Bot, g: Game) -> None:
        rk = ranking(g)
        if g.scope == "channel" and ctx.channel():              # من غادر قناتنا أثناء المسابقة لا يدخل النتيجة
            ok: list[Player] = []
            for i, p in enumerate(rk):
                if len(ok) >= CH_KEEP or i >= 80:
                    break
                if await is_subscribed(bot, p.id):
                    ok.append(p)
            rk = ok
        if g.kind == "sudden":
            top = rk[0]
            champs = [p for p in rk if (p.alive, p.out_round) == (top.alive, top.out_round)]
        else:
            champs = [p for p in rk if p.points == rk[0].points] if rk and rk[0].points > 0 else []
        medals = ["🥇", "🥈", "🥉"]
        lines = [f"{medals[i] if i < 3 else str(i + 1) + '.'} {esc(p.name)} — <b>{p.points}</b>" for i, p in enumerate(rk[:10])]
        win = ("🏆 " + t(g.lang, "gp_winner", w=" + ".join(esc(p.name) for p in champs[:5]))) if champs else t(g.lang, "gp_nowinner")
        me = (await bot.get_me()).username
        markup = kb([btn(t(g.lang, "gp_try_btn"), url=f"https://t.me/{me}?start=src_contest")],
                    *([[btn(t(g.lang, "gp_top_btn"), "gp:t")]] if g.scope == "group" else []), *sub_row(g.lang))
        await live_show(bot, g, t(g.lang, "gp_final", w=win, n=len(g.players), rows="\n".join(lines)), markup)   # نفس الرسالة الحيّة
        keep = rk[:CH_KEEP] if g.scope == "channel" else rk               # القنوات الكبيرة: أفضل 50 فقط في القاعدة
        champ_ids = {p.id for p in champs}
        for p in keep:                                                      # الأدمن لا يدخل الترتيب
            if not db.is_admin(p.id):
                if g.scope == "channel":
                    db.upsert_user(p.id, p.name)
                db.add_group_result(g.chat_id, p.id, p.points, g.kind, p.id in champ_ids)
                progress.record(db, p.id, "group", correct=p.correct, won=p.id in champ_ids)

    async def run(bot: Bot, g: Game) -> None:
        try:
            await lobby_phase(bot, g)
            if len(g.players) < g.min_players:
                await edit(bot, g, g.live, t(g.lang, "gp_too_few" if g.min_players > 1 else "gp_nobody_joined", min=g.min_players), None)
                expire_later(bot, g.chat_id, g.live, NOTICE_SECS)     # اللعبة انتهت: الرسالة تختفي وحدها
                return
            g.state = "running"
            g.rounds = build_rounds(g.kind, g.lang, g.chat_id)
            if not g.rounds:
                await edit(bot, g, g.live, t(g.lang, "gp_no_rounds"), None)
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
            await edit(bot, g, g.live, t(g.lang, "gp_stopped"), None, caption=g.live_photo)
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
            await reply(m, t(L, "gp_disabled"), expire=NOTICE_SECS)
            return
        hid, hname = host or identity(m)
        starter = presser or m.from_user
        if starter and db.is_admin(starter.id):
            hname = ANON
        db.touch_group(m.chat.id, m.chat.title)
        cur = games.get(m.chat.id)
        if cur and cur.state != "done":
            await reply(m, t(L, "gp_busy"), expire=NOTICE_SECS)
            return
        wait = CHAT_COOLDOWN - (time.monotonic() - cooldown.get(m.chat.id, -1e9))
        if wait > 0:
            await reply(m, t(L, "gp_cooldown", s=int(wait) + 1), expire=NOTICE_SECS)
            return
        w2 = START_COOLDOWN - (time.monotonic() - start_at.get(hid, -1e9))
        if w2 > 0 and not (starter and ctx.is_admin(starter.id)):
            await reply(m, t(L, "gp_cooldown", s=int(w2) + 1), expire=NOTICE_SECS)
            return
        start_at[hid] = time.monotonic()
        counter[0] += 1
        thread = m.message_thread_id if getattr(m, "is_topic_message", False) else None
        g = Game(gid=counter[0], chat_id=m.chat.id, thread=thread, reply_to=anchor_id(m), host_id=hid, host_name=hname,
                 kind=kind, lang=L, lobby_secs=LOBBY_SECONDS, q_secs=Q_SECONDS, max_players=MAX_PLAYERS,
                 min_players=MIN_PLAYERS)
        games[m.chat.id] = g
        g.live = await send(bot, g, lobby_text(g, int(g.lobby_secs)), lobby_markup(g))
        if g.live is None:                                                    # لا صلاحية للإرسال
            games.pop(m.chat.id, None)
            return
        g.task = asyncio.create_task(run(bot, g))

    @r.message(Command(*CMD_KIND.keys()))
    async def cmd_kind(m: Message, command: CommandObject):
        await open_game(m, CMD_KIND[command.command])

    def menu_markup(L: str):
        # المافيا وحدها في سطر، والباقي كل سطر لعبتان: برا السالفة ثم الجماعية، ثم الثنائية، والترتيب في آخر سطر
        rows = [[btn(t(L, "gpk_mafia"), "mf:new")]]
        pairs = [("gpk_spy", "sp:new")] + [(f"gpk_{k}", f"gp:n:{k}") for k in KINDS]
        rows += [[btn(t(L, a), c) for a, c in pairs[i:i + 2]] for i in range(0, len(pairs), 2)]
        rows.append([btn(t(L, "gpm_xo"), "ar:g:xo"), btn(t(L, "gpm_rps"), "ar:g:rps")])
        rows.append([btn(t(L, "gpm_c4"), "ar:g:c4"), btn(t(L, "gpm_top"), "gp:t")])
        return kb(*rows)

    @r.message(Command("play"))
    async def cmd_play(m: Message):
        L = db.group_lang(m.chat.id)
        if not enabled():
            await reply(m, t(L, "gp_disabled"))
            return
        await reply(m, t(L, "gp_menu"), menu_markup(L))

    @cb.callback_query(F.data.regexp(r"^gp:n:(quiz|sudden|tf|char|quote|ord|images)$"))
    async def cb_pick(c: CallbackQuery):
        cmd = c.message.reply_to_message
        await c.answer()
        try:
            await c.message.delete()
        except TelegramAPIError:
            pass
        host = (c.from_user.id, c.from_user.full_name)              # من يختار اللعبة يصير مضيفها
        await open_game(cmd or c.message, c.data.split(":")[2], host=host, presser=c.from_user)

    @cb.callback_query(F.data.regexp(r"^gp:j:\d+$"))
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
        if g.scope == "channel" and not await is_subscribed(c.bot, uid):
            await c.answer(t(L, "gp_must_sub", ch=(ctx.channel() or "").lstrip("@")), show_alert=True)
            return
        if len(g.players) >= g.max_players:
            await c.answer(t(L, "gp_full"), show_alert=True)
            return
        if g.scope == "group":                                  # القنوات الكبيرة: لا كتابة في القاعدة لكل مشارك
            db.upsert_user(uid, c.from_user.full_name)
        g.players[uid] = Player(uid, shown(uid, c.from_user.full_name))
        g.dirty = True
        g.wake.set()
        await c.answer(t(L, "gp_joined" if g.scope == "group" else "gp_joined_ch"))

    @cb.callback_query(F.data.regexp(r"^gp:u:\d+$"))
    async def cb_leave(c: CallbackQuery):
        """إلغاء المشاركة: متاح فقط قبل بدء الأسئلة."""
        g = games.get(c.message.chat.id)
        L = db.group_lang(c.message.chat.id)
        if not g or g.gid != int(c.data.split(":")[2]) or g.state == "done":
            await c.answer(t(L, "gp_gone"), show_alert=True)
            return
        if g.state != "lobby":
            await c.answer(t(L, "gp_leave_late"), show_alert=True)
            return
        if g.players.pop(c.from_user.id, None) is None:
            await c.answer(t(L, "gp_not_joined"))
            return
        g.dirty = True
        g.wake.set()
        await c.answer(t(L, "gp_left"))

    @cb.callback_query(F.data.regexp(r"^gp:s:\d+$"))
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

    @cb.callback_query(F.data.regexp(r"^gp:x:\d+$"))
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

    @cb.callback_query(F.data.regexp(r"^gp:a:\d+:\d+:\d$"))
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
            await reply(m, t(L, "gp_gone"), expire=NOTICE_SECS)
            return
        uid, _ = identity(m)
        ok = uid == g.host_id or (m.from_user and (m.from_user.id == ANON_ADMIN_ID or await can_control(m.bot, g, m.from_user.id))) \
            or (m.sender_chat is not None and m.sender_chat.id == m.chat.id)
        if not ok:
            await reply(m, t(L, "gp_host_only"), expire=NOTICE_SECS)
            return
        if g.task:
            g.task.cancel()

    def top_text(chat_id: int, L: str, plain: bool = False, n: int = 10) -> str:
        """ترتيب المجموعة العام فقط: أول 10 بالنقاط، والقائمة مختصرة (بدون أسبوعي)."""
        rows = db.group_top(chat_id, 0.0, n)
        pairs = [(x["name"], f"⭐{x['pts']} · 🏆{x['wins']}") for x in rows[:n]]
        return board.render(t(L, "gp_top_title_plain" if plain else "gp_top_title"), pairs, t(L, "lb_empty"))

    @r.message(Command("gtop"))
    async def cmd_top(m: Message):
        L = db.group_lang(m.chat.id)
        await reply(m, top_text(m.chat.id, L))

    top_at: dict[int, float] = {}

    @cb.callback_query(F.data == "gp:t")
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

    # ── مسابقات القنوات ────────────────────────────────────
    ADD_URL = "https://t.me/{me}?startchannel=play&admin=post_messages+edit_messages+delete_messages"

    def kinds_markup(L: str, chat_id: int):
        rows = [[btn(t(L, "gpk_mafia"), f"mf:cs:{chat_id}")]]                  # المافيا أولًا (تُبدأ من الخاص)
        rows += [[btn(t(L, f"gpk_{k}"), f"ch:n:{chat_id}:{k}")] for k in KINDS]
        return kb(*rows, [btn(t(L, "ch_test_btn"), f"ch:t:{chat_id}")], [btn(t(L, "btn_menu"), "menu")])

    async def offer_menu(bot: Bot, user_id: int, chat_id: int, title: str | None, warn: str = "") -> bool:
        L = db.get_lang(user_id)
        try:
            await bot.send_message(user_id, t(L, "ch_linked", title=esc(title or "?")) + warn, parse_mode="HTML",
                                   reply_markup=kinds_markup(L, chat_id))
            return True
        except TelegramAPIError:
            return False                                   # لم يبدأ البوت بالخاص بعد

    async def can_manage(bot: Bot, chat_id: int, uid: int) -> bool:
        return db.channel_owner(chat_id) == uid or await is_group_admin(bot, chat_id, uid)

    @root.my_chat_member()
    async def on_member(ev: ChatMemberUpdated):
        st = ev.new_chat_member.status
        if st in ("left", "kicked") and ev.chat.type in ANY_TYPES:
            g = games.get(ev.chat.id)
            if g and g.task:
                g.task.cancel()
            db.forget_chat(ev.chat.id)                       # لم يعد البوت هناك: لا إرسال ولا إحصاء
            return
        if ev.chat.type == "channel" and st == "administrator" and ev.from_user and not ev.from_user.is_bot:
            db.touch_group(ev.chat.id, ev.chat.title)
            db.link_channel(ev.chat.id, ev.from_user.id, ev.chat.title)
            nm = ev.new_chat_member
            L = db.get_lang(ev.from_user.id)
            ok = getattr(nm, "can_post_messages", True) and getattr(nm, "can_edit_messages", True)
            await offer_menu(ev.bot, ev.from_user.id, ev.chat.id, ev.chat.title, "" if ok else "\n\n" + t(L, "ch_rights_warn"))

    @root.channel_post(Command("play"))
    async def ch_play(m: Message):
        """اكتب /play في القناة: يحذف البوت منشورك ويرسل لك (بالخاص) قائمة أنواع المسابقة."""
        try:
            await m.delete()
        except TelegramAPIError:
            pass
        owner = db.channel_owner(m.chat.id)
        if not owner:
            try:
                admins = await m.bot.get_chat_administrators(m.chat.id)
            except TelegramAPIError:
                admins = []
            owner = next((a.user.id for a in admins if a.status == "creator" and not a.user.is_bot), None)
            if owner:
                db.link_channel(m.chat.id, owner, m.chat.title)
        ok = bool(owner) and await offer_menu(m.bot, owner, m.chat.id, m.chat.title)
        if not ok:                                         # لا نستطيع مراسلة المنظّم: تنبيه مؤقت يختفي وحده
            me = (await m.bot.get_me()).username
            try:
                note = await m.bot.send_message(m.chat.id, t(db.group_lang(m.chat.id), "ch_open_pm", me=me), parse_mode="HTML")
            except TelegramAPIError:
                return

            async def later():
                await asyncio.sleep(12)
                try:
                    await m.bot.delete_message(m.chat.id, note.message_id)
                except TelegramAPIError:
                    pass
            task = asyncio.create_task(later())
            _BG_TASKS.add(task)                          # نحتفظ بمرجع حتى ينتهي، وإلا قد يجمعه المحرر قبل حذف الرسالة
            task.add_done_callback(_BG_TASKS.discard)

    @pm.callback_query(F.data == "gpc")
    async def cb_channels(c: CallbackQuery):
        """زر القائمة الرئيسية «تحدٍّ في قناة»: قنواتك المرتبطة + إضافة قناة جديدة."""
        await c.answer()
        L = db.get_lang(c.from_user.id)
        me = (await c.bot.get_me()).username
        rows = [[btn(f"📢 {title or chat_id}", f"ch:m:{chat_id}")] for chat_id, title in db.user_channels(c.from_user.id)[:8]]
        rows.append([btn(t(L, "ch_add_btn"), url=ADD_URL.format(me=me))])
        rows.append([btn(t(L, "btn_menu"), "menu")])
        await c.message.answer(t(L, "ch_intro"), parse_mode="HTML", reply_markup=kb(*rows))

    @pm.callback_query(F.data.regexp(r"^ch:m:-?\d+$"))
    async def cb_channel_menu(c: CallbackQuery):
        chat_id = int(c.data.split(":")[2])
        L = db.get_lang(c.from_user.id)
        if not await can_manage(c.bot, chat_id, c.from_user.id):
            await c.answer(t(L, "gp_host_only"), show_alert=True)
            return
        await c.answer()
        title = next((tt for cid, tt in db.user_channels(c.from_user.id) if cid == chat_id), None)
        await c.message.answer(t(L, "ch_linked", title=esc(title or str(chat_id))), parse_mode="HTML",
                               reply_markup=kinds_markup(L, chat_id))

    @pm.callback_query(F.data.regexp(r"^ch:n:-?\d+:(quiz|sudden|tf|char|quote|ord|images)$"))
    async def cb_channel_start(c: CallbackQuery):
        _, _, cid, kind = c.data.split(":")
        chat_id = int(cid)
        L = db.get_lang(c.from_user.id)
        if not await can_manage(c.bot, chat_id, c.from_user.id):
            await c.answer(t(L, "gp_host_only"), show_alert=True)
            return
        if not enabled():
            await c.answer(t(L, "gp_disabled"), show_alert=True)
            return
        cur = games.get(chat_id)
        if cur and cur.state != "done":
            await c.answer(t(L, "gp_busy"), show_alert=True)
            return
        wait = CHAT_COOLDOWN - (time.monotonic() - cooldown.get(chat_id, -1e9))
        if wait > 0:
            await c.answer(t(L, "gp_cooldown", s=int(wait) + 1), show_alert=True)
            return
        counter[0] += 1
        starter = c.from_user
        g = Game(gid=counter[0], chat_id=chat_id, thread=None, reply_to=None, host_id=starter.id,
                 host_name=ANON if db.is_admin(starter.id) else clean(starter.full_name), kind=kind,
                 lang=db.group_lang(chat_id), scope="channel", lobby_secs=CH_LOBBY_SECONDS, q_secs=CH_Q_SECONDS,
                 max_players=CH_MAX_PLAYERS, min_players=CH_MIN_PLAYERS, edit_gap=3.0)
        games[chat_id] = g
        g.live = await send(c.bot, g, lobby_text(g, int(g.lobby_secs)), lobby_markup(g))
        if g.live is None:
            games.pop(chat_id, None)
            await c.answer((t(L, "ch_publish_fail") + "\n\n" + send_errors.get(chat_id, ""))[:200], show_alert=True)
            return
        g.task = asyncio.create_task(run(c.bot, g))
        await c.answer(t(L, "ch_started_toast"))
        await c.message.answer(t(L, "ch_started"), parse_mode="HTML", reply_markup=kb(
            [btn(t(L, "gp_start_now"), f"ch:s:{chat_id}"), btn(t(L, "gp_cancel"), f"ch:x:{chat_id}")]))

    @pm.callback_query(F.data.regexp(r"^ch:t:-?\d+$"))
    async def cb_channel_test(c: CallbackQuery):
        """اختبار النشر: يرسل رسالة قصيرة في القناة ويحذفها، ويخبرك بالنتيجة أو بسبب الفشل بالضبط."""
        chat_id = int(c.data.split(":")[2])
        L = db.get_lang(c.from_user.id)
        if not await can_manage(c.bot, chat_id, c.from_user.id):
            await c.answer(t(L, "gp_host_only"), show_alert=True)
            return
        try:
            m = await c.bot.send_message(chat_id, "✅")
        except TelegramAPIError as e:
            await c.answer((t(L, "ch_publish_fail") + "\n\n" + str(e))[:200], show_alert=True)
            return
        try:
            await c.bot.delete_message(chat_id, m.message_id)
            note = t(L, "ch_test_ok")
        except TelegramAPIError:
            note = t(L, "ch_test_ok_nodel")
        await c.answer(note, show_alert=True)

    @pm.callback_query(F.data.regexp(r"^ch:(s|x):-?\d+$"))
    async def cb_channel_control(c: CallbackQuery):
        _, act, cid = c.data.split(":")
        chat_id = int(cid)
        L = db.get_lang(c.from_user.id)
        g = games.get(chat_id)
        if not g or g.state == "done" or not await can_manage(c.bot, chat_id, c.from_user.id):
            await c.answer(t(L, "gp_gone"), show_alert=True)
            return
        await c.answer()
        if act == "s" and g.state == "lobby":
            g.start_now = True
            g.wake.set()
        elif act == "x" and g.task:
            g.task.cancel()

    @cb.callback_query()
    async def cb_fallback(c: CallbackQuery):
        await c.answer()

    root.include_router(r)
    root.include_router(cb)
    root.include_router(pm)
    return root
