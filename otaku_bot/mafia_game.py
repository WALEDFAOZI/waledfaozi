"""لعبة المافيا بطابع أنمي داخل المجموعات والقنوات. المنطق النقي في mafia.py، وهنا التدفق مع تليجرام.

- الرسالة الحيّة الواحدة تُعدَّل (الانتظار ← الليل ← النهار)، فلا تتراكم الرسائل.
- كل دور يتلقى رسالته الخاصة مع أزرار ما يجب فعله. النهار يُحسم بالتصويت في المنشور العام.
- الأدوار سرّية حتى نهاية اللعبة.
"""
from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from dataclasses import dataclass, field

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message, ReplyParameters

from . import mafia as M
from . import progress
from . import ui
from .bot import btn, chan_row, esc, kb
from .ctx import Ctx
from . import live
from .links import back_rows, msg_rows, open_private_rows, with_rows
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re
from .texts import t
from .thread_anchor import anchor_id, reply_anchored

log = logging.getLogger(__name__)

LOBBY_SECS = 300
NIGHT_SECS = 60        # قتل المافيا
DISCUSS_SECS = 120    # نقاش الصباح قبل فتح التصويت
DAY_SECS = 60         # التصويت
MAX_ROUNDS = 15
QUIET_ROUNDS = 3        # جولات متتالية بلا قتل ولا طرد، ثم يختار النظام لاعبًا عشوائيًا للخروج
COOLDOWN_SECS = 60
EDIT_GAP = 3.0
DM_RETRY_SECS = 90      # إن تعذّر إرسال الدور لبعض اللاعبين: يُفتح اللوبي من جديد لهذه المدة
LOBBY_TICK = 10.0          # كم ثانية بين تحديثات عدّاد اللوبي
GROUP_TYPES = {"group", "supergroup"}
SPECIAL_ORDER = ["detective", "doctor", "mayor", "joker"]
ICON = {"killer": "🔪", "citizen": "🧑", "detective": "🔍", "doctor": "🩺", "mayor": "🎖", "joker": "🃏"}


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
    night_actions: dict = field(default_factory=dict)   # doctor -> هدف
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
    discuss_secs: int = DISCUSS_SECS  # وقت النقاش في النهار قبل التصويت
    voting: bool = False              # التصويت مفتوح (بعد انتهاء النقاش)
    last_protect: int | None = None   # من حماه الطبيب في الليلة الماضية: لا يُحمى مرتين متتاليتين
    reveal_death: bool = False        # إظهار دور القتيل/المطرود في الإعلان (افتراضيًا مخفي)
    day_mid: int | None = None        # رسالة التصويت الحالية (تُحدَّث مع كل صوت)
    day_text: str = ""
    quiet: int = 0                    # عدّاد الجولات المتتالية بلا موت
    news: list = field(default_factory=list)  # القناة: أخبار الجولة (رقم الجولة، النص) تُرسل خاصًّا للمشاركين
    status_text: str = ""             # القناة: الحالة الحالية (ليل/نهار/نهاية)
    status_markup: object = None
    discuss_line: str = ""            # سطر «النقاش في التعليقات» (القناة)
    discuss_url: str = ""             # رابط تعليقات المنشور: يظهر كزر في رسالة القناة
    mayor_revealed: bool = False      # العمدة كشف نفسه: صوته يُحسب مرتين من تلك اللحظة
    gone: bool = False                # الرسالة الحيّة حُذفت: تتوقف اللعبة
    joker_pick: int | None = None     # من سحب المجنون معه بعد طرده
    last_out: int | None = None       # آخر لاعب طُرد بالتصويت (يُذكر في نهاية اللعبة)
    discuss_post: int | None = None   # رقم المنشور في القناة: نجد نسخته في التعليقات ونرد عليها
    vote_deadline: float = 0.0        # نهاية التصويت (يمدّدها المضيف بزر في رسالة اللعبة)
    day_markup: object = None


games: dict[int, Game] = {}
cooldown: dict[int, float] = {}
counter = [0]


_POST_LINK = re.compile(r"t\.me/(?:c/(\d+)|([A-Za-z0-9_]{4,}))/(\d+)\?comment=(\d+)")


def parse_post_link(text: str) -> tuple[str | None, str | None, int, int] | None:
    """رابط رسالة من داخل تعليقات منشور: (اسم القناة، معرّفها الداخلي لروابط t.me/c، معرّف المنشور، معرّف التعليق)."""
    m = _POST_LINK.search(text)
    if not m:
        return None
    if m.group(1):                                 # رابط خاص: t.me/c/<id>/<post>?comment=<id>
        return None, m.group(1), int(m.group(3)), int(m.group(4))
    return m.group(2), None, int(m.group(3)), int(m.group(4))


def comment_link(username: str | None, channel_id: int, post_id: int, copy_id: int) -> str:
    """رابط تعليقات المنشور: يفتح المنشور على شاشة التعليقات."""
    if username:
        return f"https://t.me/{username}/{post_id}?comment={copy_id}"
    cid = str(channel_id)[4:] if str(channel_id).startswith("-100") else str(channel_id)
    return f"https://t.me/c/{cid}/{post_id}?comment={copy_id}"


ORDINAL_AR = {1: "الأولى", 2: "الثانية", 3: "الثالثة", 4: "الرابعة", 5: "الخامسة",
              6: "السادسة", 7: "السابعة", 8: "الثامنة", 9: "التاسعة", 10: "العاشرة"}
ORDINAL_AR_MASC = {1: "الأول", 2: "الثاني", 3: "الثالث", 4: "الرابع", 5: "الخامس",
                   6: "السادس", 7: "السابع", 8: "الثامن", 9: "التاسع", 10: "العاشر"}


def news_section(g: Game, key: tuple, items: list) -> str:
    """قسم في أخبار الجولة: «أخبار الصباح الأول» أو «أخبار النهار الأول» مع أخباره."""
    r, phase = key
    if g.lang == "en":
        head = (f"🌙 <b>Night {r} news</b>" if phase == "night" else f"☀️ <b>Day {r} news</b>")
    else:
        head = (f"🌙 <b>「 أخبار الليلة {ORDINAL_AR.get(r, str(r))} 」</b>" if phase == "night"
                else f"☀️ <b>「 أخبار النهار {ORDINAL_AR_MASC.get(r, str(r))} 」</b>")
    return head + "\n" + "\n".join(items)


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
        if p.role in ("doctor", "detective") and p.uid not in g.acted:
            return False
    return True


POST_ROOT: dict[tuple[int, int], tuple[int, int]] = {}   # (القناة، رقم المنشور) -> (مجموعة التعليقات، نسخة المنشور فيها)


def build_mafia_router(ctx: Ctx) -> Router:
    db, rng = ctx.db, ctx.rng
    root = Router(name="mafia")
    msgs = Router(name="mafia_msgs")
    msgs.message.filter(F.chat.type.in_(GROUP_TYPES))

    @msgs.message(F.is_automatic_forward)
    async def on_post_copy(m: Message):
        """نسخة المنشور في مجموعة التعليقات: نحفظ مكانها لنرد عليها."""
        if m.forward_from_chat and m.forward_from_message_id:
            POST_ROOT[(m.forward_from_chat.id, m.forward_from_message_id)] = (m.chat.id, m.message_id)
        raise SkipHandler()
    cbs = Router(name="mafia_cbs")
    cbs.callback_query.filter(F.message.chat.type.in_(GROUP_TYPES | {"channel"}))
    pm = Router(name="mafia_pm")
    pm.callback_query.filter(F.message.chat.type == "private")

    async def stop_hook(bot, chat_id: int, uid: int):
        """/stop: إيقاف اللعبة الجارية في هذه المجموعة (المضيف أو أدمن البوت)."""
        g = games.get(chat_id)
        if not g or g.task is None or g.task.done():
            return None
        if uid != g.host_id and not ctx.is_admin(uid):
            return "forbidden"
        g.task.cancel()
        return "stopped"
    ctx.stop_hooks.append(stop_hook)

    # ── الإرسال ───────────────────────────────────────────
    async def send(bot: Bot, g: Game, text: str, markup=None) -> int | None:
        """الرسالة الحيّة الوحيدة للعبة: تبدأ بلافتة وتُعدَّل بعد ذلك."""
        return await live.send(bot, g.chat_id, text, markup, lang=g.lang,
                               reply_to=g.reply_to if g.scope == "group" else None,
                               thread=g.thread if g.scope == "group" else None, kind="mafia")

    CHANNEL_CAP = 1000

    def channel_body(g: Game) -> str:
        """رسالة القناة: الحالة الحالية فقط (وسطر النقاش)، بلا سجل قديم. أثناء اللعب: عدد المافيا المتبقين."""
        killers = sum(1 for p in g.players.values() if p.alive and p.role == "killer")
        left = [t(g.lang, "mf_killers_left", n=killers)] if g.state not in ("lobby", "done") else []
        return "\n\n".join(([g.discuss_line] if g.discuss_line else []) + [g.status_text] + left)

    async def flush_news(bot: Bot, g: Game) -> None:
        """يرسل أخبار كل جولة في رسالة خاصة واحدة لكل مشارك: أخبار الصباح وأخبار النهار منفصلتان."""
        if not g.news:
            return
        sections: list[str] = []
        cur, buf = None, []
        for r, phase, text in g.news:
            if (r, phase) != cur and buf:
                sections.append(news_section(g, cur, buf))
                buf = []
            cur = (r, phase)
            buf.append(text)
        if buf:
            sections.append(news_section(g, cur, buf))
        g.news = []
        text = "\n\n".join(sections)
        for uid in list(g.players):
            try:
                await bot.send_message(uid, text, parse_mode="HTML", protect_content=True)
            except TelegramAPIError:
                pass                                       # لم يبدأ البوت بالخاص

    async def show(bot: Bot, g: Game, text: str, markup=None, status: bool = False) -> int | None:
        """المجموعات: كل رسالة جديدة. القناة: رسالة واحدة تحمل آخر الإعلانات والحالة الحالية."""
        if g.scope == "channel" and g.live is not None:
            if status:
                await flush_news(bot, g)                   # أخبار الجولة السابقة تصل قبل الحالة الجديدة
                g.status_text, g.status_markup = text, with_discuss(g, markup)
            else:
                g.news.append((g.round, "night" if g.state == "night" else "day", text))
            await ledit(bot, g, g.live, channel_body(g), g.status_markup)
            return g.live
        mid = await send(bot, g, text, markup)
        if g.live is None:
            g.live = mid
        return mid

    async def joker_pick(bot: Bot, g: Game, joker_uid: int) -> None:
        """المجنون طُرد: يكشف دوره، ويختار أحد الأحياء يسحبه معه خلال 60 ثانية، وإلا يختار البوت."""
        L = g.lang
        others = [p for p in alive_players(g) if p.uid != joker_uid]
        if not others or g.gone:
            return
        g.state, g.joker_pick = "joker", None
        rows = [[btn(p.name[:24], f"mf:jk:{g.gid}:{p.uid}")] for p in others]
        await show(bot, g, t(L, "mf_joker_out", name=esc(g.players[joker_uid].name), s=60), kb(*rows), status=True)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and g.joker_pick is None and not g.gone:
            await asyncio.sleep(0.5)
        victim = g.joker_pick if g.joker_pick is not None else rng.choice(sorted(p.uid for p in others))
        g.players[victim].alive = False
        g.joker_pick = victim
        g.state = "day"
        await show(bot, g, t(L, "mf_joker_took", joker=esc(g.players[joker_uid].name), victim=esc(g.players[victim].name)), None)

    def mark_gone(g: Game) -> None:
        g.gone = True
        g.state = "done"

    async def ledit(bot: Bot, g: Game, mid: int, text: str, markup=None, media=None) -> bool:
        """تعديل الرسالة الحيّة: إن حُذفت توقف اللعبة."""
        return await live.edit(bot, g.chat_id, mid, text, markup, media=media, on_gone=lambda: mark_gone(g))

    async def lobby_edit(bot: Bot, g: Game, text: str, markup=None) -> None:
        """اللوبي وحده يُعدَّل في مكانه: يعرض المنضمين والعدّاد."""
        if g.live is not None:
            await ledit(bot, g, g.live, text, markup)

    async def dm(bot: Bot, uid: int, text: str, markup=None) -> bool:
        try:
            await bot.send_message(uid, text, parse_mode="HTML", protect_content=True, reply_markup=markup)
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
        # بعد أن يكشف العمدة نفسه تظهر أيقونته في قائمة اللاعبين (اللوبي/الحالة الحيّة)
        return "\n".join(f"{ICON['mayor'] + ' ' if (g.mayor_revealed and p.role == 'mayor') else '• '}{esc(p.name)}" for p in ps) or "—"

    def lobby_text(g: Game, left: int) -> str:
        """رسالة البدء: مرتبة ومختصرة. الشرح الكامل في الخاص (زر «شرح اللعبة»)."""
        L = g.lang
        players = "\n".join(f"  • {esc(p.name)}" for p in g.players.values()) if g.players else "  —"
        return "\n".join([
            t(L, "mf_title"),
            "━━━━━━━━━━━━━━━━",
            f"👥 <b>{t(L, 'mf_players_label')}</b> ({len(g.players)}):",
            players,
            "━━━━━━━━━━━━━━━━",
            t(L, "mf_left", s=max(0, left), min=M.MIN_PLAYERS) + "\n" + ui.bar(left / max(1, g.lobby_secs)),
            f"<i>{t(L, 'mf_join_hint')}</i>",
        ] + ([g.discuss_line] if g.discuss_line else []))

    def with_discuss(g: Game, markup):
        """في القناة: زر النقاش يظهر مع كل رسالة حالة (ليل/نهار/لوبي)."""
        if not g.discuss_url:
            return markup
        return with_rows(markup, [[btn(t(g.lang, "mf_discuss_btn"), url=g.discuss_url)]]) if markup is not None \
            else kb([btn(t(g.lang, "mf_discuss_btn"), url=g.discuss_url)])

    def lobby_markup(g: Game):
        L = g.lang
        join_url = f"https://t.me/{g.me}?start=mf_{g.gid}"
        help_url = f"https://t.me/{g.me}?start=mfh"
        # انضم: سطر كامل أخضر. انسحب وشرح اللعبة جنب بعض. الرسالة فيها أصلًا زر يفتح البوت، فلا زر بوت إضافي.
        return with_discuss(g, kb([btn(t(L, "mf_join"), url=join_url, style="success")],
                                  [btn(t(L, "mf_leave"), f"mf:l:{g.gid}", style="danger"), btn(t(L, "mf_help_btn"), url=help_url)]))

    def config_text(g: Game) -> str:
        L = g.lang
        head = [t(L, "mf_post_started", link=g.discuss_url), ""] if (g.scope == "channel" and g.discuss_url) else []
        return "\n".join(head + [t(L, "mf_cfg_title"), "", roles_line(g, L), "", t(L, "mf_cfg_hint")])

    # حدود الأوقات (ثانية) وخطوة التعديل لكل مرحلة
    TIMES = {"lobby": (30, 600, 30), "night": (15, 300, 15), "discuss": (30, 600, 30), "day": (15, 300, 15)}

    def times_rows(g: Game) -> list:
        L = g.lang
        val = {"lobby": g.lobby_secs, "night": g.night_secs, "discuss": g.discuss_secs, "day": g.day_secs}
        rows = []
        for kind in ("lobby", "night", "discuss", "day"):
            lo, hi, step = TIMES[kind]
            rows.append([btn("➖", f"mf:tm:{g.gid}:{kind}:-"),
                         btn(t(L, f"mf_tm_{kind}", s=val[kind]), f"mf:tm:{g.gid}:{kind}:0"),
                         btn("➕", f"mf:tm:{g.gid}:{kind}:+")])
        return rows

    def config_markup(g: Game):
        L = g.lang
        rows = [[btn(t(L, "mf_auto_btn") + (" ✅" if g.auto else ""), f"mf:a:{g.gid}")],
                [btn(t(L, "mf_reveal_cfg") + (" ✅" if g.reveal_death else ""), f"mf:rd:{g.gid}")]]
        rows += [[btn("➖", f"mf:k:{g.gid}:-"), btn(t(L, "mf_killers_btn", k=g.killers), f"mf:k:{g.gid}:0"),
                  btn("➕", f"mf:k:{g.gid}:+")]]
        sp = [btn(("✅ " if r in g.specials else "") + t(L, "mf_r_" + r), f"mf:r:{g.gid}:{r}") for r in SPECIAL_ORDER]
        rows += [sp[:2], sp[2:]]
        rows += times_rows(g)
        if g.state != "lobby":                                  # أثناء اللعب: الإلغاء من هنا فقط
            return kb([btn(t(L, "mf_cancel"), f"mf:x:{g.gid}", style="danger")])
        rows.append([btn(t(L, "mf_start"), f"mf:s:{g.gid}"), btn(t(L, "mf_cancel"), f"mf:x:{g.gid}", style="danger")])
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
    async def lobby_phase(bot: Bot, g: Game, secs: int | None = None) -> None:
        start = time.monotonic()
        last = 0.0
        total = secs if secs is not None else g.lobby_secs
        while not g.start_now and g.state == "lobby":
            now = time.monotonic()
            left = total - (now - start) if secs is not None else g.lobby_secs - (now - start)     # المضيف قد يزيد الوقت أثناء الانتظار
            if left <= 0:
                return
            # تحديث فوري عند الانضمام/الخروج، وإلا كل LOBBY_TICK ثانية حتى ينزل العدّاد
            due = (g.dirty and now - last >= EDIT_GAP) or now - last >= LOBBY_TICK
            if due:
                g.dirty = False
                last = now
                await lobby_edit(bot, g, lobby_text(g, math.ceil(left)), lobby_markup(g))
            await asyncio.sleep(0.5)

    # ── الليل ─────────────────────────────────────────────
    async def night_phase(bot: Bot, g: Game) -> None:
        g.state = "night"
        g.round += 1
        g.night_picks, g.night_actions, g.acted = {}, {}, set()
        L = g.lang
        back = await back_rows(bot, g.chat_id, g.live, L)               # زر العودة إلى رسالة اللعبة
        await post_discuss(bot, g, t(L, "mf_night_comment", r=g.round))  # إشعار في تعليقات المنشور
        alive = alive_players(g)
        mayor = mayor_of(g)
        mayor_warn = t(L, "mf_mayor_warn", name=esc(mayor.name)) if (mayor and g.mayor_revealed) else ""
        for p in alive:
            if p.role == "killer":
                opts = [q for q in alive if q.role != "killer"]
                rows = [[btn(q.name[:24], f"mf:n:{g.gid}:killer:{q.uid}")] for q in opts]
            elif p.role == "doctor":
                rows = [[btn(q.name[:24], f"mf:n:{g.gid}:doctor:{q.uid}")] for q in alive if q.uid != g.last_protect]
            elif p.role == "detective":
                rows = [[btn(q.name[:24], f"mf:n:{g.gid}:{p.role}:{q.uid}")] for q in alive if q.uid != p.uid]
            else:
                continue
            text = t(L, f"mf_n_{p.role}")
            if p.role == "killer" and mayor_warn:
                text += "\n\n" + mayor_warn
            await dm(bot, p.uid, text, kb(*rows, *back))
        await show(bot, g, t(L, "mf_night_live", r=g.round, s=g.night_secs, n=len(alive), names=names(g, True)),
                   kb(*await open_private_rows(bot, L)), status=True)
        deadline = time.monotonic() + g.night_secs
        reminded = False
        while time.monotonic() < deadline and g.state == "night" and not night_complete(g):
            if not reminded and time.monotonic() > deadline - g.night_secs / 2:
                reminded = True
                await remind_night(bot, g)
            await asyncio.sleep(0.5)

    def resolve_night(g: Game):
        roles = {p.uid: p.role for p in g.players.values()}
        alive = {p.uid for p in alive_players(g)}
        picks = {k: tgt for k, tgt in g.night_picks.items() if g.players.get(k) and g.players[k].alive}   # من غادر لا يقتل
        killers_alive = any(p.role == "killer" and p.alive for p in g.players.values())
        pool = [p.uid for p in alive_players(g) if p.role != "killer"]
        kills = M.strike_targets(picks, alive, rng, killers_alive, pool)     # ضربة لكل قاتل حيّ اختار (أو ضربة واحدة أقل من 6)
        protect = {}
        for r in ("doctor",):                       # الحماية تسري فقط إن كان صاحب الدور ما زال حيًّا
            if r in g.night_actions and g.night_actions[r] in alive and any(p.role == r and p.alive for p in g.players.values()):
                protect[r] = g.night_actions[r]
        return M.resolve_night(roles, alive, M.Night(kills=kills, protect=protect))

    # ── النهار ────────────────────────────────────────────
    async def day_phase(bot: Bot, g: Game) -> int | None:
        g.state = "day"
        g.votes = {}
        g.voting = False
        L = g.lang
        alive = alive_players(g)
        # ١) النقاش: بلا أزرار تصويت، والأحياء يُنبَّهون بمكان النقاش
        g.day_text = t(L, "mf_discuss_live", r=g.round, s=g.discuss_secs, names=names(g, True))
        g.day_markup = None
        g.day_mid = await show(bot, g, g.day_text, g.day_markup, status=True)
        await post_discuss(bot, g, g.day_text)                # النقاش يبدأ: نفس التحديث في تعليقات المنشور
        await notify_discuss_start(bot, g, alive)
        deadline = time.monotonic() + g.discuss_secs
        while time.monotonic() < deadline and g.state == "day" and not g.gone:
            await asyncio.sleep(0.5)
        if g.state != "day" or g.gone:
            return None
        # ٢) التصويت: تظهر الأزرار وتبدأ النافذة
        btns = [[btn(f"🗳 {p.name[:22]}", f"mf:v:{g.gid}:{p.uid}")] for p in alive]
        btns.append([btn(t(L, "mf_skip"), f"mf:v:{g.gid}:0")])
        btns.append([btn(t(L, "mf_extend_btn"), f"mf:xt:{g.gid}")])          # المضيف يمدّد التصويت دقيقة
        g.day_text = t(L, "mf_day_live", r=g.round, s=g.day_secs, names=names(g, True))
        g.day_markup = kb(*btns)
        g.voting = True
        if g.scope == "channel":
            await show(bot, g, g.day_text, g.day_markup, status=True)
        else:
            await ledit(bot, g, g.day_mid, g.day_text, g.day_markup)
        await post_discuss(bot, g, g.day_text)                # بدأ التصويت: يظهر في التعليقات أيضاً
        await notify_vote_start(bot, g, alive)
        await notify_mayor(bot, g)
        g.vote_deadline = time.monotonic() + g.day_secs
        reminded = False
        while time.monotonic() < g.vote_deadline and g.state == "day":
            if all(p.uid in g.votes for p in alive_players(g)):
                break
            if not reminded and time.monotonic() > g.vote_deadline - g.day_secs / 2:
                reminded = True
                await remind_vote(bot, g)
            await asyncio.sleep(0.5)
        g.voting = False                                    # أُغلق التصويت: لا أصوات بعد الآن
        missed = [p for p in alive_players(g) if p.uid not in g.votes]
        if missed:                                          # من لم يصوّت: صوته يُحسب على نفسه (لا يطرد أحدًا)
            names_missed = "، ".join(esc(p.name) for p in missed)
            await show(bot, g, t(L, "mf_self_votes", names=names_missed), None)
            await post_discuss(bot, g, t(L, "mf_self_votes", names=names_missed))
        tally: dict[int, int] = {}
        skips = 0
        weights = vote_weights(g)
        for voter_uid, tgt in g.votes.items():
            if voter_uid not in {p.uid for p in alive_players(g)}:
                continue
            if tgt:
                tally[tgt] = tally.get(tgt, 0) + weights.get(voter_uid, 1)
            else:
                skips += weights.get(voter_uid, 1)
        if tally or skips:
            lines = [f"• {esc(g.players[u].name)}: {n}" for u, n in sorted(tally.items(), key=lambda kv: -kv[1])]
            if skips:
                lines.append(t(L, "mf_vote_skip", n=skips))
            await show(bot, g, t(L, "mf_vote_results", lines="\n".join(lines)), None)
            await post_discuss(bot, g, t(L, "mf_vote_results", lines="\n".join(lines)))
        ballots = {v: tgt for v, tgt in g.votes.items() if tgt}
        return M.vote({p.uid for p in alive_players(g)}, ballots, weights)

    async def remind_night(bot: Bot, g: Game) -> None:
        """تذكير خاص لمن لم يتصرف بعد في الليل (القاتل والطبيب والمحقق)."""
        pending = [p for p in alive_players(g) if
                   (p.role == "killer" and p.uid not in g.night_picks) or
                   (p.role in ("doctor", "detective") and p.uid not in g.acted)]
        for p in pending:
            Lp = db.get_lang(p.uid)
            try:
                await bot.send_message(p.uid, t(Lp, "mf_night_remind"), parse_mode="HTML", protect_content=True)
            except TelegramAPIError:
                pass

    async def remind_vote(bot: Bot, g: Game) -> None:
        """تذكير خاص لمن لم يصوّت بعد، مع زر يفتح رسالة التصويت."""
        pending = [p for p in alive_players(g) if p.uid not in g.votes]
        for p in pending:
            Lp = db.get_lang(p.uid)
            rows = await msg_rows(bot, g.chat_id, g.day_mid, "btn_go_vote", Lp)
            try:
                await bot.send_message(p.uid, t(Lp, "mf_vote_remind"), parse_mode="HTML", protect_content=True, reply_markup=kb(*rows))
            except TelegramAPIError:
                pass

    def mayor_of(g: Game):
        return next((p for p in g.players.values() if p.role == "mayor" and p.alive), None)

    def vote_weights(g: Game) -> dict[int, int]:
        """صوت العمدة يُحسب مرتين بعد أن يكشف نفسه (ما دام حيًّا)."""
        m = mayor_of(g)
        return {m.uid: 2} if (m and g.mayor_revealed) else {}

    async def notify_mayor(bot: Bot, g: Game) -> None:
        """في بداية التصويت: رسالة خاصة للعمدة فيها زر «اكشف نفسي» (مرة واحدة فقط)."""
        m = mayor_of(g)
        if not m or g.mayor_revealed:
            return
        Lm = db.get_lang(m.uid)
        try:
            await bot.send_message(m.uid, t(Lm, "mf_mayor_dm"), parse_mode="HTML", protect_content=True, reply_markup=kb(
                [btn(t(Lm, "mf_reveal_btn"), f"mf:rv:{g.gid}")]))
        except TelegramAPIError:
            pass

    @pm.callback_query(F.data.regexp(r"^mf:rv:\d+$"))
    async def cb_reveal(c: CallbackQuery):
        """العمدة يكشف نفسه أثناء النهار قبل إغلاق التصويت، مرة واحدة فقط."""
        L = db.get_lang(c.from_user.id)
        g = next((x for x in games.values() if x.gid == int(c.data.split(":")[2])), None)
        if not g or g.state != "day":
            await c.answer(t(L, "mf_late"), show_alert=True)
            return
        m = g.players.get(c.from_user.id)
        if not m:
            await c.answer(t(L, "mf_not_player"), show_alert=True)
            return
        if not m.alive or m.role != "mayor":
            await c.answer(t(L, "mf_not_yours"), show_alert=True)
            return
        if g.mayor_revealed:
            await c.answer(t(L, "mf_already_revealed"), show_alert=True)
            return
        g.mayor_revealed = True
        await c.answer()
        await show(c.bot, g, t(g.lang, "mf_mayor_revealed", name=esc(m.name)), None)

    async def notify_discuss_start(bot: Bot, g: Game, alive: list) -> None:
        """بداية النهار: رسالة خاصة لكل حي فيها زر يودي لمكان النقاش."""
        for p in alive:
            Lp = db.get_lang(p.uid)
            if g.discuss_url:                                   # القناة: الزر يودي لتعليقات المنشور مباشرة
                rows = [[btn(t(Lp, "btn_go_discuss"), url=g.discuss_url)]]
            else:
                rows = await msg_rows(bot, g.chat_id, g.day_mid, "btn_go_discuss", Lp)
            if not rows:
                return
            try:
                await bot.send_message(p.uid, t(Lp, "mf_discuss_dm", s=g.discuss_secs), parse_mode="HTML", protect_content=True,
                                       reply_markup=kb(*rows))
            except TelegramAPIError:
                pass

    async def notify_vote_start(bot: Bot, g: Game, alive: list) -> None:
        """رسالة خاصة لكل حي فيها زر يفتح رسالة التصويت مباشرة (في التعليقات إن كانت اللعبة فيها)."""
        for p in alive:
            Lp = db.get_lang(p.uid)
            rows = await msg_rows(bot, g.chat_id, g.day_mid, "btn_go_vote", Lp)
            if not rows:
                return
            try:
                await bot.send_message(p.uid, t(Lp, "mf_vote_dm"), parse_mode="HTML", protect_content=True, reply_markup=kb(*rows))
            except TelegramAPIError:
                pass                                        # لم يبدأ البوت بالخاص

    # ── إعلانات ───────────────────────────────────────────
    async def post_discuss(bot: Bot, g: Game, text: str) -> None:
        """تحديث في تعليقات المنشور نفسه (رد على نسخة المنشور في مجموعة التعليقات، بدون أدوار).
        إن لم يكن البوت رأى نسخة المنشور (مثلًا لم يكن عضوًا وقت نشره) فلا يُرسل شيء."""
        if not g.discuss_post:
            return
        root = POST_ROOT.get((g.chat_id, g.discuss_post))
        if not root:
            return
        chat_id, root_mid = root
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML",
                                   reply_parameters=ReplyParameters(message_id=root_mid, allow_sending_without_reply=False))
        except TelegramAPIError:
            pass

    async def announce_morning(bot: Bot, g: Game, res: M.Result) -> None:
        L = g.lang
        if res.victims:
            if len(res.victims) == 1:
                text = t(L, "mf_morning_dead", name=esc(g.players[res.victims[0]].name))
            else:
                names = "، ".join(esc(g.players[v].name) for v in res.victims)
                text = t(L, "mf_morning_dead_many", names=names)
            if g.reveal_death:
                text += "".join("\n" + role_line(g, v) for v in res.victims)
            for v in res.victims:                           # كل قتيل يتلقى رسالته الدرامية في الخاص
                await dm(bot, g.players[v].uid, t(db.get_lang(g.players[v].uid), "mf_you_died"))
        elif res.saved:
            text = t(L, "mf_morning_saved")
        else:
            text = t(L, "mf_morning_quiet")
        await show(bot, g, text, None)
        await post_discuss(bot, g, text)

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
        for p in g.players.values():                        # إحصائيات المافيا الشخصية
            db.record_outcome(p.uid, "mafia", "draw" if not w else ("win" if p.uid in won else "lose"))
        head = t(L, f"mf_end_{w}") if w else t(L, "mf_end_draw")
        if g.last_out is not None and g.last_out in g.players:     # يوضح آخر طرد بالتصويت ودوره
            voted = g.players[g.last_out]
            if voted.role == "killer":
                head += "\n" + t(L, "mf_vote_killer", name=esc(voted.name))
            else:
                head += "\n" + t(L, "mf_vote_other", name=esc(voted.name), role=t(L, "mf_r_" + voted.role))
        reveal = "\n".join(
            f"{ICON[p.role]} {esc(p.name)} — {t(L, 'mf_r_' + p.role)}{' ✅' if p.uid in won else ''}"
            for p in g.players.values())
        result = t(L, "mf_end", head=head, reveal=reveal, rounds=g.round)
        await show(bot, g, result, kb(*chan_row(L, bot_link=True)) or None, status=True)
        await post_discuss(bot, g, result)                  # النتيجة كاملة في تعليقات المنشور (انتهت اللعبة، الأدوار تنكشف)
        for p in g.players.values():                        # وكل لاعب يستلمها في الخاص
            await dm(bot, p.uid, result)
        for p in g.players.values():
            if db.is_admin(p.uid):
                continue
            db.add_group_result(g.chat_id, p.uid, 100 if p.uid in won else 30, "mafia", p.uid in won)
            progress.record(db, p.uid, "group", correct=g.round, won=p.uid in won)

    # ── الحلقة الرئيسية ───────────────────────────────────
    async def end_too_few(bot: Bot, g: Game) -> None:
        """لم يكتمل العدد: تُحذف رسالة اللوبي من القناة/المجموعة، وفي المجموعة يبقى التنبيه ثوانٍ ثم يُحذف."""
        L = g.lang
        lobby = g.live
        g.state = "done"
        g.start_now = True                                  # يوقف أي انتظار متبقٍ
        notice = None
        if g.scope != "channel":
            notice = await show(bot, g, t(L, "mf_too_few", min=M.MIN_PLAYERS), None)

        async def _delete(ids: list) -> None:
            for mid in ids:
                if mid is None:
                    continue
                try:
                    await bot.delete_message(g.chat_id, mid)
                except TelegramAPIError:
                    pass

        await _delete([lobby])                              # رسالة اللوبي تختفي فورًا
        if notice is not None and notice != lobby:
            async def _later():
                await asyncio.sleep(10)
                await _delete([notice])
            asyncio.create_task(_later())

    async def run(bot: Bot, g: Game) -> None:
        L = g.lang
        try:
            await lobby_phase(bot, g)
            if g.state != "lobby":
                return
            while True:
                if g.gone:
                    return
                if len(g.players) < M.MIN_PLAYERS:
                    await end_too_few(bot, g)
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
                killer_count = sum(1 for q in g.players.values() if q.role == "killer")
                for p in g.players.values():
                    text = t(L, "mf_role_dm", icon=ICON[p.role], role=t(L, "mf_r_" + p.role),
                             desc=t(L, "mf_desc_" + p.role), team=t(L, "mf_team_" + M.ROLES[p.role][1]))
                    if p.role == "killer" and killer_count > 1:            # القتلة يعرفون بعض
                        mates = [esc(q.name) for q in g.players.values() if q.role == "killer" and q.uid != p.uid]
                        text += "\n" + t(L, "mo_killer_mates", names="، ".join(mates))
                    ok = await dm(bot, p.uid, text)
                    if not ok:
                        failed.append(p.uid)
                if not failed:
                    break
                names = "، ".join(esc(g.players[u].name) for u in failed)
                for u in failed:                              # لا يصل إليه دوره: يُستبعد
                    g.players.pop(u, None)
                g.start_now = False
                g.dirty = True
                await show(bot, g, t(L, "mf_dm_removed", names=names, s=DM_RETRY_SECS), None)
                await lobby_phase(bot, g, DM_RETRY_SECS)      # اللوبي يُفتح من جديد لمدة قصيرة لينضم غيرهم
                if g.state != "lobby" or g.gone:
                    return
            roles_map = {p.uid: p.role for p in g.players.values()}
            while True:
                alive_at_start = len(alive_players(g))
                await night_phase(bot, g)
                res = resolve_night(g)
                g.last_protect = g.night_actions.get("doctor")   # الحماية تنتهي إن لم يحمِ الطبيب هذه الليلة
                for v in res.victims:
                    g.players[v].alive = False
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
                    await dm(bot, out, t(db.get_lang(out), "mf_you_voted"))
                    g.last_out = out
                    last = g.players[out].role
                    text = t(L, "mf_executed", name=esc(g.players[out].name))
                    public = text                                 # بدون دور: التعليقات لا تكشف الأدوار
                    if g.reveal_death and last != "joker":        # المجنون يُكشف دوره أصلًا
                        text += "\n" + role_line(g, out)
                    await show(bot, g, text, None)
                    await post_discuss(bot, g, public)
                    if last == "joker":                           # يكشف دوره ويسحب معه أحدًا (لا يفوز وحده)
                        await joker_pick(bot, g, out)
                else:
                    await show(bot, g, t(L, "mf_no_exec"), None)
                    await post_discuss(bot, g, t(L, "mf_no_exec"))
                died_this_round = len(alive_players(g)) < alive_at_start     # قتل أو طرد أو انسحاب
                if res.victims or out is not None or died_this_round:
                    g.quiet = 0
                else:
                    g.quiet += 1
                    if g.quiet >= QUIET_ROUNDS and alive_players(g):
                        pick = rng.choice(sorted(p.uid for p in alive_players(g)))
                        g.players[pick].alive = False
                        g.quiet = 0
                        await show(bot, g, t(L, "mf_quiet_death", name=esc(g.players[pick].name)), None)
                await flush_news(bot, g)                       # أخبار التصويت تصل فور انتهائه
                if g.gone:
                    return
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
            try:                                              # الخطأ يظهر في القناة/المجموعة بدل أن تقف اللعبة بصمت
                await show(bot, g, t(L, "mf_crashed"), None)
            except Exception:  # noqa: BLE001
                pass
        finally:
            g.state = "done"
            if g.gone:
                try:
                    await bot.send_message(g.host_id, t(g.lang, "mf_gone_stop"))
                except TelegramAPIError:
                    pass
            try:
                await flush_news(bot, g)                  # أي خبر متبقٍ (مثلًا عند الإلغاء) يصل للمشاركين
            except Exception:  # noqa: BLE001
                pass
            if games.get(g.chat_id) is g:
                games.pop(g.chat_id, None)
            cooldown[g.chat_id] = time.monotonic()

    def new_game(chat_id: int, scope: str, host_id: int, host_name: str, reply_to, thread, lang: str) -> Game:
        counter[0] += 1
        return Game(gid=counter[0], chat_id=chat_id, scope=scope, host_id=host_id, host_name=host_name,
                    lang=lang, reply_to=reply_to, thread=thread,
                    lobby_secs=LOBBY_SECS, night_secs=NIGHT_SECS, day_secs=DAY_SECS,
                    discuss_secs=DISCUSS_SECS)

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
            await reply_anchored(m, t(L, "mf_busy" if why == "busy" else "mf_cool"))
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
    @pm.message(CommandStart(deep_link=True, magic=F.args == "mfh"))
    async def on_help_start(m: Message):
        """شرح اللعبة في الخاص: رسالة مفصلة من زر «شرح اللعبة» في رسالة البدء."""
        L = db.get_lang(m.from_user.id)
        db.upsert_user(m.from_user.id, m.from_user.full_name)
        await m.answer(t(L, "mf_help_long"), parse_mode="HTML")

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
        if len(g.players) == M.MIN_PLAYERS:                 # اكتمل الحد الأدنى: المضيف يُبلَّغ مرة واحدة ويقدر يبدأ
            Lh = db.get_lang(g.host_id)
            try:
                await m.bot.send_message(g.host_id, t(Lh, "mf_ready_host", n=len(g.players)), parse_mode="HTML",
                                         reply_markup=kb([btn(t(Lh, "mf_start"), f"mf:s:{g.gid}")]))
            except TelegramAPIError:
                pass

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

    @pm.callback_query(F.data.regexp(r"^mf:r:\d+:(detective|doctor|mayor|joker)$"))
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

    def role_line(g: Game, uid: int) -> str:
        L = g.lang
        return t(L, "mf_role_shown", role=t(L, "mf_r_" + g.players[uid].role))

    @pm.callback_query(F.data.regexp(r"^mf:rd:\d+$"))
    async def cb_reveal_cfg(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        g = host_game(c, int(c.data.split(":")[2]))
        if not g:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        g.reveal_death = not g.reveal_death
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

    @pm.callback_query(F.data.regexp(r"^mf:tm:\d+:(lobby|night|discuss|day):[-+0]$"))
    async def cb_times(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        _, _, gid, kind, op = c.data.split(":")
        g = host_game(c, int(gid))
        if not g:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        lo, hi, step = TIMES[kind]
        attr = {"lobby": "lobby_secs", "night": "night_secs", "discuss": "discuss_secs", "day": "day_secs"}[kind]
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

    @pm.callback_query(F.data.regexp(r"^mf:x:\d+$"))             # من الخاص (زر المضيف في رسالته الخاصة)
    @cbs.callback_query(F.data.regexp(r"^mf:x:\d+$"))            # ومن المجموعات والقنوات
    async def cb_cancel(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        g = next((x for x in games.values() if x.gid == int(c.data.split(":")[2])), None)
        if not g or c.from_user.id != g.host_id:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        await c.answer()
        if g.task:
            g.task.cancel()

    @cbs.callback_query(F.data.regexp(r"^mf:jk:\d+:\d+$"))
    async def cb_joker_pick(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        _, _, gid, tgt = c.data.split(":")
        g = get_game(c, int(gid))
        if not g or g.state != "joker" or g.joker_pick is not None:
            await c.answer(t(L, "mf_late"), show_alert=True)
            return
        presser = g.players.get(c.from_user.id)
        target = int(tgt)
        if not presser:
            await c.answer(t(L, "mf_not_player"), show_alert=True)
            return
        if not presser.alive or target == presser.uid or target not in g.players or not g.players[target].alive:
            await c.answer(t(L, "mf_bad_target"), show_alert=True)
            return
        g.joker_pick = target
        await c.answer()

    @cbs.callback_query(F.data.regexp(r"^mf:xt:\d+$"))
    async def cb_extend_vote(c: CallbackQuery):
        """المضيف يمدّد التصويت دقيقة من داخل رسالة اللعبة نفسها."""
        L = db.group_lang(c.message.chat.id)
        g = get_game(c, int(c.data.split(":")[2]))
        if not g or g.state != "day" or not g.voting:
            await c.answer(t(L, "mf_late"), show_alert=True)
            return
        if c.from_user.id != g.host_id and not await can_control(c.bot, g, c.from_user.id):
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        g.vote_deadline += 60
        await c.answer(t(L, "mf_extended"))

    @cbs.callback_query(F.data.regexp(r"^mf:v:\d+:\d+$"))
    async def cb_vote(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        _, _, gid, tgt = c.data.split(":")
        g = get_game(c, int(gid))
        if not g or g.state != "day":
            await c.answer(t(L, "mf_late"), show_alert=True)
            return
        if not g.voting:
            await c.answer(t(L, "mf_discuss_wait"), show_alert=True)
            return
        voter = g.players.get(c.from_user.id)
        if not voter:
            await c.answer(t(L, "mf_not_player"), show_alert=True)
            return
        if not voter.alive:
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
            pending = [esc(p.name) for p in alive if p.uid not in g.votes]
            status = (t(L, "mf_vote_pending", names="\n" + "\n".join(f"• {n}" for n in pending)) if pending
                      else t(L, "mf_vote_all"))
            status += "\n" + t(L, "mf_vote_note")
            text = g.day_text + "\n\n" + status
            if g.scope == "channel":
                g.status_text = text
                await ledit(c.bot, g, g.day_mid, channel_body(g), g.status_markup)
            else:
                await ledit(c.bot, g, g.day_mid, text, g.day_markup)

    @cbs.callback_query(F.data.regexp(r"^mf:i:\d+$"))
    async def cb_info(c: CallbackQuery):
        L = db.group_lang(c.message.chat.id)
        await c.answer(t(L, "mf_info_toast")[:190], show_alert=True)

    # ── الخاص: أفعال الليل ────────────────────────────────
    @pm.callback_query(F.data.regexp(r"^mf:n:\d+:(killer|doctor|detective):\d+$"))
    async def cb_night(c: CallbackQuery):
        L = db.get_lang(c.from_user.id)
        _, _, gid, role, tgt = c.data.split(":")
        g = next((x for x in games.values() if x.gid == int(gid)), None)     # games مفاتيحها معرّف المجموعة
        if not g or g.state != "night":
            await c.answer(t(L, "mf_late"), show_alert=True)
            return
        p = g.players.get(c.from_user.id)
        if not p:
            await c.answer(t(L, "mf_not_player"), show_alert=True)
            return
        if not p.alive or p.role != role:
            await c.answer(t(L, "mf_not_yours"), show_alert=True)
            return
        target = int(tgt)
        tp = g.players.get(target)
        if role == "doctor" and target == g.last_protect:
            await c.answer(t(L, "mf_protect_repeat"), show_alert=True)
            return
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

    class PostPick(StatesGroup):
        link = State()

    @pm.callback_query(F.data.regexp(r"^mf:cs:-?\d+$"))
    async def cb_channel_choice(c: CallbackQuery, state: FSMContext):
        """اختيار مكان النقاش: القناة نفسها، أو تعليقات منشور."""
        L = db.get_lang(c.from_user.id)
        chat_id = int(c.data.split(":")[2])
        if db.channel_owner(chat_id) != c.from_user.id:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        await c.answer()
        await state.set_state(PostPick.link)                   # مباشرة: طلب رابط تعليق داخل المنشور
        await state.update_data(channel=chat_id)
        await c.message.answer(t(L, "mf_post_ask"), parse_mode="HTML")

    @pm.callback_query(F.data.regexp(r"^mf:cp:-?\d+$"))
    async def cb_post_place(c: CallbackQuery, state: FSMContext):
        """النقاش في تعليقات منشور: ينتظر رابط المنشور من المضيف."""
        L = db.get_lang(c.from_user.id)
        chat_id = int(c.data.split(":")[2])
        if db.channel_owner(chat_id) != c.from_user.id:
            await c.answer(t(L, "mf_host_only"), show_alert=True)
            return
        await c.answer()
        await state.set_state(PostPick.link)
        await state.update_data(channel=chat_id)
        await c.message.answer(t(L, "mf_post_ask"), parse_mode="HTML")

    @pm.message(PostPick.link, F.text)
    async def on_post_link(m: Message, state: FSMContext):
        """المضيف أرسل رابط تعليق داخل المنشور: اللعبة تبقى في القناة، والنقاش يكون في التعليقات."""
        L = db.get_lang(m.from_user.id)
        data = await state.get_data()
        chat_id = data.get("channel")
        if not chat_id or db.channel_owner(chat_id) != m.from_user.id:
            await state.clear()
            await m.answer(t(L, "mf_host_only"))
            return
        found = parse_post_link(m.text or "")
        if not found:
            await m.answer(t(L, "mf_post_bad"), parse_mode="HTML")
            return
        username, internal, post_id, comment_id = found
        try:
            ch = await m.bot.get_chat(chat_id)
        except TelegramAPIError:
            await m.answer(t(L, "mf_post_bad"), parse_mode="HTML")
            return
        if username and (ch.username or "").lower() != username.lower():
            await m.answer(t(L, "mf_post_bad"), parse_mode="HTML")
            return
        if internal is not None and str(chat_id) != f"-100{internal}":
            await m.answer(t(L, "mf_post_bad"), parse_mode="HTML")
            return
        why = busy_or_cool(chat_id)
        if why:
            await m.answer(t(L, "mf_busy" if why == "busy" else "mf_cool"))
            return
        await state.clear()
        url = comment_link(ch.username, chat_id, post_id, int(f"{comment_id}99"))   # رقمان 99 تفتح التعليقات
        g = new_game(chat_id, "channel", m.from_user.id, ch.title or "القناة", None, None, db.group_lang(chat_id))
        g.discuss_line = t(db.group_lang(chat_id), "mf_discuss_line")
        g.discuss_url = url
        g.discuss_post = post_id                                       # نسخة المنشور في التعليقات تصل تلقائيًا للبوت
        linked = getattr(ch, "linked_chat_id", None)
        if linked and (chat_id, post_id) not in POST_ROOT:
            # ما وصلت نسخة المنشور التلقائية بعد: نرد على التعليق الذي أرسله المضيف (داخل خيط المنشور نفسه).
            # نسخة المنشور الحقيقية (إن وصلت لاحقًا) تستبدله تلقائيًا في on_post_copy.
            POST_ROOT[(chat_id, post_id)] = (linked, comment_id)
        in_discuss = False
        if linked:
            try:
                me = await m.bot.get_me()
                member = await m.bot.get_chat_member(linked, me.id)
                in_discuss = member.status in ("member", "administrator", "creator")
            except TelegramAPIError:
                in_discuss = False
        if not in_discuss:                                             # تحذير المضيف في الخاص: التحديثات لن تصل للتعليقات
            try:
                await m.bot.send_message(m.from_user.id, t(L, "mf_no_discuss_warn", ch=esc(ch.title or "")), parse_mode="HTML")
            except TelegramAPIError:
                pass
        if not await open_lobby(m.bot, g):
            await m.answer(t(L, "mf_post_bad"), parse_mode="HTML")
            return
        if not g.cfg_msg:                                              # إعدادات المضيف تحمل رابط النقاش؛ إن تعذّر إرسالها نرسل الرابط وحده
            await m.answer(t(L, "mf_post_started", link=url), parse_mode="HTML")

    @pm.callback_query(F.data.regexp(r"^mf:cc:-?\d+$"))
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
