"""لعب أونلاين مباشرة مع البوت: يختار اللاعب لعبة، ينتظر منافسًا في الطابور، ثم يتنافسان على نفس الأسئلة.
أفضل واحد (الأكثر صحيحًا، ثم الأسرع) يفوز، وتظهر النتيجة للاثنين. بدون خاص أو مجموعة أو قناة."""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, field

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery

from . import progress
from .bot import btn, esc, kb
from .config import ROOT
from .ctx import Ctx
from .texts import t

log = logging.getLogger(__name__)
KINDS = ("quiz", "tf")
ROUNDS = 8
ROUND_SECS = 20
QUEUE_SECS = 180
GAP_SECS = 2
LETTERS = ["A", "B", "C", "D"]


@dataclass
class Match:
    mid: int
    kind: str
    players: list[int]
    qs: list[dict] = field(default_factory=list)
    rnd: int = -1
    answers: dict = field(default_factory=dict)      # uid -> (choice, time)
    score: dict = field(default_factory=dict)
    msg: dict = field(default_factory=dict)          # uid -> message_id للسؤال الحالي
    total_ms: dict = field(default_factory=dict)
    state: str = "play"
    task: asyncio.Task | None = None


queue: dict[str, list[tuple[int, float]]] = {k: [] for k in KINDS}
matches: dict[int, Match] = {}
user_match: dict[int, int] = {}
counter = [0]


def build_online_router(ctx: Ctx) -> Router:
    db, rng = ctx.db, ctx.rng
    r = Router(name="online")
    r.callback_query.filter(F.message.chat.type == "private")

    def L_(uid: int) -> str:
        return db.get_lang(uid)

    def opp_card(other: int, L: str) -> str:
        """بطاقة المنافس بلا اسم أو معرّف: الترتيب وأرقامه فقط."""
        u = db.get_user(other) or {}
        games_n = db.conn.execute("SELECT COUNT(*) n FROM game_sessions WHERE tg_id=?", (other,)).fetchone()["n"]
        return t(L, "on_opp_card", rank=db.user_rank(other) or "—", best=f"{u['best_score'] or 0:.1f}",
                 tests=u["tests_taken"] or 0, sd=u["best_sudden"] or 0, games=games_n)

    async def send(bot: Bot, uid: int, text: str, markup=None, parse_mode_html: bool = True) -> int | None:
        try:
            return (await bot.send_message(uid, text, parse_mode="HTML" if parse_mode_html else None,
                                           reply_markup=markup)).message_id
        except TelegramAPIError:
            return None

    async def edit(bot: Bot, uid: int, mid: int | None, text: str, markup=None) -> None:
        if not mid:
            return
        try:
            await bot.edit_message_text(text, chat_id=uid, message_id=mid, parse_mode="HTML", reply_markup=markup)
        except TelegramAPIError:
            pass

    def pool_quiz(L: str) -> list[dict]:
        out = []
        for q in db.all_questions():
            if L == "en" and not q.q_en:
                continue
            out.append({"text": q.text(L), "opts": q.opts(L), "answer": q.answer})
        return out

    def pool_tf(L: str) -> list[dict]:
        data = json.loads((ROOT / "data" / "games.json").read_text(encoding="utf-8"))
        out = []
        for ar, en, val, *_ in data["tf"]:
            out.append({"text": en if L == "en" else ar, "opts": [t(L, "g_true"), t(L, "g_false")],
                        "answer": 0 if val else 1})
        return out

    def pick_questions(kind: str, L: str) -> list[dict]:
        pool = pool_quiz(L) if kind == "quiz" else pool_tf(L)
        return rng.sample(pool, min(ROUNDS, len(pool)))

    def q_markup(m: Match, uid: int, q: dict):
        n = len(q["opts"])
        btns = [btn(f"{LETTERS[i]}) {q['opts'][i][:40]}", f"on:a:{m.mid}:{m.rnd}:{i}") for i in range(n)]
        rows = [btns[i:i + 2] for i in range(0, n, 2)]
        return kb(*rows, [btn(t(L_(uid), "on_forfeit"), f"on:q:{m.mid}")])

    async def send_round(bot: Bot, m: Match) -> None:
        m.rnd += 1
        m.answers = {}
        q = m.qs[m.rnd]
        for uid in m.players:
            L = L_(uid)
            text = t(L, "on_round", n=m.rnd + 1, total=len(m.qs), q=esc(q["text"]),
                     opts="\n".join(f"<b>{LETTERS[i]})</b> {esc(o)}" for i, o in enumerate(q["opts"])),
                     secs=ROUND_SECS, a=m.score.get(uid, 0), b=m.score.get(_other(m, uid), 0))
            m.msg[uid] = await send(bot, uid, text, q_markup(m, uid, q))

    def _other(m: Match, uid: int) -> int:
        return m.players[1] if m.players[0] == uid else m.players[0]

    async def play(bot: Bot, m: Match) -> None:
        try:
            for uid in m.players:
                other = _other(m, uid)
                await send(bot, uid, opp_card(other, L_(uid)), parse_mode_html=True)
            await asyncio.sleep(GAP_SECS)
            for uid in m.players:
                await send(bot, uid, t(L_(uid), "on_started", kind=t(L_(uid), f"on_kind_{m.kind}"), secs=ROUND_SECS))
            await asyncio.sleep(GAP_SECS)
            for _ in range(len(m.qs)):
                if m.state != "play":
                    return
                await send_round(bot, m)
                end = time.monotonic() + ROUND_SECS
                while time.monotonic() < end and len(m.answers) < 2 and m.state == "play":
                    await asyncio.sleep(0.3)
                q = m.qs[m.rnd]
                for uid in m.players:
                    got = m.answers.get(uid)
                    if got:
                        ok = got[0] == q["answer"]
                        if ok:
                            m.score[uid] = m.score.get(uid, 0) + 1
                        m.total_ms[uid] = m.total_ms.get(uid, 0) + int((got[1] - (end - ROUND_SECS)) * 1000)
                    else:
                        m.total_ms[uid] = m.total_ms.get(uid, 0) + ROUND_SECS * 1000
                    txt = t(L_(uid), "on_reveal_ok" if got and got[0] == q["answer"] else "on_reveal_bad",
                            right=esc(q["opts"][q["answer"]]))
                    await edit(bot, uid, m.msg.get(uid), txt, None)
                await asyncio.sleep(GAP_SECS)
            await finish(bot, m)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("online match crashed %s", m.mid)
        finally:
            for uid in m.players:
                user_match.pop(uid, None)
            matches.pop(m.mid, None)

    async def finish(bot: Bot, m: Match) -> None:
        a, b = m.players
        def key(u):
            return (m.score.get(u, 0), -m.total_ms.get(u, 0))
        winner = a if key(a) > key(b) else b if key(b) > key(a) else None
        for uid in m.players:
            L = L_(uid)
            other = _other(m, uid)
            head = t(L, "on_draw") if winner is None else t(L, "on_win" if winner == uid else "on_lose")
            await send(bot, uid, t(L, "on_result", head=head, me=m.score.get(uid, 0), op=m.score.get(other, 0),
                                   n=len(m.qs), name=esc(db.get_user(other)["name"] or "?")))
            if uid == winner:
                progress.bonus(db, uid, "duel_win", 25, "duel_wins")
            progress.record(db, uid, "duel", correct=m.score.get(uid, 0), won=uid == winner)

    def to_queue_or_match(bot: Bot, uid: int, kind: str) -> bool:
        """يضيف اللاعب للطابور، أو يبدأ مباراة مع أول منافس. True إن بدأت مباراة."""
        for other, _ in queue[kind]:
            if other != uid and other not in user_match:
                queue[kind] = [x for x in queue[kind] if x[0] != other]
                counter[0] += 1
                L = L_(uid)
                m = Match(mid=counter[0], kind=kind, players=[other, uid])
                m.qs = pick_questions(kind, L)
                matches[m.mid] = m
                user_match[uid] = user_match[other] = m.mid
                m.task = asyncio.create_task(play(bot, m))
                return True
        queue[kind] = [x for x in queue[kind] if x[0] != uid] + [(uid, time.time())]
        return False

    @r.callback_query(F.data == "on:m")
    async def cb_menu(c: CallbackQuery):
        await c.answer()
        L = L_(c.from_user.id)
        await c.message.answer(t(L, "on_menu"), parse_mode="HTML", reply_markup=kb(
            *[[btn(t(L, f"on_kind_{k}"), f"on:j:{k}")] for k in KINDS], [btn(t(L, "btn_menu"), "menu")]))

    @r.callback_query(F.data.regexp(r"^on:j:(quiz|tf)$"))
    async def cb_join(c: CallbackQuery):
        uid, L = c.from_user.id, L_(c.from_user.id)
        kind = c.data.split(":")[2]
        db.upsert_user(uid, c.from_user.full_name)
        if uid in user_match:
            await c.answer(t(L, "on_busy"), show_alert=True)
            return
        await c.answer()
        started = to_queue_or_match(c.bot, uid, kind)
        if not started:
            await c.message.answer(t(L, "on_waiting", kind=t(L, f"on_kind_{kind}"), s=QUEUE_SECS), parse_mode="HTML",
                                   reply_markup=kb([btn(t(L, "on_cancel"), f"on:c:{kind}")]))
            asyncio.get_event_loop().call_later(QUEUE_SECS, lambda: asyncio.ensure_future(_expire(c.bot, uid, kind)))

    async def _expire(bot: Bot, uid: int, kind: str) -> None:
        if any(x[0] == uid for x in queue[kind]) and uid not in user_match:
            queue[kind] = [x for x in queue[kind] if x[0] != uid]
            await send(bot, uid, t(L_(uid), "on_timeout"))

    @r.callback_query(F.data.regexp(r"^on:c:(quiz|tf)$"))
    async def cb_cancel(c: CallbackQuery):
        kind = c.data.split(":")[2]
        queue[kind] = [x for x in queue[kind] if x[0] != c.from_user.id]
        await c.answer(t(L_(c.from_user.id), "on_cancelled"))

    @r.callback_query(F.data.regexp(r"^on:a:\d+:\d+:\d$"))
    async def cb_answer(c: CallbackQuery):
        _, _, mid, rnd, choice = c.data.split(":")
        m = matches.get(int(mid))
        L = L_(c.from_user.id)
        if not m or c.from_user.id not in m.players or int(rnd) != m.rnd or m.state != "play":
            await c.answer(t(L, "on_late"), show_alert=True)
            return
        if c.from_user.id in m.answers:
            await c.answer(t(L, "on_already"))
            return
        m.answers[c.from_user.id] = (int(choice), time.time())
        await c.answer(t(L, "on_saved"))

    @r.callback_query(F.data.regexp(r"^on:q:\d+$"))
    async def cb_forfeit(c: CallbackQuery):
        m = matches.get(int(c.data.split(":")[2]))
        if not m or c.from_user.id not in m.players:
            await c.answer()
            return
        await c.answer()
        other = _other(m, c.from_user.id)
        m.score[c.from_user.id] = -1                       # الانسحاب يخسر المباراة
        m.score[other] = max(m.score.get(other, 0), 0) + ROUNDS
        m.state = "done"
        if m.task:
            m.task.cancel()
        await finish(c.bot, m)

    return r
