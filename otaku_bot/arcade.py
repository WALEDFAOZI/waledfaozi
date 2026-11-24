"""ألعاب ثنائية: إكس أو، حجرة ورقة مقص، أربعة في صف. تُلعب أونلاين (طابور) أو تحدٍّ مع صديق بالرابط.

المنطق نقي وسهل الاختبار (الدوال في الأعلى)، والرسائل والأزرار بعده.
"""
from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, InputMediaPhoto, Message, ReplyParameters

from . import live, ui
from .resultcard import make_match_card
from .bot import btn, esc, kb
from .ctx import Ctx
from .texts import t

log = logging.getLogger(__name__)
KINDS = ("xo", "rps", "c4")
LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
RPS = {"r": "✊", "p": "✋", "s": "✌️"}
RPS_BEATS = {"r": "s", "p": "r", "s": "p"}
C4_ROWS, C4_COLS = 6, 7
SYM_XO = {0: "X", 1: "O"}
SYM_C4 = {0: "R", 1: "Y"}
EMOJI = {"X": "❌", "O": "⭕", "R": "🔴", "Y": "🟡", None: "⬜"}   # الرموز الموحّدة في ui.py للأدوار والحالات


# ── المنطق ──────────────────────────────────────────────
def xo_state(board: list) -> str | None:
    """الفائز X أو O، أو draw إن امتلأت اللوحة، أو None للاستمرار."""
    for a, b, c in LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return "draw" if all(board) else None


def c4_drop(grid: list, col: int, sym: str) -> int | None:
    """يسقط القرص في العمود. grid[r][c] حيث r=0 هو الأسفل. يرجع الصف، أو None إن امتلأ العمود."""
    for r in range(C4_ROWS):
        if grid[r][col] is None:
            grid[r][col] = sym
            return r
    return None


def c4_state(grid: list) -> str | None:
    for r in range(C4_ROWS):
        for c in range(C4_COLS):
            s = grid[r][c]
            if not s:
                continue
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                cells = [(r + dr * k, c + dc * k) for k in range(4)]
                if all(0 <= rr < C4_ROWS and 0 <= cc < C4_COLS and grid[rr][cc] == s for rr, cc in cells):
                    return s
    if all(grid[C4_ROWS - 1][c] is not None for c in range(C4_COLS)):
        return "draw"
    return None


def rps_result(a: str, b: str) -> int:
    """0 تعادل، 1 فاز a، 2 فاز b."""
    if a == b:
        return 0
    return 1 if RPS_BEATS[a] == b else 2


# ── المباراة ────────────────────────────────────────────
@dataclass
class Match:
    gid: int
    kind: str
    players: list[int]                 # [الأول، الثاني]
    names: dict[int, str]
    board: list = field(default_factory=list)
    turn: int = 0                      # فهرس اللاعب الذي عليه الدور (xo/c4)
    picks: dict = field(default_factory=dict)     # rps: uid -> اختيار هذه الجولة
    score: list = field(default_factory=lambda: [0, 0])
    last: str = ""                     # نتيجة الجولة الأخيرة (rps)
    msgs: dict = field(default_factory=dict)      # uid -> message_id (المباريات الخاصة)
    state: str = "play"                # join | play | done (join: بانتظار اللاعب الثاني في المجموعة/القناة)
    scope: str = "p"                   # p: خاص مع كل لاعب | c: رسالة واحدة في مجموعة أو قناة
    chat_id: int | None = None
    mid: int | None = None             # رسالة المجموعة/القناة الحيّة
    inline_id: str | None = None       # رسالة الوضع الداخلي (inline): تُعدَّل بمعرّفها، ولا توجد دردشة
    photo: bool = False                # رسالة المجموعة/القناة صورة اللافتة مع النص تعليقًا (رسالة واحدة)
    host: int | None = None            # من بدأ المباراة في المجموعة: يقدر يلغيها
    seq: int = 0                       # رقم النوبة الحالية: يتغيّر مع كل حركة، ويلغي تذكيرات النوبة السابقة


REMIND_SECS = 90                       # بعد هذه المدة بلا حركة يُذكَّر من عليه الدور
matches: dict[int, Match] = {}
user_match: dict[int, int] = {}
queue: dict[str, list[int]] = {k: [] for k in KINDS}
invites: dict[int, tuple[int, str]] = {}          # رقم الدعوة -> (صاحب الدعوة، النوع)
counter = [0]


def build_arcade_router(ctx: Ctx) -> Router:
    db, rng = ctx.db, ctx.rng
    r = Router(name="arcade")

    def L_(uid: int) -> str:
        return db.get_lang(uid)

    reminders: set[asyncio.Task] = set()     # مراجع المهام كي لا تُجمع قبل انتهائها

    def new_match(kind: str, a: int, b: int, names: dict) -> Match:
        counter[0] += 1
        m = Match(gid=counter[0], kind=kind, players=[a, b], names=names)
        m.board = [None] * 9 if kind == "xo" else [[None] * C4_COLS for _ in range(C4_ROWS)]
        matches[m.gid] = m
        user_match[a] = user_match[b] = m.gid
        return m

    def end(m: Match) -> None:
        m.state = "done"
        for uid in m.players:
            if user_match.get(uid) == m.gid:
                user_match.pop(uid, None)
        matches.pop(m.gid, None)

    def sym_of(m: Match, uid: int) -> str:
        idx = m.players.index(uid)
        return (SYM_XO if m.kind == "xo" else SYM_C4)[idx]

    def opp_name(m: Match, uid: int) -> str:
        return m.names[m.players[1 - m.players.index(uid)]]

    # ── العرض ───────────────────────────────────────────
    def render(m: Match, uid: int) -> tuple[str, object]:
        L = L_(uid)
        title = t(L, "ar_title_" + m.kind)
        head = f"{title}\n⚔️ {t(L, 'ar_vs', name=opp_name(m, uid))}"
        if m.kind == "rps":
            mine = m.picks.get(uid)
            status = t(L, "ar_rps_wait") if mine is None else t(L, "ar_rps_done")
            score = f"{m.score[m.players.index(uid)]} : {m.score[1 - m.players.index(uid)]}"
            text = "\n".join([head, t(L, "ar_score", s=score), status] + ([m.last] if m.last else []))
            rows = [[btn(RPS[k], f"ar:r:{m.gid}:{k}") for k in ("r", "p", "s")]] if mine is None else []
            return text, kb(*rows)
        mine_turn = m.players[m.turn] == uid
        status = t(L, "ar_your_turn") if mine_turn else t(L, "ar_their_turn")
        if m.kind == "xo":
            grid = [[EMOJI[m.board[r * 3 + c]] for c in range(3)] for r in range(3)]
            text = "\n".join([head, status, ""] + ["".join(row) for row in grid])
            rows = []
            for r in range(3):
                row = []
                for c in range(3):
                    i = r * 3 + c
                    label = EMOJI[m.board[i]] if m.board[i] else str(i + 1)
                    row.append(btn(label, f"ar:x:{m.gid}:{i}" if mine_turn and not m.board[i] else f"ar:n:{m.gid}"))
                rows.append(row)
            return text, kb(*rows)
        # أربعة في صف
        lines = ["".join(EMOJI[m.board[r][c]] for c in range(C4_COLS)) for r in range(C4_ROWS - 1, -1, -1)]
        text = "\n".join([head, status, ""] + lines + ["1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣"])
        cols = [btn(str(c + 1), f"ar:c:{m.gid}:{c}" if mine_turn and m.board[C4_ROWS - 1][c] is None else f"ar:n:{m.gid}")
                for c in range(C4_COLS)]
        return text, kb(cols)

    def chat_name(m: Match, uid: int) -> str:
        return esc(m.names.get(uid, "?"))

    def render_chat(m: Match, lang: str) -> tuple[str, object]:
        """رسالة واحدة في المجموعة/القناة: الجميع يرى نفس اللوحة، والحركة تُقبل من صاحب الدور فقط."""
        title = t(lang, "ar_title_" + m.kind)
        if m.state == "join":
            names = " ، ".join(chat_name(m, u) for u in m.players) or "—"
            text = "\n".join([title, t(lang, "ar_waiting", names=names)])
            return text, kb([btn(t(lang, "ar_join_btn"), f"ar:j:{m.gid}", style="success")])
        p1, p2 = m.players
        vs = f"{chat_name(m, p1)} ❌⭕ {chat_name(m, p2)}" if m.kind == "xo" else \
            f"{chat_name(m, p1)} 🔴🟡 {chat_name(m, p2)}" if m.kind == "c4" else \
            f"{chat_name(m, p1)} ⚔️ {chat_name(m, p2)}"
        if m.kind == "rps":
            score = f"{m.score[0]} : {m.score[1]}"
            done = " ، ".join(f"✅ {chat_name(m, u)}" for u in m.picks) or t(lang, "ar_rps_wait_chat")
            text = "\n".join([title, vs, t(lang, "ar_score", s=score), done] + ([m.last] if m.last else []))
            return text, kb([btn(RPS[k], f"ar:r:{m.gid}:{k}") for k in ("r", "p", "s")])
        turn = chat_name(m, m.players[m.turn])
        if m.kind == "xo":
            grid = ["".join(EMOJI[m.board[r * 3 + c]] for c in range(3)) for r in range(3)]
            text = "\n".join([title, vs, t(lang, "ar_chat_turn", name=turn), ""] + grid)
            rows = []
            for r in range(3):
                row = []
                for c in range(3):
                    i = r * 3 + c
                    if m.board[i]:
                        row.append(btn(EMOJI[m.board[i]], f"ar:n:{m.gid}"))
                    else:
                        row.append(btn(str(i + 1), f"ar:x:{m.gid}:{i}"))
                rows.append(row)
            return text, kb(*rows)
        lines = ["".join(EMOJI[m.board[r][c]] for c in range(C4_COLS)) for r in range(C4_ROWS - 1, -1, -1)]
        text = "\n".join([title, vs, t(lang, "ar_chat_turn", name=turn), ""] + lines + ["1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣"])
        cols = [btn(str(c + 1), f"ar:c:{m.gid}:{c}" if m.board[C4_ROWS - 1][c] is None else f"ar:n:{m.gid}")
                for c in range(C4_COLS)]
        return text, kb(cols)

    def chat_view(m: Match, lang: str):
        """نص ولوحة رسالة المجموعة/القناة، ومعها زر «إنهاء اللعبة» للمضيف."""
        text, markup = render_chat(m, lang)
        if markup is not None and getattr(markup, "inline_keyboard", None) is not None and m.state in ("join", "play"):
            markup.inline_keyboard.append([btn(t(lang, "g_stop"), f"ar:stop:{m.gid}", style="danger")])
        return text, markup

    def chat_lang(m: Match) -> str:
        return db.group_lang(m.chat_id) if m.chat_id else L_(m.players[0])

    async def edit_match_message(bot: Bot, m: Match, text: str, markup) -> None:
        """يعدّل رسالة المباراة: نص، أو تعليق الصورة إن كانت اللافتة معها."""
        if m.inline_id:
            target = {"inline_message_id": m.inline_id}
        else:
            target = {"chat_id": m.chat_id, "message_id": m.mid}
        if m.photo:                                            # صورة (مجموعة أو وضع داخلي): تعليق الصورة يُعدَّل
            await bot.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=markup, **target)
        else:
            await bot.edit_message_text(text, parse_mode="HTML", reply_markup=markup, **target)

    async def show_chat(bot: Bot, m: Match, lang: str = "ar", markup_override=None) -> None:
        text, markup = chat_view(m, lang)
        try:
            if m.inline_id or m.mid:
                await edit_match_message(bot, m, text, markup_override if markup_override is not None else markup)
            else:
                sent = await bot.send_message(m.chat_id, text, parse_mode="HTML", reply_markup=markup)
                m.mid = sent.message_id
        except TelegramAPIError:
            log.warning("arcade: cannot update chat message for match %s", m.gid)

    def waiting_for(m: Match) -> list[int]:
        """من عليه الدور الآن (xo/c4: لاعب واحد، rps: من لم يختر بعد)."""
        if m.kind == "rps":
            return [uid for uid in m.players if uid not in m.picks]
        return [m.players[m.turn]]

    def remind_secs() -> float:
        v = db.get_setting("arcade_remind_secs")          # يُضبط من لوحة الأدمن؛ 0 = بدون تذكير
        return REMIND_SECS if v is None else int(v)

    async def remind_later(bot: Bot, gid: int, seq: int) -> None:
        await asyncio.sleep(remind_secs())
        m = matches.get(gid)
        if not m or m.seq != seq or m.state != "play":
            return                                   # تغيّرت النوبة أو انتهت اللعبة
        for uid in waiting_for(m):
            text = t(L_(uid), "ar_turn_remind", name=esc(m.names.get(uid, "?")))
            try:
                if m.scope == "c" and m.chat_id:
                    await bot.send_message(m.chat_id, text, parse_mode="HTML")
                else:
                    await bot.send_message(uid, text, parse_mode="HTML")
            except TelegramAPIError:
                pass
        # تذكير واحد لكل نوبة؛ لا نكرر حتى تتحرك اللعبة

    def schedule_remind(bot: Bot, m: Match) -> None:
        m.seq += 1
        if remind_secs() <= 0:
            return
        task = asyncio.create_task(remind_later(bot, m.gid, m.seq))
        reminders.add(task)
        task.add_done_callback(reminders.discard)

    async def show_all(bot: Bot, m: Match) -> None:
        if m.state == "play":
            schedule_remind(bot, m)
        if m.scope == "c":
            await show_chat(bot, m)
            return
        for uid in m.players:
            text, markup = render(m, uid)
            mid = m.msgs.get(uid)
            try:
                if mid:
                    await bot.edit_message_text(text, chat_id=uid, message_id=mid, parse_mode="HTML", reply_markup=markup)
                else:
                    sent = await bot.send_message(uid, text, parse_mode="HTML", reply_markup=markup)
                    m.msgs[uid] = sent.message_id
            except TelegramAPIError:
                pass

    def result_png(m: Match, lang: str, summary: str) -> bytes | None:
        """بطاقة النتيجة كصورة (None إن فشل الرسم؛ اللعبة لا تتأثر)."""
        board = m.board if m.kind != "rps" else None
        scores = f"{m.score[0]} : {m.score[1]}" if m.kind == "rps" else None
        names = [m.names.get(u, "?") for u in m.players]
        title = t(lang, "ar_title_" + m.kind)
        try:
            return make_match_card(m.kind, board, names, title, summary, scores)
        except Exception:  # noqa: BLE001
            log.warning("arcade: result card failed for match %s", m.gid)
            return None

    async def edit_match_photo(bot: Bot, m: Match, png: bytes, caption: str, markup) -> None:
        """يستبدل صورة اللافتة في رسالة اللعبة بصورة النتيجة مع النص تعليقًا: تبقى رسالة واحدة."""
        target = {"inline_message_id": m.inline_id} if m.inline_id else {"chat_id": m.chat_id, "message_id": m.mid}
        media = InputMediaPhoto(media=BufferedInputFile(png, "result.jpg"), caption=caption, parse_mode="HTML")
        await bot.edit_message_media(media=media, reply_markup=markup, **target)

    async def send_card(bot: Bot, m: Match, lang: str, summary: str) -> None:
        """بطاقة النتيجة كصورة منفصلة (للمحادثات الخاصة فقط)."""
        png = await asyncio.to_thread(result_png, m, lang, summary)
        if not png:
            return
        targets = [m.chat_id] if m.chat_id else list(m.players)
        for chat in targets:
            try:
                await bot.send_photo(chat, BufferedInputFile(png, "result.jpg"), caption=summary)
            except TelegramAPIError:
                pass

    async def finish(bot: Bot, m: Match, result_for: dict[int, str], summary: str = "") -> None:
        lang = chat_lang(m)
        merged = False
        if m.scope == "c":
            text, _ = render_chat(m, lang)
            body = "\n".join([text.split("\n")[0], summary]) if summary else text
            markup = kb([btn(t(lang, "ar_again"), "ar:m")])
            if summary and m.photo:
                png = await asyncio.to_thread(result_png, m, lang, summary)
                if png:
                    try:
                        await edit_match_photo(bot, m, png, body, markup)
                        merged = True
                    except TelegramAPIError:
                        log.warning("arcade: cannot merge result card into match %s", m.gid)
            if not merged:
                try:
                    await edit_match_message(bot, m, body, markup)
                except TelegramAPIError:
                    pass
        else:
            for uid in m.players:
                L = L_(uid)
                text, _ = render(m, uid)
                body = text.split("\n")[0] + "\n" + result_for.get(uid, "")
                try:
                    await bot.edit_message_text(body, chat_id=uid, message_id=m.msgs[uid], parse_mode="HTML",
                                                reply_markup=kb([btn(t(L, "ar_again"), "ar:m")]))
                except (TelegramAPIError, KeyError):
                    pass
        if summary and not merged:
            await send_card(bot, m, lang, summary)
        end(m)

    def record(m: Match, winner: int | None) -> None:
        for i, uid in enumerate(m.players):
            outcome = "draw" if winner is None else ("win" if i == winner else "lose")
            db.record_outcome(uid, m.kind, outcome)

    async def xo_or_c4_outcome(bot: Bot, m: Match, win: str | None) -> bool:
        """يُعلن النتيجة إن انتهت اللعبة. True إن انتهت."""
        if win is None:
            return False
        record(m, None if win == "draw" else (0 if win == sym_of(m, m.players[0]) else 1))
        lang = chat_lang(m)
        if win == "draw":
            summary = t(lang, "ar_chat_draw")
        else:
            winner = m.players[0] if win == sym_of(m, m.players[0]) else m.players[1]
            summary = t(lang, "ar_chat_win", name=chat_name(m, winner))
        if m.scope == "c":
            await finish(bot, m, {}, summary)
            return True
        result = {}
        for uid in m.players:
            L = L_(uid)
            if win == "draw":
                result[uid] = t(L, "ar_draw")
            else:
                result[uid] = t(L, "ar_win") if sym_of(m, uid) == win else t(L, "ar_lose")
        await finish(bot, m, result, summary)
        return True

    async def start(bot: Bot, a: int, b: int, kind: str, names: dict) -> None:
        m = new_match(kind, a, b, names)
        await show_all(bot, m)

    # ── الطابور ─────────────────────────────────────────
    @r.callback_query(F.data.regexp(r"^ar:q:(xo|rps|c4)$"))
    async def cb_queue(c: CallbackQuery):
        kind = c.data.split(":")[2]
        uid, L = c.from_user.id, L_(c.from_user.id)
        db.upsert_user(uid, c.from_user.full_name)
        if uid in user_match:
            await c.answer(t(L, "ar_busy"), show_alert=True)
            return
        await c.answer()
        if any(x == uid for x in queue[kind]):
            return
        others = [x for x in queue[kind] if x != uid]
        if others:
            other = others[0]
            queue[kind].remove(other)
            names = {uid: c.from_user.full_name, other: db.get_user(other)["name"] if db.get_user(other) else "?"}
            await start(c.bot, other, uid, kind, names)
            return
        queue[kind].append(uid)
        await c.message.answer(t(L, "ar_queued"), parse_mode="HTML",
                               reply_markup=kb([btn(t(L, "ar_cancel"), f"ar:qc:{kind}", style="danger")]))

    @r.callback_query(F.data.regexp(r"^ar:qc:(xo|rps|c4)$"))
    async def cb_queue_cancel(c: CallbackQuery):
        kind = c.data.split(":")[2]
        queue[kind] = [x for x in queue[kind] if x != c.from_user.id]
        await c.answer(t(L_(c.from_user.id), "ar_cancelled"))

    # ── تحدّي الصديق بالرابط ─────────────────────────────
    @r.callback_query(F.data.regexp(r"^ar:f:(xo|rps|c4)$"))
    async def cb_invite(c: CallbackQuery):
        kind = c.data.split(":")[2]
        uid, L = c.from_user.id, L_(c.from_user.id)
        db.upsert_user(uid, c.from_user.full_name)
        if uid in user_match:
            await c.answer(t(L, "ar_busy"), show_alert=True)
            return
        counter[0] += 1
        invites[counter[0]] = (uid, kind)
        me = (await c.bot.get_me()).username
        link = f"https://t.me/{me}?start=ar_{counter[0]}"
        await c.answer()
        await c.message.answer(t(L, "ar_invite", game=t(L, "ar_title_" + kind), link=link), parse_mode="HTML")

    @r.message(CommandStart(deep_link=True, magic=F.args.startswith("ar_")))
    async def on_invite_start(m: Message):
        uid, L = m.from_user.id, L_(m.from_user.id)
        db.upsert_user(uid, m.from_user.full_name)
        try:
            code = int(m.text.split("ar_", 1)[1].split()[0])
        except (ValueError, IndexError):
            code = -1
        inv = invites.get(code)
        if not inv:
            await m.answer(t(L, "ar_invite_gone"))
            return
        host, kind = inv
        if host == uid:
            await m.answer(t(L, "ar_invite_self"))
            return
        if uid in user_match or host in user_match:
            await m.answer(t(L, "ar_busy"))
            return
        invites.pop(code, None)
        names = {host: db.get_user(host)["name"] if db.get_user(host) else "?", uid: m.from_user.full_name}
        await start(m.bot, host, uid, kind, names)

    # ── الحركات ─────────────────────────────────────────
    def _match_for(c: CallbackQuery, gid: int, kind: str) -> Match | None:
        m = matches.get(gid)
        if not m or m.kind != kind or m.state != "play" or c.from_user.id not in m.players:
            return None
        return m

    @r.callback_query(F.data.regexp(r"^ar:x:\d+:\d$"))
    async def cb_xo(c: CallbackQuery):
        _, _, gid, i = c.data.split(":")
        m = _match_for(c, int(gid), "xo")
        L = L_(c.from_user.id)
        if not m or m.players[m.turn] != c.from_user.id or m.board[int(i)]:
            await c.answer(t(L, "ar_not_now"), show_alert=True)
            return
        await c.answer()
        m.board[int(i)] = sym_of(m, c.from_user.id)
        m.turn = 1 - m.turn
        win = xo_state(m.board)
        if await xo_or_c4_outcome(c.bot, m, win):
            return
        await show_all(c.bot, m)

    @r.callback_query(F.data.regexp(r"^ar:c:\d+:\d$"))
    async def cb_c4(c: CallbackQuery):
        _, _, gid, col = c.data.split(":")
        m = _match_for(c, int(gid), "c4")
        L = L_(c.from_user.id)
        if not m or m.players[m.turn] != c.from_user.id or m.board[C4_ROWS - 1][int(col)] is not None:
            await c.answer(t(L, "ar_not_now"), show_alert=True)
            return
        await c.answer()
        c4_drop(m.board, int(col), sym_of(m, c.from_user.id))
        m.turn = 1 - m.turn
        win = c4_state(m.board)
        if await xo_or_c4_outcome(c.bot, m, win):
            return
        await show_all(c.bot, m)

    @r.callback_query(F.data.regexp(r"^ar:r:\d+:[rps]$"))
    async def cb_rps(c: CallbackQuery):
        _, _, gid, pick = c.data.split(":")
        m = _match_for(c, int(gid), "rps")
        L = L_(c.from_user.id)
        if not m or c.from_user.id in m.picks:
            await c.answer(t(L, "ar_not_now"), show_alert=True)
            return
        await c.answer()
        m.picks[c.from_user.id] = pick
        if len(m.picks) < 2:
            await show_all(c.bot, m)
            return
        a, b = m.players
        res = rps_result(m.picks[a], m.picks[b])
        if res:
            m.score[0 if res == 1 else 1] += 1
        if res == 0:
            m.last = t(L_(a), "ar_round_draw", a=RPS[m.picks[a]], b=RPS[m.picks[b]])
        else:
            m.last = t(L_(a), "ar_round", a=RPS[m.picks[a]], b=RPS[m.picks[b]],
                       w=m.names[a] if res == 1 else m.names[b])
        m.picks = {}
        if max(m.score) >= 2:
            winner = 0 if m.score[0] > m.score[1] else 1
            record(m, winner)
            lang = chat_lang(m)
            summary = t(lang, "ar_chat_win", name=chat_name(m, m.players[winner]))
            if m.scope == "c":
                await finish(c.bot, m, {}, summary)
                return
            result = {uid: (t(L_(uid), "ar_win") if i == winner else t(L_(uid), "ar_lose"))
                      for i, uid in enumerate(m.players)}
            await finish(c.bot, m, result, summary)
            return
        await show_all(c.bot, m)

    @r.callback_query(F.data.regexp(r"^ar:n(:\d+)?$"))
    async def cb_noop(c: CallbackQuery):
        await c.answer(t(L_(c.from_user.id), "ar_not_now"))

    async def chat_create(bot: Bot, chat_id: int, kind: str, starter: int | None, starter_name: str,
                          reply_to: ReplyParameters | None = None) -> None:
        counter[0] += 1
        m = Match(gid=counter[0], kind=kind, players=[], names={}, scope="c", chat_id=chat_id, state="join")
        m.board = [None] * 9 if kind == "xo" else [[None] * C4_COLS for _ in range(C4_ROWS)]
        matches[m.gid] = m
        m.host = starter
        lang = db.group_lang(chat_id)
        text, markup = chat_view(m, lang)
        try:                                                   # اللافتة والنص في رسالة واحدة (الصورة تعليقها النص)
            sent = await bot.send_photo(chat_id, await live.banner_media(lang, kind), caption=text,
                                        parse_mode="HTML", reply_markup=markup, reply_parameters=reply_to)
            m.mid, m.photo = sent.message_id, True
        except (TelegramAPIError, Exception):  # noqa: BLE001
            log.warning("arcade: banner not sent for %s", kind)
            sent = await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup, reply_parameters=reply_to)
            m.mid = sent.message_id
        if starter is not None:
            m.players.append(starter)
            m.names[starter] = starter_name
            user_match[starter] = m.gid
        await show_chat(bot, m)

    @r.message(Command("xo", "rps", "c4"), F.chat.type.in_({"group", "supergroup"}))
    async def cmd_chat(msg: Message):
        kind = msg.text.split()[0].lstrip("/").split("@")[0]
        kind = {"xo": "xo", "rps": "rps", "c4": "c4"}.get(kind, "xo")
        await chat_create(msg.bot, msg.chat.id, kind, msg.from_user.id, msg.from_user.full_name,
                          reply_to=ReplyParameters(message_id=msg.message_id, allow_sending_without_reply=True))

    @r.channel_post(Command("xo", "rps", "c4"))
    async def cmd_channel(msg: Message):
        kind = msg.text.split()[0].lstrip("/").split("@")[0]
        kind = {"xo": "xo", "rps": "rps", "c4": "c4"}.get(kind, "xo")
        await chat_create(msg.bot, msg.chat.id, kind, None, "")

    @r.callback_query(F.data.regexp(r"^ar:stop:\d+$"))
    async def cb_chat_stop(c: CallbackQuery):
        """المضيف (أو من في المباراة، أو أدمن البوت) ينهي المباراة الجارية في المجموعة/القناة."""
        m = matches.get(int(c.data.split(":")[2]))
        L = L_(c.from_user.id)
        if not m or m.scope != "c" or m.state == "done":
            await c.answer(t(L, "ar_not_now"), show_alert=True)
            return
        if not (c.from_user.id == m.host or c.from_user.id in m.players or db.is_admin(c.from_user.id)):
            await c.answer(t(L, "gp_host_only"), show_alert=True)
            return
        await c.answer()
        lang = chat_lang(m)
        try:
            await edit_match_message(c.bot, m, t(lang, "ar_cancelled"), None)
        except TelegramAPIError:
            pass
        end(m)

    async def stop_hook(bot: Bot, chat_id: int, uid: int):
        """/stop: إنهاء المباراة الجارية في هذه المجموعة (من بدأها أو اللاعبان أو أدمن البوت)."""
        ms = [m for m in matches.values() if m.scope == "c" and m.chat_id == chat_id and m.state != "done"]
        if not ms:
            return None
        m = ms[0]
        if not (uid == m.host or uid in m.players or ctx.is_admin(uid)):
            return "forbidden"
        try:
            await edit_match_message(bot, m, t(chat_lang(m), "ar_cancelled"), None)
        except TelegramAPIError:
            pass
        end(m)
        return "stopped"
    ctx.stop_hooks.append(stop_hook)

    @r.callback_query(F.data.regexp(r"^ar:g:(xo|rps|c4)$"))
    async def cb_chat_start(c: CallbackQuery):
        """من قائمة المجموعة أو القناة: يبدأ تحدٍّ ثنائي في نفس المحادثة (المنشئ هو اللاعب الأول في المجموعة)."""
        kind = c.data.split(":")[2]
        chat = c.message.chat
        uid, L = c.from_user.id, L_(c.from_user.id)
        if chat.type == "private":
            await c.answer(t(L, "ar_not_now"), show_alert=True)
            return
        if chat.type != "channel" and uid in user_match:
            await c.answer(t(L, "ar_busy"), show_alert=True)
            return
        await c.answer()
        starter = None if chat.type == "channel" else uid
        await chat_create(c.bot, chat.id, kind, starter, c.from_user.full_name)

    inline_matches: dict[str, int] = {}

    @r.callback_query(F.data.regexp(r"^ar:ij(p?):(xo|rps|c4)$"))
    async def cb_inline_join(c: CallbackQuery):
        """من رسالة الوضع الداخلي: أول ضغطة تفتح المباراة في نفس الرسالة، وأول لاعبين يلعبان."""
        photo, kind = c.data.split(":")[1] == "ijp", c.data.split(":")[2]     # ijp: النتيجة صورة اللافتة
        iid = c.inline_message_id
        uid, L = c.from_user.id, L_(c.from_user.id)
        if not iid:
            await c.answer(t(L, "ar_not_now"), show_alert=True)
            return
        gid = inline_matches.get(iid)
        m = matches.get(gid) if gid else None
        if m is None:
            counter[0] += 1
            m = Match(gid=counter[0], kind=kind, players=[], names={}, scope="c", chat_id=None,
                      inline_id=iid, state="join", photo=photo)
            m.board = [None] * 9 if kind == "xo" else [[None] * C4_COLS for _ in range(C4_ROWS)]
            matches[m.gid] = m
            inline_matches[iid] = m.gid
        if m.state != "join" or uid in m.players:
            await c.answer(t(L, "ar_chat_full" if m.state != "join" else "ar_chat_already"), show_alert=True)
            return
        if uid in user_match:
            await c.answer(t(L, "ar_busy"), show_alert=True)
            return
        await c.answer()
        m.players.append(uid)
        m.names[uid] = c.from_user.full_name
        user_match[uid] = m.gid
        if len(m.players) == 2:
            m.state = "play"
        await show_all(c.bot, m)

    @r.callback_query(F.data.regexp(r"^ar:j:\d+$"))
    async def cb_chat_join(c: CallbackQuery):
        gid = int(c.data.split(":")[2])
        m = matches.get(gid)
        uid, L = c.from_user.id, L_(c.from_user.id)
        if not m or m.scope != "c" or m.state != "join":
            await c.answer(t(L, "ar_chat_full"), show_alert=True)
            return
        if uid in m.players:
            await c.answer(t(L, "ar_chat_already"), show_alert=True)
            return
        if uid in user_match:
            await c.answer(t(L, "ar_busy"), show_alert=True)
            return
        await c.answer()
        m.players.append(uid)
        m.names[uid] = c.from_user.full_name
        user_match[uid] = m.gid
        if len(m.players) == 2:
            m.state = "play"
        await show_all(c.bot, m)

    @r.callback_query(F.data.regexp(r"^ar:k:(xo|rps|c4)$"))
    async def cb_game_pick(c: CallbackQuery):
        """لعبة واحدة من القائمة: خياران فقط، أونلاين أو تحدّي صديق."""
        kind = c.data.split(":")[2]
        L = L_(c.from_user.id)
        await c.answer()
        await c.message.answer(t(L, "ar_pick_mode", game=t(L, "ar_title_" + kind)), parse_mode="HTML",
                               reply_markup=kb([btn(t(L, "ar_online_btn"), f"ar:q:{kind}"),
                                                btn(t(L, "ar_friend_btn"), f"ar:f:{kind}")]))

    @r.callback_query(F.data == "ar:m")
    async def cb_menu(c: CallbackQuery):
        L = L_(c.from_user.id)
        await c.answer()
        rows = []
        for k in KINDS:
            rows.append([btn(t(L, "ar_title_" + k), f"ar:q:{k}"), btn(t(L, "ar_friend_btn"), f"ar:f:{k}")])
        await c.message.answer(t(L, "ar_menu"), parse_mode="HTML", reply_markup=kb(*rows))

    return r


def make_invite(uid: int, kind: str) -> int:
    """رقم دعوة لتحدٍّ ثنائي (يُستخدم في رابط ?start=ar_<رقم>). يُحفظ آخر 500 دعوة فقط."""
    counter[0] += 1
    invites[counter[0]] = (uid, kind)
    while len(invites) > 500:
        invites.pop(next(iter(invites)))
    return counter[0]
