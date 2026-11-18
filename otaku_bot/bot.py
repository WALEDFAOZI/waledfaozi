from __future__ import annotations

import asyncio
import html
import json
import logging
import time
from urllib.parse import quote

from aiogram import BaseMiddleware, Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (BufferedInputFile, CallbackQuery, FSInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, InputMediaPhoto, Message)

from . import card
from .config import LEVELS, ROOT
from .ctx import Ctx
from .quiz import (category_breakdown, compute_score, pick_category, pick_questions, progress_bar,
                   shuffle_options, title_for)
from .texts import cat_label, t
from .timeutil import week_start

log = logging.getLogger(__name__)
LETTERS = {"ar": ["أ", "ب", "ج", "د"], "en": ["A", "B", "C", "D"]}
GRACE_SECONDS = 2          # سماح لتأخر الشبكة
SUSPECT_FAST_RATIO = 0.7   # نسبة إجابات أسرع من ثانية تعتبر مشبوهة
MODE_SIZE = {"full": LEVELS * 5, "quick": 10, "category": 10, "sudden": LEVELS * 5, "daily": 5, "dq": 1, "duel": 7}


class Suggest(StatesGroup):
    wait = State()          # ننتظر اقتراح سؤال من اللاعب


class ClearState(BaseMiddleware):
    """أي زر يضغطه اللاعب يُلغي أي إدخال معلّق (كاقتراح سؤال) حتى لا يُفسَّر كلامه التالي بالغلط."""

    async def __call__(self, handler, event, data):
        st = data.get("state")
        if st is not None:
            await st.clear()
        return await handler(event, data)


SUGGEST_PER_DAY = 3
SUGGEST_MAX_PENDING = 5


def esc(s: str) -> str:
    return html.escape(str(s), quote=False)


def kb(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[r for r in rows if r])


def btn(text: str, data: str | None = None, url: str | None = None) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data, url=url)


INVITE_BADGES = [(1, "🌱", "سفير الأوتاكو", "Otaku Ambassador"), (3, "🤝", "جامع الشلّة", "Squad Gatherer"),
                 (5, "🔥", "قائد النقابة", "Guild Leader"), (10, "⚔️", "أسطورة الدعوات", "Recruiter Legend"),
                 (25, "👑", "إمبراطور الأوتاكو", "Otaku Emperor")]


def invite_badge(n: int):
    got = [b for b in INVITE_BADGES if n >= b[0]]
    return got[-1] if got else None


def badge_label(b, L: str) -> str:
    return f"{b[1]} {b[2] if L == 'ar' else b[3]}"


_CHAN = {"get": lambda: ""}   # يضبطها build_router: القناة الحالية (قابلة للتعديل من لوحة الأدمن)


def chan_row(L: str) -> list[list[InlineKeyboardButton]]:
    """صف زر «تعال للقناة وتفاعل مع الأوتاكو»، أو لا شيء إن لم تُضبط قناة."""
    ch = (_CHAN["get"]() or "").lstrip("@")
    return [[btn(t(L, "btn_channel"), url=f"https://t.me/{ch}")]] if ch else []


def menu_kb(L: str, top: list[list[InlineKeyboardButton]] | None = None,
            images: bool = False) -> InlineKeyboardMarkup:
    """القائمة الرئيسية قصيرة: الاختبار أولًا، والألعاب والمزيد في قوائم فرعية."""
    return kb(*(top or []),
              [btn(t(L, "btn_full"), "go")],
              [btn(t(L, "btn_daily"), "dy:m"), btn(t(L, "du_btn"), "du:new")],
              [btn(t(L, "btn_quick"), "qk"), btn(t(L, "btn_cat"), "cats")],
              [btn(t(L, "btn_games_menu"), "m:games"), btn(t(L, "btn_anime"), "an:m")],
              [btn(t(L, "btn_rank"), "lb:menu"), btn(t(L, "btn_profile"), "pf")],
              [btn(t(L, "btn_invite"), "iv"), btn(t(L, "btn_more"), "m:more")],
              *chan_row(L))


def games_kb(L: str, images: bool = False) -> InlineKeyboardMarkup:
    rows = [[btn(t(L, "btn_sudden"), "sd")]]
    if images:
        rows.append([btn(t(L, "btn_images"), "ct:images")])
    rows += [[btn(t(L, "g_tf"), "g:tf")], [btn(t(L, "g_song"), "g:song")], [btn(t(L, "g_ord"), "g:ord")],
             [btn(t(L, "g_char"), "g:char")], [btn(t(L, "g_quote"), "g:quote")], [btn(t(L, "btn_menu"), "menu")]]
    return kb(*rows)


def more_kb(L: str) -> InlineKeyboardMarkup:
    return kb([btn(t(L, "btn_stats"), "st")],
              [btn(t(L, "btn_suggest"), "sg"), btn(t(L, "btn_lang"), "lg:toggle")],
              [btn(t(L, "btn_menu"), "menu")])


def build_router(ctx: Ctx) -> Router:
    r = Router()
    db, rng, settings = ctx.db, ctx.rng, ctx.settings
    _CHAN["get"] = ctx.channel
    r.message.filter(F.chat.type == "private")                    # الخاص فقط؛ المجموعات لها router مستقل (group.py)
    r.callback_query.filter(F.message.chat.type == "private")
    r.callback_query.outer_middleware(ClearState())
    timers: dict[tuple[int, int], asyncio.Task] = {}
    sub_ok: dict[int, float] = {}      # من ثبت اشتراكه: لا نسأل تليجرام عنه ثانية قبل 30 ثانية (توازن بين السرعة وكشف من غادر القناة)
    me_cache: dict[str, str] = {}

    def pub(u) -> str:
        """الاسم الذي يراه الآخرون: الأدمن/المالك لا يظهر اسمه أبدًا."""
        return "مجهول 🎭" if db.is_admin(u["tg_id"]) else (u["name"] or "?")

    async def bot_username(bot: Bot) -> str:
        if "u" not in me_cache:
            me_cache["u"] = (await bot.get_me()).username
        return me_cache["u"]

    def lang(uid: int) -> str:
        return db.get_lang(uid)

    def welcome_for(L: str, user) -> str:
        """يا هلا والله {الاسم}! — الاسم الأول للمستخدم (وإن لم يوجد فالاسم الكامل)."""
        first = (getattr(user, "first_name", None) or getattr(user, "full_name", None) or "").strip()
        return t(L, "welcome", name=esc(first[:30]) or ("صديقي" if L == "ar" else "friend"))

    def menu(L: str, top=None) -> InlineKeyboardMarkup:
        return menu_kb(L, top, images=db.category_counts(L).get("images", 0) >= 10)

    # ── الاشتراك الإجباري ───────────────────────────────────
    async def subscribed(bot: Bot, tg_id: int) -> bool | None:
        """True مشترك، False غير مشترك، None تعذّر التحقق (غالبًا البوت ليس أدمن بالقناة)."""
        ch = ctx.channel()
        if not ch:
            return True
        if ctx.is_admin(tg_id):
            return True
        if time.time() - sub_ok.get(tg_id, 0) < 30:
            return True
        try:
            member = await bot.get_chat_member(ch, tg_id)
        except TelegramAPIError as e:
            log.warning("cannot verify subscription to %s (is the bot an admin there?): %s", ch, e)
            return None
        ok = member.status in ("creator", "administrator", "member") or (
            member.status == "restricted" and getattr(member, "is_member", False))
        if ok:
            sub_ok[tg_id] = time.time()
        return ok

    def note_join(tg_id: int) -> None:
        """من طُلب منه الاشتراك ثم صار مشتركًا = «اشترك عبر البوت» (يُحسب مرة واحدة)."""
        if ctx.channel() and not ctx.is_admin(tg_id) and db.has_event(tg_id, "gate_prompt") \
                and not db.has_event(tg_id, "gate_joined"):
            db.log_event(tg_id, "gate_joined")

    async def gate(bot: Bot, chat_id: int, tg_id: int) -> bool:
        ok = await subscribed(bot, tg_id)
        if ok:
            note_join(tg_id)
            return True
        L = lang(tg_id)
        if ok is None:
            await bot.send_message(chat_id, t(L, "sub_unverifiable"))
        else:
            if not db.has_event(tg_id, "gate_prompt"):
                db.log_event(tg_id, "gate_prompt")
            ch = ctx.channel()
            await bot.send_message(
                chat_id, t(L, "sub_required", ch=esc(ch)), parse_mode="HTML",
                reply_markup=kb([btn(t(L, "btn_subscribe"), url=f"https://t.me/{ch.lstrip('@')}")],
                                [btn(t(L, "btn_checked"), "chk")]))
        return False

    ctx.subscribed, ctx.gate = subscribed, gate            # يستعملها حارس الاشتراك على كل الأزرار (app.SubGate)

    # ── عرض الرسائل (نص/صورة) ──────────────────────────────
    async def render(bot: Bot, chat_id: int, sid: int, text: str, markup, photo: str | None = None) -> bool:
        """يعرض رسالة الجلسة: يعدّل الموجودة إن أمكن، وإلا يحذفها ويرسل جديدة.
        يرجع False فقط إذا تعذّر تحميل صورة السؤال."""
        sess = db.get_session(sid)
        kind = "photo" if photo else "text"
        mid = sess["message_id"]
        if mid and sess["msg_kind"] == kind:
            try:
                if photo:
                    await bot.edit_message_media(
                        InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"),
                        chat_id=chat_id, message_id=mid, reply_markup=markup)
                else:
                    await bot.edit_message_text(text, chat_id=chat_id, message_id=mid,
                                                reply_markup=markup, parse_mode="HTML")
                return True
            except TelegramBadRequest as e:
                if "not modified" in str(e).lower():
                    return True
        if mid:
            try:
                await bot.delete_message(chat_id, mid)
            except TelegramAPIError:
                pass
            db.set_message(sid, 0, "text")
        try:
            if photo:
                m = await bot.send_photo(chat_id, photo, caption=text, reply_markup=markup, parse_mode="HTML")
            else:
                m = await bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")
        except TelegramBadRequest as e:
            if not photo:
                raise
            log.warning("photo failed (%s): %s", photo[:60], e)
            return False
        db.set_message(sid, m.message_id, kind)
        return True

    def question_text(sid: int, pos: int):
        sess = db.get_session(sid)
        row = db.session_question(sid, pos)
        q = db.get_question(row["question_id"])
        L = lang(sess["tg_id"])
        order = json.loads(row["option_order"])
        opts = q.opts(L)
        letters = LETTERS.get(L, LETTERS["ar"])
        total = db.session_len(sid)
        head = t(L, "q_head", n=pos + 1, t=total, lvl=row["level"]) + f"\n{progress_bar(pos, total)}"
        if ctx.timer():
            head += "  " + t(L, "timer", s=ctx.timer())
        if sess["mode"] == "sudden":
            head += "  ☠️"
        lines = [f"{letters[i]}) {esc(opts[o])}" for i, o in enumerate(order)]
        text = f"{head}\n\n<b>{esc(q.text(L))}</b>\n\n" + "\n".join(lines)
        answers = [btn(letters[i], f"a:{sid}:{pos}:{i}") for i in range(len(order))]
        return text, kb(answers, [btn(t(L, "btn_report_q"), f"rq:{sid}:{pos}"), btn(t(L, "btn_stop"), f"stop:{sid}")]), q.image

    def expired(row) -> bool:
        return bool(ctx.timer() and row["sent_at"] and time.time() - row["sent_at"] > ctx.timer() + GRACE_SECONDS)

    def cancel_timer(sid: int, pos: int) -> None:
        tk = timers.pop((sid, pos), None)
        if tk:
            tk.cancel()

    async def send_question(bot: Bot, chat_id: int, sid: int, pos: int) -> None:
        while True:
            text, markup, photo = question_text(sid, pos)
            if await render(bot, chat_id, sid, text, markup, photo):
                break
            # الصورة تعطّلت: نتخطى السؤال بلا احتساب، وبعد 3 مرات يُعطَّل تلقائيًا
            row = db.session_question(sid, pos)
            db.bump_img_fail(row["question_id"])
            db.skip_question(sid, pos)
            if pos + 1 >= db.session_len(sid):
                await finish(bot, chat_id, sid)
                return
            pos += 1
            db.advance(sid, pos)
        db.mark_sent(sid, pos)
        if ctx.timer():
            cancel_timer(sid, pos)
            timers[(sid, pos)] = asyncio.create_task(timeout_watch(bot, chat_id, sid, pos))

    async def timeout_watch(bot: Bot, chat_id: int, sid: int, pos: int) -> None:
        try:
            await asyncio.sleep(ctx.timer() + GRACE_SECONDS)
        except asyncio.CancelledError:
            return
        timers.pop((sid, pos), None)
        sess = db.get_session(sid)
        if not sess or sess["state"] != "active" or sess["current_pos"] != pos:
            return
        if db.record_answer(sid, pos, -1, timed_out=True) is None:
            return
        await show_timeout(bot, chat_id, sid, pos)

    async def show_timeout(bot: Bot, chat_id: int, sid: int, pos: int) -> None:
        sess = db.get_session(sid)
        L = lang(sess["tg_id"])
        row = db.session_question(sid, pos)
        q = db.get_question(row["question_id"])
        right = q.opts(L)[json.loads(row["option_order"])[row["correct_pos"]]]
        await render(bot, chat_id, sid, t(L, "timeout", ans=esc(right)),
                     kb([btn(t(L, "btn_next"), f"n:{sid}:{pos}")],
                        [btn(t(L, "btn_report_q"), f"rq:{sid}:{pos}"), btn(t(L, "btn_stop"), f"stop:{sid}")]))

    async def advance_after(bot: Bot, chat_id: int, sid: int, pos: int, correct: bool) -> None:
        sess = db.get_session(sid)
        if sess["mode"] == "sudden" and not correct:
            await finish(bot, chat_id, sid)
        elif pos + 1 < db.session_len(sid):
            db.advance(sid, pos + 1)
            await send_question(bot, chat_id, sid, pos + 1)
        else:
            await finish(bot, chat_id, sid)


    # ── التحدي اليومي وسؤال اليوم وسلسلة الأيام ───────────────
    def board_text(L: str, day: int) -> str:
        rows = db.daily_board(day, "daily", 10)
        medals = ["🥇", "🥈", "🥉"]
        lines = [f"{medals[i] if i < 3 else str(i + 1) + '.'} {esc(r['name'] or '?')} — <b>{r['correct']}/{r['total']}</b> · {r['secs']:.0f}s"
                 for i, r in enumerate(rows)]
        return t(L, "dy_board", rows="\n".join(lines)) if lines else t(L, "dy_board_empty")

    async def finish_daily(bot: Bot, chat_id: int, sid: int, tg_id: int, mode: str, answers, L: str) -> None:
        from .daily import STREAK_MILESTONES
        day = db.today()
        correct = sum(a.correct for a in answers)
        total = db.session_len(sid)
        secs = db.session_time_ms(sid) / 1000
        db.finish_session(sid, tg_id, float(correct), mode, counted=False)
        db.record_daily(day, mode, tg_id, correct, total, secs)
        streak, grew = db.mark_streak(tg_id, day)
        if mode == "dq":
            pct, n = db.daily_pct(day, mode)
            r = t(L, "dy_right" if correct else "dy_wrong")
            text = t(L, "dy_res_q", r=r, p=pct, n=n) if n >= 3 else t(L, "dy_res_q_solo", r=r)
        else:
            rank = db.daily_rank(day, mode, tg_id)
            text = t(L, "dy_res_d", c=correct, n=total, s=f"{secs:.0f}", rank=rank if rank else "—")
        text += "\n\n" + t(L, "dy_streak_now", n=streak)
        if grew and streak in STREAK_MILESTONES:
            text += "\n" + t(L, "dy_streak_ms", n=streak)
        await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb(
            [btn(t(L, "dy_btn_lb"), "dy:lb"), btn(t(L, "btn_daily"), "dy:m")], *chan_row(L), [btn(t(L, "btn_menu"), "menu")]))

    def dy_menu_view(uid: int, L: str):
        day = db.today()
        u = db.get_user(uid)
        text = t(L, "dy_menu", streak=db.current_streak(uid, day), best=u["best_streak"],
                 q=t(L, "dy_done" if db.played_today(uid, "dq") else "dy_todo"),
                 d=t(L, "dy_done" if db.played_today(uid, "daily") else "dy_todo"))
        return text, kb([btn(t(L, "dy_btn_q"), "dy:q"), btn(t(L, "dy_btn_d"), "dy:d")],
                        [btn(t(L, "dy_btn_lb"), "dy:lb")],
                        [btn(t(L, "dy_rm_on" if u["remind"] else "dy_rm_off"), "dy:rm")],
                        [btn(t(L, "btn_menu"), "menu")])

    @r.message(Command("daily"))
    async def cmd_daily(m: Message):
        db.upsert_user(m.from_user.id, m.from_user.full_name)
        L = lang(m.from_user.id)
        text, markup = dy_menu_view(m.from_user.id, L)
        await m.answer(text, parse_mode="HTML", reply_markup=markup)

    @r.callback_query(F.data == "dy:m")
    async def cb_daily_menu(c: CallbackQuery):
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        await c.answer()
        L = lang(c.from_user.id)
        text, markup = dy_menu_view(c.from_user.id, L)
        await c.message.answer(text, parse_mode="HTML", reply_markup=markup)

    @r.callback_query(F.data.in_({"dy:q", "dy:d"}))
    async def cb_daily_start(c: CallbackQuery):
        await c.answer()
        await begin(c.bot, c.message.chat.id, c.from_user.id, name_of(c), mode="dq" if c.data == "dy:q" else "daily")

    @r.callback_query(F.data == "dy:lb")
    async def cb_daily_board(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        await c.message.answer(board_text(L, db.today()), parse_mode="HTML",
                               reply_markup=kb(*chan_row(L), [btn(t(L, "btn_daily"), "dy:m")]))

    @r.callback_query(F.data.in_({"dy:rm", "dy:off"}))
    async def cb_daily_remind(c: CallbackQuery):
        uid = c.from_user.id
        db.upsert_user(uid, c.from_user.full_name)
        L = lang(uid)
        on = (not db.get_user(uid)["remind"]) if c.data == "dy:rm" else False
        db.set_remind(uid, on)
        await c.answer(t(L, "dy_rm_set_on" if on else "dy_rm_set_off"), show_alert=True)
        if c.data == "dy:rm":
            text, markup = dy_menu_view(uid, L)
            try:
                await c.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
            except TelegramAPIError:
                pass

    # ── مواجهة مع صديق (نفس الأسئلة، كلٌّ في وقته) ───────────────
    @r.callback_query(F.data == "du:new")
    async def cb_duel_new(c: CallbackQuery):
        await c.answer()
        did = db.create_duel(c.from_user.id)
        await begin(c.bot, c.message.chat.id, c.from_user.id, name_of(c), mode="duel", duel_id=did)

    @r.callback_query(F.data.regexp(r"^du:acc:\d+$"))
    async def cb_duel_accept(c: CallbackQuery):
        L = lang(c.from_user.id)
        did = int(c.data.split(":")[2])
        d = db.get_duel(did)
        cs = db.get_session(d["creator_sid"]) if d and d["creator_sid"] else None
        if not cs or cs["state"] != "finished" or not db.join_duel(did, c.from_user.id):
            await c.answer(t(L, "du_unavail"), show_alert=True)
            return
        await c.answer()
        await begin(c.bot, c.message.chat.id, c.from_user.id, name_of(c), mode="duel",
                    challenge_of=cs["id"], duel_id=did, force_new=True)

    async def finish_duel(bot: Bot, chat_id: int, sess, tg_id: int, answers, L: str) -> None:
        did = sess["duel_id"]
        correct = sum(a.correct for a in answers)
        n = db.session_len(sess["id"])
        db.finish_session(sess["id"], tg_id, float(correct), "duel", counted=False)
        d = db.get_duel(did)
        if not d:
            return
        if tg_id == d["creator"]:
            link = f"https://t.me/{await bot_username(bot)}?start=du_{did}"
            await bot.send_message(chat_id, t(L, "du_wait", c=correct, n=n), parse_mode="HTML", reply_markup=kb(
                [btn(t(L, "du_share_btn"), url=f"https://t.me/share/url?url={quote(link)}&text={quote(t(L, 'du_share_text'))}")],
                [btn(t(L, "btn_menu"), "menu")]))
            return
        a_sess = db.get_session(d["creator_sid"])
        sa, sb = int(a_sess["score"] or 0), correct
        db.duel_done(did)
        ua, ub = db.get_user(d["creator"]), db.get_user(tg_id)
        for uid, Lx in ((d["creator"], lang(d["creator"])), (tg_id, L)):
            winner = pub(ua) if sa > sb else pub(ub) if sb > sa else None
            verdict = t(Lx, "du_win", w=esc(winner)) if winner else t(Lx, "du_draw")
            try:
                await bot.send_message(uid, t(Lx, "du_result", a=esc(pub(ua)), sa=sa, b=esc(pub(ub)), sb=sb, n=n, v=verdict),
                                       parse_mode="HTML", reply_markup=kb([btn(t(Lx, "du_btn"), "du:new")],
                                                                          [btn(t(Lx, "btn_menu"), "menu")]))
            except TelegramAPIError:
                pass

    # ── الدعوات ─────────────────────────────────────────────
    async def credit_invite(bot: Bot, tg_id: int) -> None:
        inv = db.credit_invite(tg_id)
        if not inv:
            return
        n = db.invite_count(inv)
        Li = lang(inv)
        old, new = invite_badge(n - 1), invite_badge(n)
        text = t(Li, "iv_joined", n=n)
        if new and new != old:
            text += "\n" + t(Li, "iv_badge_up", b=badge_label(new, Li))
        try:
            await bot.send_message(inv, text)
        except TelegramAPIError:
            pass

    @r.callback_query(F.data == "iv")
    async def cb_invite(c: CallbackQuery):
        uid = c.from_user.id
        db.upsert_user(uid, c.from_user.full_name)
        L = lang(uid)
        await c.answer()
        n = db.invite_count(uid)
        b = invite_badge(n)
        nxt = next((x for x in INVITE_BADGES if x[0] > n), None)
        lines = [t(L, "iv_head"), "", t(L, "iv_count", n=n),
                 t(L, "iv_badge", b=badge_label(b, L)) if b else t(L, "iv_nobadge")]
        if nxt:
            lines.append(t(L, "iv_next", k=nxt[0] - n, b=badge_label(nxt, L)))
        link = f"https://t.me/{await bot_username(c.bot)}?start=inv_{uid}"
        share = t(L, "iv_share")
        await c.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=kb(
            [btn(t(L, "iv_btn"), url=f"https://t.me/share/url?url={quote(link)}&text={quote(share)}")],
            [btn(t(L, "btn_menu"), "menu")]))

    # ── النتيجة ─────────────────────────────────────────────
    async def finish(bot: Bot, chat_id: int, sid: int) -> None:
        sess = db.get_session(sid)
        tg_id, mode = sess["tg_id"], sess["mode"]
        user = db.get_user(tg_id)
        name, L = user["name"] or "?", user["lang"]
        answers = db.session_answers(sid)
        username = await bot_username(bot)

        async def drop_quiz_message():
            if sess["message_id"]:
                try:
                    await bot.delete_message(chat_id, sess["message_id"])
                except TelegramAPIError:
                    pass

        again = [btn(t(L, "btn_again"), "go" if mode == "full" else {"quick": "qk", "sudden": "sd"}.get(mode, "cats")),
                 btn(t(L, "btn_menu"), "menu")]

        if mode == "sudden":
            streak = sum(a.correct for a in answers)
            lvl = answers[-1].level if answers else 1
            db.finish_session(sid, tg_id, float(streak), "sudden", counted=False)
            best = db.set_best_sudden(tg_id, streak)
            text = t(L, "fin_head", name=esc(name)) + "\n\n" + t(L, "sudden_res", n=streak, lvl=lvl, best=best)
            text += "\n<i>" + t(L, "sd_line_low" if streak < 5 else "sd_line_mid" if streak < 20 else "sd_line_high") + "</i>"
            if streak == len(answers) == db.session_len(sid):
                text += "\n" + t(L, "sudden_perfect")
            await drop_quiz_message()
            try:
                png = await asyncio.to_thread(card.make_sudden_card, name, streak, lvl, best, L, "@" + username)
                await bot.send_photo(chat_id, BufferedInputFile(png, "sudden.jpg"), caption=text,
                                     parse_mode="HTML", reply_markup=kb(again))
            except Exception as e:  # noqa: BLE001
                log.warning("sudden card failed: %s", e)
                await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb(again))
            return

        if mode in ("daily", "dq"):
            await drop_quiz_message()
            await finish_daily(bot, chat_id, sid, tg_id, mode, answers, L)
            return
        if mode == "duel":
            await drop_quiz_message()
            await finish_duel(bot, chat_id, sess, tg_id, answers, L)
            return

        score = compute_score(answers)
        suspicious = mode == "full" and db.fast_answer_ratio(sid) > SUSPECT_FAST_RATIO
        db.finish_session(sid, tg_id, score, mode, counted=not suspicious)
        if mode == "full" and not suspicious and db.pending_inviter(tg_id):
            if await subscribed(bot, tg_id) is not False:        # لا يُحسب إلا بعد الاشتراك بالقناة
                await credit_invite(bot, tg_id)
        title = title_for(score, L)
        brk = category_breakdown(answers)
        pct = db.percentile(score) if mode == "full" else None
        correct = sum(a.correct for a in answers)

        tier = card.tier_of(score)[0]
        parts = [t(L, "fin_head", name=esc(name)), "", t(L, "res_score", score=f"{score:.1f}"),
                 t(L, "res_title", title=esc(title)), "<i>" + t(L, f"res_line_{tier}") + "</i>",
                 t(L, "res_correct", c=correct, t=len(answers))]
        if pct is not None:
            parts.append(t(L, "res_pct", p=f"{pct:.0f}"))
        parts += ["", t(L, "res_cat")]
        for cat, (ok, total) in sorted(brk.items(), key=lambda kv: -kv[1][0] / kv[1][1]):
            parts.append(f"• {cat_label(L, cat)}: {ok}/{total}")
        if suspicious:
            parts += ["", t(L, "res_suspect")]
        elif mode != "full":
            parts += ["", t(L, "res_nolb")]

        # مقارنة التحدي
        if sess["challenge_of"]:
            ch = db.get_session(sess["challenge_of"])
            if ch and ch["score"] is not None:
                them_user = db.get_user(ch["tg_id"])
                them, mine = ch["score"], score
                verdict = "vs_win" if mine > them else "vs_lose" if mine < them else "vs_draw"
                parts += ["", t(L, "vs_head", name=esc(pub(them_user))),
                          t(L, "vs_line", me=f"{mine:.1f}", name=esc(pub(them_user)), them=f"{them:.1f}"),
                          t(L, verdict)]
                Lc = them_user["lang"]
                dm_v = "vs_dm_win" if them > mine else "vs_dm_lose" if them < mine else "vs_dm_draw"
                try:
                    await bot.send_message(ch["tg_id"], t(Lc, "vs_dm", name=esc(name), me=f"{mine:.1f}",
                                                          them=f"{them:.1f}", verdict=t(Lc, dm_v)), parse_mode="HTML")
                except TelegramAPIError:
                    pass

        rows = [again]
        if mode == "full":
            link = f"https://t.me/{username}?start=ch_{sid}"
            share = t(L, "share_text", score=f"{score:.1f}", title=title)
            rows.append([btn(t(L, "btn_share"), url=f"https://t.me/share/url?url={quote(link)}&text={quote(share)}")])
        if db.session_shown(sid):
            rows.append([btn(t(L, "btn_report"), f"rp:{sid}:0")])
        rows += chan_row(L)
        markup = kb(*rows)
        caption = "\n".join(parts)
        await drop_quiz_message()
        try:
            mode_text = (t(L, "mode_quick") if mode == "quick"
                         else cat_label(L, sess["category"]) if mode == "category" and sess["category"] else None)
            png = await asyncio.to_thread(card.make_card, name, score, title, pct, brk, L, mode_text, "@" + username)
            await bot.send_photo(chat_id, BufferedInputFile(png, "result.jpg"), caption=caption,
                                 reply_markup=markup, parse_mode="HTML")
        except Exception as e:  # noqa: BLE001  (الخط غير متوفر أو أي خطأ في الصورة → نص فقط)
            log.warning("card failed: %s", e)
            await bot.send_message(chat_id, caption, reply_markup=markup, parse_mode="HTML")

    # ── بدء الاختبار ────────────────────────────────────────
    async def begin(bot: Bot, chat_id: int, tg_id: int, name: str, mode: str = "full",
                    category: str | None = None, force_new: bool = False, challenge_of: int | None = None, duel_id: int | None = None) -> None:
        from .daily import daily_questions, duel_questions
        db.upsert_user(tg_id, name)
        L = lang(tg_id)
        if not await gate(bot, chat_id, tg_id):
            return
        active = db.active_session(tg_id)
        if active and not force_new:
            await bot.send_message(
                chat_id, t(L, "resume_prompt", n=active["current_pos"] + 1, t=db.session_len(active["id"])),
                reply_markup=kb([btn(t(L, "btn_resume"), "resume"),
                                 btn(t(L, "btn_new"), f"nw:{mode}:{category or '-'}:{challenge_of or 0}"
                                     if mode not in ("daily", "dq", "duel") else "dy:m")]))
            return
        if mode in ("daily", "dq") and db.played_today(tg_id, mode):
            await bot.send_message(chat_id, t(L, "dy_played"), reply_markup=kb(
                [btn(t(L, "dy_btn_lb"), "dy:lb")], [btn(t(L, "btn_menu"), "menu")]))
            return
        if mode == "full" and not challenge_of and not force_new:
            last = db.last_finished_at(tg_id)
            if last and ctx.cooldown():
                wait = last + ctx.cooldown() * 60 - time.time()
                if wait > 0:
                    await bot.send_message(chat_id, t(L, "cooldown", m=int(wait // 60) + 1))
                    return
        db.abandon_active(tg_id)
        pool = [q for q in db.all_questions() if (q.q_en if L == "en" else True)]
        seen = db.seen_map(tg_id)
        if challenge_of:
            qs = db.session_questions_ordered(challenge_of)
        elif mode in ("daily", "dq"):
            qs = daily_questions([q for q in db.all_questions() if q.q_en], db.today(), mode)
        elif mode == "duel":
            qs = duel_questions([q for q in db.all_questions() if q.q_en], seen, rng)
        elif mode == "quick":
            qs = pick_questions(pool, seen, rng, per_level=1)
        elif mode == "category":
            qs = pick_category(pool, seen, category or "", rng)
        else:
            qs = pick_questions(pool, seen, rng)
        if len(qs) < MODE_SIZE.get(mode, 50) or not qs:
            await bot.send_message(chat_id, t(L, "bank_short"))
            return
        picked = []
        for q in qs:
            order, cpos = shuffle_options(q, rng)
            picked.append((q, order, cpos))
        sid = db.create_session(tg_id, picked, mode=mode, challenge_of=challenge_of, category=category,
                                duel_id=duel_id)
        if duel_id:
            d = db.get_duel(duel_id)
            db.duel_set_sid(duel_id, "creator" if d["creator"] == tg_id else "opponent", sid)
        await send_question(bot, chat_id, sid, 0)

    async def resume(bot: Bot, chat_id: int, tg_id: int, name: str) -> None:
        if not await gate(bot, chat_id, tg_id):
            return
        sess = db.active_session(tg_id)
        if not sess:
            await begin(bot, chat_id, tg_id, name)
            return
        sid, pos = sess["id"], sess["current_pos"]
        row = db.session_question(sid, pos)
        if row["user_answer"] is None and expired(row):
            db.record_answer(sid, pos, -1, timed_out=True)
            row = db.session_question(sid, pos)
        if row["user_answer"] is not None:
            if row["user_answer"] == -1:
                await show_timeout(bot, chat_id, sid, pos)
            else:
                await advance_after(bot, chat_id, sid, pos, row["is_correct"] != 0)
            return
        await send_question(bot, chat_id, sid, pos)

    async def send_welcome(m: Message, L: str, text: str, markup) -> None:
        """بانر مرسوم (assets/banner*.png) + نص الترحيب في رسالة واحدة. معرّف الصورة يُخزَّن فلا تُرفع كل مرة."""
        path = ROOT / "assets" / ("banner_en.jpg" if L == "en" else "banner.jpg")
        key = f"banner_fid_{L}"
        fid = db.get_setting(key, "") or None
        if fid or path.is_file():
            try:
                sent = await m.answer_photo(fid or FSInputFile(path), caption=text, reply_markup=markup, parse_mode="HTML")
                if not fid and getattr(sent, "photo", None):
                    db.set_setting(key, sent.photo[-1].file_id)
                return
            except TelegramAPIError as e:
                log.warning("banner failed: %s", e)
                db.set_setting(key, "")
        await m.answer(text, reply_markup=markup, parse_mode="HTML")

    # ── الأوامر ─────────────────────────────────────────────
    @r.message(Command("start"))
    async def cmd_start(m: Message, command: CommandObject):
        hint = "en" if (m.from_user.language_code or "").startswith("en") else "ar"
        arg = (command.args or "").strip()
        is_new = db.get_user(m.from_user.id) is None
        db.upsert_user(m.from_user.id, m.from_user.full_name, hint)
        if is_new and arg.startswith("inv_") and arg[4:].isdigit():
            db.set_inviter(m.from_user.id, int(arg[4:]))
        L = lang(m.from_user.id)
        extra, top = "", []
        if arg.startswith("ch_") and arg[3:].isdigit():
            s = db.get_session(int(arg[3:]))
            if s and s["state"] == "finished" and s["mode"] == "full" and s["tg_id"] != m.from_user.id:
                friend = db.get_user(s["tg_id"])
                extra = t(L, "challenge_banner", name=esc(pub(friend)), score=f"{s['score']:.1f}",
                          title=esc(title_for(s["score"], L)))
                top = [[btn(t(L, "btn_accept"), f"cc:{s['id']}")]]
        if arg.startswith("du_") and arg[3:].isdigit():
            d = db.get_duel(int(arg[3:]))
            cs = db.get_session(d["creator_sid"]) if d and d["creator_sid"] else None
            if d and d["creator"] != m.from_user.id and d["state"] == "open" and cs and cs["state"] == "finished" \
                    and d["opponent"] in (None, m.from_user.id):
                extra = t(L, "du_invite", name=esc(pub(db.get_user(d["creator"]))))
                top = [[btn(t(L, "du_accept"), f"du:acc:{d['id']}")]]
        if arg.startswith("pf_") and arg[3:].isdigit() and int(arg[3:]) != m.from_user.id:
            fr = db.get_user(int(arg[3:]))
            if fr and fr["best_score"] > 0 and not db.is_admin(fr["tg_id"]):      # ملف الأدمن لا يُعرض لأحد
                extra = t(L, "pf_visit", name=esc(fr["name"] or "?"), score=f"{fr['best_score']:.1f}",
                          title=esc(title_for(fr["best_score"], L)))
                top = [[btn(t(L, "btn_try_too"), "go")]]
        await send_welcome(m, L, welcome_for(L, m.from_user) + extra, menu(L, top))

    @r.message(Command("help"))
    async def cmd_help(m: Message):
        await m.answer(t(lang(m.from_user.id), "help"))

    @r.message(Command("retry"))
    async def cmd_retry(m: Message):
        await begin(m.bot, m.chat.id, m.from_user.id, m.from_user.full_name)

    @r.message(Command("myid"))
    async def cmd_myid(m: Message):
        from . import INSTANCE, STARTED, VERSION
        adm = "✅ نعم" if ctx.is_admin(m.from_user.id) else "❌ لا"
        up = int((time.time() - STARTED) // 60)
        await m.answer(f"ID: <code>{m.from_user.id}</code>\nمشرف: {adm}\nنسخة البوت: <code>{VERSION}</code>\n"
                       f"الهوية: <code>{INSTANCE}</code>\nشغّال منذ: {up} دقيقة", parse_mode="HTML")

    @r.message(Command("ping"))
    async def cmd_ping(m: Message):
        """يفرّق بين بطء الوصول من تليجرام وبطء البوت نفسه."""
        age = max(0.0, time.time() - m.date.timestamp())
        t0 = time.perf_counter()
        sent = await m.answer("🏓 …")
        rt = (time.perf_counter() - t0) * 1000
        await sent.edit_text(
            f"🏓 pong\n⏱ تأخر وصول رسالتك للبوت: {age:.0f} ث (±1)\n📤 زمن إرسال الرد إلى تليجرام: {rt:.0f} ms\n\n"
            "• التأخر كبير (أكثر من 3 ث)؟ المشكلة في الوصول: نسخة ثانية/Conflict أو شبكة الاستضافة.\n"
            "• التأخر صغير والرد بطيء؟ المشكلة في الاستضافة نفسها.")

    @r.message(Command("chatid"))
    async def cmd_chatid(m: Message):
        """يعرض رقم المحادثة (اكتبه داخل قناة/مجموعة النسخ ليعطيك BACKUP_CHAT_ID)."""
        await m.answer(f"chat id: <code>{m.chat.id}</code>", parse_mode="HTML")

    @r.channel_post(Command("chatid"))
    async def ch_chatid(m: Message):
        await m.answer(f"chat id: <code>{m.chat.id}</code>", parse_mode="HTML")

    @r.message(Command("lang"))
    async def cmd_lang(m: Message):
        await m.answer("🌐", reply_markup=kb([btn("العربية", "lg:ar"), btn("English", "lg:en")]))

    @r.message(Command("top"))
    async def cmd_top(m: Message):
        text, markup = lb_view(m.from_user.id, "all")
        await m.answer(text, parse_mode="HTML", reply_markup=markup)

    @r.message(Command("weekly"))
    async def cmd_weekly(m: Message):
        text, markup = lb_view(m.from_user.id, "week")
        await m.answer(text, parse_mode="HTML", reply_markup=markup)

    def stats_text(uid: int) -> str:
        L = lang(uid)
        u = db.get_user(uid)
        if not u or not u["tests_taken"]:
            return t(L, "no_tests")
        recent = ", ".join(f"{s['score']:.1f}" for s in db.last_session_stats(uid))
        return t(L, "stats", best=f"{u['best_score']:.1f}", title=esc(title_for(u["best_score"], L)),
                 rank=db.user_rank(uid) or "-", n=u["tests_taken"], sd=u["best_sudden"], recent=recent)

    @r.message(Command("stats"))
    async def cmd_stats(m: Message):
        await m.answer(stats_text(m.from_user.id), parse_mode="HTML")

    @r.callback_query(F.data == "st")
    async def cb_stats(c: CallbackQuery):
        await c.answer()
        await c.message.answer(stats_text(c.from_user.id), parse_mode="HTML")

    @r.callback_query(F.data == "noop")
    async def cb_noop(c: CallbackQuery):
        await c.answer()

    async def send_profile(bot: Bot, chat_id: int, uid: int, fallback_name: str) -> None:
        L = lang(uid)
        p = db.user_profile(uid)
        if not p or not p["tests"]:
            await bot.send_message(chat_id, t(L, "no_tests"))
            return
        title = title_for(p["best"], L)
        lines = [t(L, "prof_head", name=esc(p["name"] or fallback_name)),
                 t(L, "prof_best", best=f"{p['best']:.1f}", title=esc(title))]
        if p["rank"]:
            lines.append(t(L, "prof_rank", rank=p["rank"]))
        if p["weekly_rank"]:
            lines.append(t(L, "prof_week", rank=p["weekly_rank"]))
        lines.append(t(L, "prof_tests", n=p["tests"]))
        if p["answers"]:
            lines.append(t(L, "prof_acc", pct=round(100 * p["correct"] / p["answers"]), ok=p["correct"], n=p["answers"]))
        if p["sudden"]:
            lines.append(t(L, "prof_sudden", n=p["sudden"]))
        ib = invite_badge(db.invite_count(uid))
        if ib:
            lines.append(t(L, "iv_badge", b=badge_label(ib, L)))
        if p["cats"]:
            lines.append(t(L, "prof_cat"))
            lines += [f"• {cat_label(L, cat)}: {acc * 100:.0f}%" for cat, acc, _ in p["cats"]]
        link = f"https://t.me/{await bot_username(bot)}?start=pf_{uid}"
        share = t(L, "prof_share", score=f"{p['best']:.1f}", title=title)
        markup = kb([btn(t(L, "btn_share_profile"), url=f"https://t.me/share/url?url={quote(link)}&text={quote(share)}")],
                    *chan_row(L), [btn(t(L, "btn_menu"), "menu")])
        caption = "\n".join(lines)
        try:
            png = await asyncio.to_thread(card.make_profile_card, p, title, L, "@" + await bot_username(bot))
            await bot.send_photo(chat_id, BufferedInputFile(png, "profile.jpg"), caption=caption,
                                 reply_markup=markup, parse_mode="HTML")
        except Exception as e:  # noqa: BLE001  (لا خط/أي خطأ → نص فقط)
            log.warning("profile card failed: %s", e)
            await bot.send_message(chat_id, caption, reply_markup=markup, parse_mode="HTML")

    @r.message(Command("profile"))
    async def cmd_profile(m: Message):
        db.upsert_user(m.from_user.id, m.from_user.full_name)
        await send_profile(m.bot, m.chat.id, m.from_user.id, m.from_user.full_name)

    @r.callback_query(F.data == "pf")
    async def cb_profile(c: CallbackQuery):
        await c.answer()
        await send_profile(c.bot, c.message.chat.id, c.from_user.id, c.from_user.full_name)

    @r.message(Command("diag"))
    async def cmd_diag(m: Message):
        """تشخيص الاشتراك الإجباري: يوضح لماذا لا يظهر طلب الاشتراك."""
        ch = ctx.channel()
        if not ch:
            await m.answer("الاشتراك الإجباري معطّل (REQUIRED_CHANNEL فارغ).")
            return
        lines = [f"القناة المطلوبة: {ch}"]
        me = await m.bot.get_me()
        try:
            b = await m.bot.get_chat_member(ch, me.id)
            lines.append(f"حالة البوت في القناة: {b.status}"
                         + ("" if b.status == "administrator" else "  ← لازم يكون administrator ❗"))
        except TelegramAPIError as e:
            lines.append(f"❌ البوت لا يرى القناة: {e}")
        try:
            u = await m.bot.get_chat_member(ch, m.from_user.id)
            lines.append(f"حالتك أنت في القناة: {u.status}")
            if u.status in ("creator", "administrator") or ctx.is_admin(m.from_user.id):
                lines.append("ℹ️ أنت مالك/مشرف، لذلك لن يطلب منك الاشتراك. جرّب بحساب آخر.")
        except TelegramAPIError as e:
            lines.append(f"❌ تعذّر فحص حسابك: {e}")
        await m.answer("\n".join(lines))

    # ── اقتراح أسئلة من اللاعبين ────────────────────────────
    async def ask_suggestion(target: Message, state: FSMContext, uid: int):
        L = lang(uid)
        await state.set_state(Suggest.wait)
        await target.answer(t(L, "sg_prompt"), parse_mode="HTML")

    @r.message(Command("suggest"))
    async def cmd_suggest(m: Message, state: FSMContext):
        db.upsert_user(m.from_user.id, m.from_user.full_name)
        await ask_suggestion(m, state, m.from_user.id)

    @r.callback_query(F.data == "sg")
    async def cb_suggest(c: CallbackQuery, state: FSMContext):
        await c.answer()
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        await ask_suggestion(c.message, state, c.from_user.id)

    @r.message(Command("cancel"))
    async def cmd_cancel(m: Message, state: FSMContext):
        await stop_everything(m.bot, m.chat.id, m.from_user.id, state)

    @r.message(Suggest.wait, F.text, ~F.text.startswith("/"))
    async def on_suggestion(m: Message, state: FSMContext):
        uid, L = m.from_user.id, lang(m.from_user.id)
        lines = [x.strip() for x in m.text.splitlines() if x.strip()]
        if len(lines) != 5:
            await m.answer(t(L, "sg_format"))
            return
        q, options = lines[0], lines[1:]
        if not 10 <= len(q) <= 200 or any(len(o) > 60 for o in options):
            await m.answer(t(L, "sg_len"))
            return
        if len({o.lower() for o in options}) != 4:
            await m.answer(t(L, "sg_dupopt"))
            return
        await state.clear()
        if db.suggestions_today(uid) >= SUGGEST_PER_DAY:
            await m.answer(t(L, "sg_limit", n=SUGGEST_PER_DAY))
        elif db.pending_suggestions_of(uid) >= SUGGEST_MAX_PENDING:
            await m.answer(t(L, "sg_pending", n=db.pending_suggestions_of(uid)))
        elif db.text_exists(q):
            await m.answer(t(L, "sg_exists"))
        else:
            db.add_suggestion(uid, q, options)       # options[0] هو الجواب الصحيح
            await m.answer(t(L, "sg_ok"))

    @r.message(Command("claim"))
    async def cmd_claim(m: Message, command: CommandObject):
        code = (command.args or "").strip()
        if ctx.claim_code and code == ctx.claim_code and db.admin_count() == 0:
            db.add_admin(m.from_user.id, owner=True)
            ctx.claim_code = None
            await m.answer("✅ صرت مالك البوت. افتح لوحة التحكم بـ /admin")
        else:
            await m.answer("❌")

    # ── المتصدرون ───────────────────────────────────────────
    GAME_ICONS = {"tf": "✅❌", "song": "🎵", "ord": "📅", "char": "🕵️", "quote": "💬"}

    def lb_menu_view(uid: int):
        """شاشة اختيار واضحة: كل قسم بزر مستقل وشرح سطر واحد."""
        L = lang(uid)
        return t(L, "lbm_text"), kb(
            [btn(t(L, "lbm_quiz"), "lb:all")], [btn(t(L, "lbm_sd"), "lb:sd")],
            [btn(t(L, "lbm_games"), "lb:gm")], [btn(t(L, "lbm_daily"), "lb:dy")],
            *chan_row(L), [btn(t(L, "btn_menu"), "menu")])

    def lb_view(uid: int, kind: str):
        """قسم واحد في كل مرة: عنوان + شرح + الأفضل 10 + ترتيبك + تبويبات داخلية فقط عند الحاجة."""
        L = lang(uid)
        extra, sub_tabs = "", []
        if kind == "week":
            since = week_start()
            rows = db.weekly_leaderboard(since)
            head = t(L, "lb_week")
            lines = [f"{i + 1}. {esc(x['name'] or '?')} — <b>{x['score']:.1f}</b>" for i, x in enumerate(rows)]
            rank = db.weekly_rank(uid, since)
            extra = t(L, "lb_you", rank=rank) if rank else ""
        elif kind == "sd":
            rows = db.sudden_leaderboard()
            head = t(L, "lb_sudden")
            lines = [f"{i + 1}. {esc(x['name'] or '?')} — <b>{x['best_sudden']}</b>" for i, x in enumerate(rows)]
            rank = db.sudden_rank(uid)
            extra = t(L, "lb_you", rank=rank) if rank else t(L, "lb_you_none")
        elif kind == "dy":
            rows = db.daily_board(db.today(), "daily", 10)
            head = t(L, "lt_daily_head")
            lines = [f"{i + 1}. {esc(x['name'] or '?')} — <b>{x['correct']}/{x['total']}</b> · {x['secs']:.0f}s"
                     for i, x in enumerate(rows)]
            rank = db.daily_rank(db.today(), "daily", uid)
            extra = t(L, "lb_you", rank=rank) if rank else t(L, "lb_you_none")
        elif kind == "gm" or kind.startswith("g:"):
            gk = "tf" if kind == "gm" else kind.split(":")[1]
            rows = db.game_board(gk, 10)
            head = t(L, "lt_game_head", g=t(L, f"g_{gk}"))
            lines = [f"{i + 1}. {esc(x['name'] or '?')} — <b>{x['best']}</b>" for i, x in enumerate(rows)]
            rank = db.game_rank(uid, gk)
            extra = t(L, "lb_you", rank=rank) if rank else t(L, "lb_you_none")
            names = {"tf": "lg_tf", "song": "lg_song", "ord": "lg_ord", "char": "lg_char", "quote": "lg_quote"}
            sub_tabs = [[btn(("✅ " if k == gk else "") + t(L, names[k]), f"lb:g:{k}")] for k in GAME_ICONS]
            sub_tabs = [[row[0] for row in sub_tabs[:3]], [row[0] for row in sub_tabs[3:]]]
        else:
            kind = "all"
            rows = db.leaderboard(10)
            head = t(L, "lb_all")
            lines = [f"{i + 1}. {esc(x['name'] or '?')} — <b>{x['best_score']:.1f}</b> ({esc(title_for(x['best_score'], L))})"
                     for i, x in enumerate(rows)]
            rank = db.user_rank(uid)
            extra = t(L, "lb_you", rank=rank) if rank else t(L, "lb_you_none")
        if kind in ("all", "week"):
            sub_tabs = [[btn(("✅ " if kind == "all" else "") + t(L, "tab_all"), "lb:all"),
                         btn(("✅ " if kind == "week" else "") + t(L, "tab_week"), "lb:week")]]
        medals = ["🥇", "🥈", "🥉"]
        lines = [(medals[i] + l[l.index("."):][1:]) if i < 3 else l for i, l in enumerate(lines)]
        body = "\n".join(lines) if lines else t(L, "lb_empty")
        markup = kb(*sub_tabs, [btn(t(L, "lb_back"), "lb:menu"), btn(t(L, "btn_menu"), "menu")], *chan_row(L))
        return f"{head}\n\n{body}{extra}", markup

    @r.callback_query(F.data.regexp(r"^lb:(menu|all|week|sd|dy|gm|g:(tf|song|ord|char|quote))$"))
    async def cb_lb(c: CallbackQuery):
        await c.answer()
        view = c.data[3:]
        text, markup = lb_menu_view(c.from_user.id) if view == "menu" else lb_view(c.from_user.id, view)
        try:
            await c.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        except TelegramBadRequest:
            await c.message.answer(text, parse_mode="HTML", reply_markup=markup)

    # ── القوائم والأوضاع ────────────────────────────────────
    @r.callback_query(F.data == "m:games")
    async def cb_games_menu(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        await c.message.answer(t(L, "g_menu"), parse_mode="HTML",
                               reply_markup=games_kb(L, db.category_counts(L).get("images", 0) >= 10))

    @r.callback_query(F.data == "m:more")
    async def cb_more_menu(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        await c.message.answer(t(L, "more_menu"), reply_markup=more_kb(L))

    @r.callback_query(F.data == "menu")
    async def cb_menu(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        await c.message.answer(welcome_for(L, c.from_user), reply_markup=menu(L), parse_mode="HTML")

    def name_of(c: CallbackQuery) -> str:
        return c.from_user.full_name

    @r.callback_query(F.data == "go")
    async def cb_go(c: CallbackQuery):
        await c.answer()
        await begin(c.bot, c.message.chat.id, c.from_user.id, name_of(c))

    @r.callback_query(F.data == "qk")
    async def cb_quick(c: CallbackQuery):
        await c.answer()
        await begin(c.bot, c.message.chat.id, c.from_user.id, name_of(c), mode="quick")

    @r.callback_query(F.data == "sd")
    async def cb_sudden(c: CallbackQuery):
        await c.answer()
        await begin(c.bot, c.message.chat.id, c.from_user.id, name_of(c), mode="sudden")

    @r.callback_query(F.data == "cats")
    async def cb_cats(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        counts = db.category_counts(L)
        rows = [[btn(f"{cat_label(L, cat)} ({n})", f"ct:{cat}")] for cat, n in sorted(counts.items()) if n >= 10]
        if not rows:
            await c.message.answer(t(L, "no_cats"))
            return
        await c.message.answer(t(L, "cat_menu"), reply_markup=kb(*rows, [btn(t(L, "btn_back"), "menu")]))

    @r.callback_query(F.data.startswith("ct:"))
    async def cb_cat(c: CallbackQuery):
        await c.answer()
        await begin(c.bot, c.message.chat.id, c.from_user.id, name_of(c), mode="category",
                    category=c.data.split(":", 1)[1])

    @r.callback_query(F.data.startswith("cc:"))
    async def cb_accept(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        s = db.get_session(int(c.data.split(":")[1]))
        if not s or s["state"] != "finished" or s["mode"] != "full":
            await c.message.answer(t(L, "ch_gone"))
            return
        if s["tg_id"] == c.from_user.id:
            await c.message.answer(t(L, "ch_self"))
            return
        prev = db.challenge_session(c.from_user.id, s["id"])
        if prev and prev["state"] == "finished":
            await c.message.answer(t(L, "ch_done", score=f"{prev['score']:.1f}"), parse_mode="HTML")
            return
        await begin(c.bot, c.message.chat.id, c.from_user.id, name_of(c), challenge_of=s["id"])

    @r.callback_query(F.data.startswith("lg:"))
    async def cb_lang(c: CallbackQuery):
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        new = c.data.split(":")[1]
        if new == "toggle":
            new = "ar" if lang(c.from_user.id) == "en" else "en"
        db.set_lang(c.from_user.id, new)
        await c.answer(t(new, "lang_set"))
        await c.message.answer(welcome_for(new, c.from_user), reply_markup=menu(new), parse_mode="HTML")

    @r.callback_query(F.data == "chk")
    async def cb_check(c: CallbackQuery):
        L = lang(c.from_user.id)
        ok = await subscribed(c.bot, c.from_user.id)
        if not ok:
            await c.answer(t(L, "sub_no") if ok is False else t(L, "sub_err"), show_alert=True)
            return
        note_join(c.from_user.id)
        await c.answer(t(L, "sub_ok"))
        await c.message.answer(welcome_for(L, c.from_user), reply_markup=menu(L), parse_mode="HTML")

    @r.callback_query(F.data.startswith("nw:"))
    async def cb_new(c: CallbackQuery):
        await c.answer()
        _, mode, cat, ch = c.data.split(":")
        await begin(c.bot, c.message.chat.id, c.from_user.id, name_of(c), mode=mode,
                    category=None if cat == "-" else cat, force_new=True,
                    challenge_of=int(ch) or None)

    @r.callback_query(F.data == "resume")
    async def cb_resume(c: CallbackQuery):
        await c.answer()
        await resume(c.bot, c.message.chat.id, c.from_user.id, name_of(c))

    # ── الإجابات ────────────────────────────────────────────
    def own_active(c: CallbackQuery, sid: int):
        sess = db.get_session(sid)
        if not sess or sess["tg_id"] != c.from_user.id or sess["state"] != "active":
            return None
        return sess

    @r.callback_query(F.data.startswith("a:"))
    async def cb_answer(c: CallbackQuery):
        _, sid, pos, choice = c.data.split(":")
        sid, pos, choice = int(sid), int(pos), int(choice)
        L = lang(c.from_user.id)
        sess = own_active(c, sid)
        if not sess or sess["current_pos"] != pos:
            await c.answer(t(L, "toast_stale"))
            return
        row = db.session_question(sid, pos)
        if row["user_answer"] is not None:
            await c.answer()
            return
        was_expired = expired(row)
        cancel_timer(sid, pos)
        correct = db.record_answer(sid, pos, choice, timed_out=was_expired)
        if correct is None:
            await c.answer()
            return
        if was_expired:
            await c.answer(t(L, "toast_time"))
        elif correct:
            await c.answer(t(L, "toast_ok"))
        else:
            q = db.get_question(row["question_id"])
            right = q.opts(L)[json.loads(row["option_order"])[row["correct_pos"]]]
            await c.answer(t(L, "toast_bad", ans=right)[:190])
        await advance_after(c.bot, c.message.chat.id, sid, pos, bool(correct))

    @r.callback_query(F.data.startswith("n:"))
    async def cb_next(c: CallbackQuery):
        _, sid, pos = c.data.split(":")
        sid, pos = int(sid), int(pos)
        sess = own_active(c, sid)
        await c.answer()
        if not sess or sess["current_pos"] != pos:
            return
        row = db.session_question(sid, pos)
        if row["user_answer"] is None:
            return
        await advance_after(c.bot, c.message.chat.id, sid, pos, bool(row["is_correct"]))

    @r.callback_query(F.data.startswith("stop:"))
    async def cb_stop(c: CallbackQuery):
        """زر «إنهاء»: يطلب تأكيدًا أولًا حتى لا يُلغى الاختبار بضغطة خاطئة."""
        sid = int(c.data.split(":")[1])
        sess = own_active(c, sid)
        await c.answer()
        if not sess:
            return
        L = lang(c.from_user.id)
        await render(c.bot, c.message.chat.id, sid, t(L, "stop_confirm"),
                     kb([btn(t(L, "stop_yes"), f"sty:{sid}")], [btn(t(L, "stop_no"), f"stn:{sid}")]))

    @r.callback_query(F.data.startswith("sty:"))
    async def cb_stop_yes(c: CallbackQuery):
        sid = int(c.data.split(":")[1])
        sess = own_active(c, sid)
        await c.answer()
        if not sess:
            return
        L = lang(c.from_user.id)
        cancel_timer(sid, sess["current_pos"])
        db.abandon_active(c.from_user.id)
        await render(c.bot, c.message.chat.id, sid, t(L, "stopped"), menu(L))

    @r.callback_query(F.data.startswith("stn:"))
    async def cb_stop_no(c: CallbackQuery):
        await c.answer()
        if own_active(c, int(c.data.split(":")[1])):
            await resume(c.bot, c.message.chat.id, c.from_user.id, name_of(c))

    async def stop_everything(bot: Bot, chat_id: int, uid: int, state: FSMContext) -> None:
        """/stop و/cancel: يلغي أي اختبار أو لعبة أو إدخال معلّق، مهما كان نوعه."""
        L = lang(uid)
        done: list[str] = []
        if await state.get_state():
            await state.clear()
            done.append(t(L, "w_input"))
        sess = db.active_session(uid)
        if sess:
            cancel_timer(sess["id"], sess["current_pos"])
            if sess["message_id"]:
                await render(bot, chat_id, sess["id"], t(L, "stopped"), None)   # تتعطّل أزرار السؤال القديم
            db.abandon_active(uid)
            done.append(t(L, "w_quiz"))
        if db.abort_active_games(uid):
            done.append(t(L, "w_game"))
        if done:
            await bot.send_message(chat_id, t(L, "cancel_done", what="، ".join(done)), reply_markup=menu(L), parse_mode="HTML")
        else:
            await bot.send_message(chat_id, t(L, "cancel_nothing"))

    @r.message(Command("stop"))
    async def cmd_stop(m: Message, state: FSMContext):
        await stop_everything(m.bot, m.chat.id, m.from_user.id, state)

    # ── الإبلاغ عن الأخطاء: متاح لكل سؤال، بحماية من الإساءة ──
    # • زر «🚩 أبلغ» على كل سؤال أثناء الاختبار، وبعد النتيجة قائمة بكل أسئلة جولتك (✅/❌).
    # • لازم يكون السؤال ظهر لك فعلًا في جلستك أنت (لا يمكن الإبلاغ عن سؤال لم تره).
    # • بلاغ واحد لكل مستخدم لكل سؤال، وحد يومي لكل مستخدم (الإعدادات).
    # • لا يصل الأدمن إلا عند تجمّع عدة بلاغات مستقلة على نفس السؤال (العتبة من الإعدادات).
    def own_shown(c: CallbackQuery, sid: int, pos: int):
        """صف السؤال إن كانت الجلسة له وكان السؤال قد ظهر له (في أي حالة للجلسة)."""
        s = db.get_session(sid)
        if not s or s["tg_id"] != c.from_user.id:
            return None
        row = db.session_question(sid, pos)
        return row if row and row["sent_at"] is not None else None

    PAGE = 8

    @r.callback_query(F.data.regexp(r"^rp:\d+(:\d+)?$"))
    async def cb_report_list(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        parts = c.data.split(":")
        sid, page = int(parts[1]), int(parts[2]) if len(parts) > 2 else 0
        s = db.get_session(sid)
        if not s or s["tg_id"] != c.from_user.id:
            await c.message.answer(t(L, "rp_closed"))
            return
        shown = db.session_shown(sid)
        if not shown:
            await c.message.answer(t(L, "rp_none"))
            return
        pages = (len(shown) + PAGE - 1) // PAGE
        page = max(0, min(page, pages - 1))
        rows = []
        for w in shown[page * PAGE:(page + 1) * PAGE]:
            q = db.get_question(w["question_id"])
            icon = "✅" if w["is_correct"] == 1 else "❌" if w["is_correct"] == 0 else "⏭"
            rows.append([btn(f"{icon} {w['pos'] + 1}. {q.text(L)[:40]}", f"rq:{sid}:{w['pos']}")])
        nav = []
        if page > 0:
            nav.append(btn("◀️", f"rp:{sid}:{page - 1}"))
        nav.append(btn(f"{page + 1}/{pages}", "noop"))
        if page < pages - 1:
            nav.append(btn("▶️", f"rp:{sid}:{page + 1}"))
        await c.message.answer(t(L, "rp_pick"), reply_markup=kb(*rows, nav if pages > 1 else []))

    @r.callback_query(F.data.regexp(r"^rq:\d+:\d+$"))
    async def cb_report_reason(c: CallbackQuery):
        L = lang(c.from_user.id)
        _, sid, pos = c.data.split(":")
        row = own_shown(c, int(sid), int(pos))
        if not row:
            await c.answer(t(L, "rp_closed"))
            return
        await c.answer()
        q = db.get_question(row["question_id"])
        idx = [0, 1, 2, 3] + ([4] if q.image else [])
        # رسالة جديدة: لا نلمس رسالة السؤال، فيستمر الاختبار والمؤقت كما هما
        await c.message.answer(t(L, "rp_reason"),
                               reply_markup=kb(*[[btn(t(L, f"rr_{i}"), f"rr:{sid}:{pos}:{i}")] for i in idx]))

    @r.callback_query(F.data.regexp(r"^rr:\d+:\d+:\d$"))
    async def cb_report_send(c: CallbackQuery):
        L = lang(c.from_user.id)
        _, sid, pos, ri = c.data.split(":")
        sid, pos, ri = int(sid), int(pos), int(ri)
        row = own_shown(c, sid, pos)
        if not row or not 0 <= ri <= 4:
            await c.answer(t(L, "rp_closed"))
            return
        res = db.add_report(row["question_id"], c.from_user.id, t("ar", f"rr_{ri}"), ctx.reports_per_day())
        if res == "dup":
            await c.answer(t(L, "rp_dup"), show_alert=True)
        elif res == "limit":
            await c.answer(t(L, "rp_limit", n=ctx.reports_per_day()), show_alert=True)
        else:
            await c.answer(t(L, "rp_ok"))
            qid = row["question_id"]
            if db.open_report_count(qid) == ctx.report_threshold():
                q = db.get_question(qid)
                for admin in ctx.admin_ids():
                    try:
                        await c.bot.send_message(
                            admin, f"🚩 سؤال وصل {ctx.report_threshold()} بلاغات مستقلة:\n#{qid} {esc(q.q)}",
                            reply_markup=kb([btn("🔎 مراجعة", f"ad:rv:{qid}")]))
                    except TelegramAPIError:
                        pass
        try:
            await c.message.delete()                 # ننظّف رسالة الأسباب (واختبارك لم يتأثر)
        except TelegramAPIError:
            pass

    # شبكة أمان: أي زر لم يلتقطه معالج (زر قديم من رسالة سابقة) يُجاب فورًا بدل أن يبقى «يحمّل» بلا رد.
    # يجب أن يبقى آخر معالج في آخر راوتر.
    @r.callback_query()
    async def cb_unknown(c: CallbackQuery):
        await c.answer(t(lang(c.from_user.id), "btn_stale"), show_alert=False)

    return r
