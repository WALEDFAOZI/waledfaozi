from __future__ import annotations

import asyncio
import html
import logging
import random
import time
from urllib.parse import quote

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from . import card
from .config import CATEGORY_LABELS, LEVELS, PER_LEVEL, Settings
from .db import DB
from .quiz import category_breakdown, compute_score, pick_questions, progress_bar, shuffle_options, title_for

log = logging.getLogger(__name__)
LETTERS = ["أ", "ب", "ج", "د", "هـ", "و"]
GRACE_SECONDS = 2          # سماح لتأخر الشبكة
SUSPECT_FAST_RATIO = 0.7   # نسبة إجابات أسرع من ثانية تعتبر مشبوهة


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def kb(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


def btn(text: str, data: str | None = None, url: str | None = None) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data, url=url)


def build_router(settings: Settings, db: DB) -> Router:
    r = Router()
    timers: dict[tuple[int, int], asyncio.Task] = {}
    rng = random.Random()
    TOTAL = LEVELS * PER_LEVEL

    # ── أدوات مساعدة ─────────────────────────────────────────
    def expired(row) -> bool:
        return bool(settings.timer_seconds and row["sent_at"]
                    and time.time() - row["sent_at"] > settings.timer_seconds + GRACE_SECONDS)

    def cancel_timer(sid: int, pos: int) -> None:
        t = timers.pop((sid, pos), None)
        if t:
            t.cancel()

    async def safe_edit(bot: Bot, chat_id: int, message_id: int | None, text: str,
                        markup: InlineKeyboardMarkup | None) -> int:
        """يعدّل الرسالة إن أمكن وإلا يرسل جديدة. يرجع message_id المستخدم."""
        if message_id:
            try:
                await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id,
                                            reply_markup=markup, parse_mode="HTML")
                return message_id
            except TelegramBadRequest as e:
                if "not modified" in str(e).lower():
                    return message_id
        m = await bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")
        return m.message_id

    def question_text(sid: int, pos: int) -> tuple[str, InlineKeyboardMarkup]:
        row = db.session_question(sid, pos)
        q = db.get_question(row["question_id"])
        import json
        order = json.loads(row["option_order"])
        lines = [f"{LETTERS[i]}) {esc(q.options[o])}" for i, o in enumerate(order)]
        head = (f"🎌 <b>السؤال {pos + 1}/{TOTAL}</b>  ·  المستوى {row['level']}/{LEVELS}\n"
                f"{progress_bar(pos, TOTAL)}")
        if settings.timer_seconds:
            head += f"  ⏱ {settings.timer_seconds}ث"
        text = f"{head}\n\n<b>{esc(q.q)}</b>\n\n" + "\n".join(lines)
        answers = [btn(LETTERS[i], f"a:{sid}:{pos}:{i}") for i in range(len(order))]
        return text, kb(answers, [btn("⛔ إنهاء الاختبار", f"stop:{sid}")])

    async def send_question(bot: Bot, chat_id: int, sid: int, pos: int) -> None:
        sess = db.get_session(sid)
        text, markup = question_text(sid, pos)
        msg_id = await safe_edit(bot, chat_id, sess["message_id"], text, markup)
        db.mark_sent(sid, pos, msg_id)
        if settings.timer_seconds:
            cancel_timer(sid, pos)
            timers[(sid, pos)] = asyncio.create_task(timeout_watch(bot, chat_id, sid, pos))

    async def timeout_watch(bot: Bot, chat_id: int, sid: int, pos: int) -> None:
        try:
            await asyncio.sleep(settings.timer_seconds + GRACE_SECONDS)
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
        import json
        row = db.session_question(sid, pos)
        q = db.get_question(row["question_id"])
        order = json.loads(row["option_order"])
        right = q.options[order[row["correct_pos"]]]
        text = (f"⏰ <b>انتهى الوقت!</b>\nالجواب الصحيح: <b>{esc(right)}</b>")
        sess = db.get_session(sid)
        await safe_edit(bot, chat_id, sess["message_id"], text,
                        kb([btn("التالي ▶️", f"n:{sid}:{pos}")], [btn("⛔ إنهاء", f"stop:{sid}")]))

    async def next_or_finish(bot: Bot, chat_id: int, sid: int, pos: int, tg_id: int, name: str) -> None:
        if pos + 1 < db.session_len(sid):
            db.advance(sid, pos + 1)
            await send_question(bot, chat_id, sid, pos + 1)
        else:
            await finish(bot, chat_id, sid, tg_id, name)

    async def finish(bot: Bot, chat_id: int, sid: int, tg_id: int, name: str) -> None:
        answers = db.session_answers(sid)
        score = compute_score(answers)
        suspicious = db.fast_answer_ratio(sid) > SUSPECT_FAST_RATIO
        db.finish_session(sid, tg_id, score, count_best=not suspicious)
        pct = db.percentile(score)
        title = title_for(score)
        brk = category_breakdown(answers)
        correct = sum(a.correct for a in answers)

        parts = [f"🏁 <b>انتهى التقييم يا {esc(name)}!</b>", "",
                 f"⭐ التقييم: <b>{score:.1f} / 10</b>",
                 f"🏷 اللقب: <b>{esc(title)}</b>",
                 f"✅ الإجابات الصحيحة: {correct}/{len(answers)}",
                 f"📊 أفضل من {pct:.0f}% من اللاعبين", "", "<b>حسب التصنيف:</b>"]
        for cat, (ok, total) in sorted(brk.items(), key=lambda kv: -kv[1][0] / kv[1][1]):
            parts.append(f"• {CATEGORY_LABELS.get(cat, cat)}: {ok}/{total}")
        if suspicious:
            parts += ["", "⚠️ إجاباتك كانت سريعة جدًا؛ لن تُحتسب النتيجة في المتصدرين."]
        caption = "\n".join(parts)

        me = await bot.get_me()
        share_text = f"حصلت على {score:.1f}/10 وصرت «{title}» في بوت تقييم الأوتاكو! تقدر تغلبني؟"
        link = f"https://t.me/{me.username}?start=ch_{tg_id}"
        markup = kb(
            [btn("🔁 اختبار جديد", "go"), btn("🏆 المتصدرون", "top")],
            [btn("📤 تحدَّ صديقك", url=f"https://t.me/share/url?url={quote(link)}&text={quote(share_text)}")],
        )
        sess = db.get_session(sid)
        if sess["message_id"]:
            try:
                await bot.delete_message(chat_id, sess["message_id"])
            except TelegramBadRequest:
                pass
        try:
            png = card.make_card(name, score, title, pct, brk)
            await bot.send_photo(chat_id, BufferedInputFile(png, "result.png"),
                                 caption=caption, reply_markup=markup, parse_mode="HTML")
        except Exception as e:  # الخط غير متوفر أو أي خطأ في الصورة → نص فقط
            log.warning("card failed: %s", e)
            await bot.send_message(chat_id, caption, reply_markup=markup, parse_mode="HTML")

    async def begin_test(bot: Bot, chat_id: int, tg_id: int, name: str, force_new: bool = False) -> None:
        db.upsert_user(tg_id, name)
        active = db.active_session(tg_id)
        if active and not force_new:
            await bot.send_message(
                chat_id,
                f"عندك اختبار غير مكتمل (وصلت للسؤال {active['current_pos'] + 1}/{TOTAL}).",
                reply_markup=kb([btn("▶️ كمّل", "resume"), btn("🆕 ابدأ من جديد", "new")]))
            return
        if not force_new:
            last = db.last_finished_at(tg_id)
            if last and settings.cooldown_minutes:
                wait = last + settings.cooldown_minutes * 60 - time.time()
                if wait > 0:
                    await bot.send_message(
                        chat_id, f"⏳ لازم تنتظر {int(wait // 60) + 1} دقيقة قبل اختبار جديد.\n"
                                 "راجع نتيجتك بـ /stats أو شف المتصدرين بـ /top")
                    return
        db.abandon_active(tg_id)
        picked = []
        for q in pick_questions(db.all_questions(), db.seen_map(tg_id), rng):
            order, cpos = shuffle_options(q, rng)
            picked.append((q, order, cpos))
        if len(picked) < TOTAL:
            await bot.send_message(chat_id, "عذرًا، بنك الأسئلة لا يكفي حاليًا. جرّب لاحقًا.")
            return
        sid = db.create_session(tg_id, picked)
        await send_question(bot, chat_id, sid, 0)

    async def resume(bot: Bot, chat_id: int, tg_id: int, name: str) -> None:
        sess = db.active_session(tg_id)
        if not sess:
            await begin_test(bot, chat_id, tg_id, name)
            return
        sid, pos = sess["id"], sess["current_pos"]
        row = db.session_question(sid, pos)
        if row["user_answer"] is None and expired(row):
            db.record_answer(sid, pos, -1, timed_out=True)
            row = db.session_question(sid, pos)
        if row["user_answer"] is not None:   # أُجيب/انتهى وقته لكن لم ننتقل بعد
            if row["user_answer"] == -1:
                await show_timeout(bot, chat_id, sid, pos)
            else:
                await next_or_finish(bot, chat_id, sid, pos, tg_id, name)
            return
        await send_question(bot, chat_id, sid, pos)

    # ── الأوامر ─────────────────────────────────────────────
    START_KB = kb([btn("🎮 ابدأ التقييم", "go")], [btn("🏆 المتصدرون", "top")])

    @r.message(Command("start"))
    async def cmd_start(m: Message, command: CommandObject):
        db.upsert_user(m.from_user.id, m.from_user.full_name)
        extra = ""
        arg = (command.args or "").strip()
        if arg.startswith("ch_") and arg[3:].isdigit():
            friend = db.get_user(int(arg[3:]))
            if friend and friend["tests_taken"] and friend["tg_id"] != m.from_user.id:
                extra = (f"\n\n⚔️ <b>{esc(friend['name'])}</b> تحداك! "
                         f"أفضل نتيجة له: <b>{friend['best_score']:.1f}/10</b> — تقدر تغلبه؟")
        await m.answer(
            "أهلًا بك في <b>بوت تقييم الأوتاكو</b> 🎌\n\n"
            f"{TOTAL} سؤالًا بأربعة اختيارات، من الأسهل للأصعب، وفي النهاية تحصل على تقييم من 10 "
            "ولقب! الأسئلة الصعبة تُحسب بوزن أكبر.\n"
            "الأسئلة تتغير في كل مرة، فلا تتكرر عليك إلا إذا خلصت البنك." + extra,
            reply_markup=START_KB, parse_mode="HTML")

    @r.message(Command("help"))
    async def cmd_help(m: Message):
        await m.answer("/start — البداية\n/retry — اختبار جديد\n/stats — إحصائياتك\n/top — المتصدرون")

    @r.message(Command("retry"))
    async def cmd_retry(m: Message):
        await begin_test(m.bot, m.chat.id, m.from_user.id, m.from_user.full_name)

    @r.message(Command("top"))
    async def cmd_top(m: Message):
        await m.answer(top_text(), parse_mode="HTML")

    def top_text() -> str:
        rows = db.leaderboard(10)
        if not rows:
            return "ما فيه متصدرين بعد، كن الأول! 🏆"
        medals = ["🥇", "🥈", "🥉"]
        lines = ["🏆 <b>أفضل 10 أوتاكو</b>", ""]
        for i, u in enumerate(rows):
            lines.append(f"{medals[i] if i < 3 else f'{i + 1}.'} {esc(u['name'] or '؟')} — "
                         f"<b>{u['best_score']:.1f}</b>  ({title_for(u['best_score'])})")
        return "\n".join(lines)

    @r.message(Command("stats"))
    async def cmd_stats(m: Message):
        u = db.get_user(m.from_user.id)
        if not u or not u["tests_taken"]:
            await m.answer("ما أخذت أي اختبار بعد. اضغط /start 🎌")
            return
        recent = ", ".join(f"{s['score']:.1f}" for s in db.last_session_stats(m.from_user.id))
        await m.answer(
            f"📈 <b>إحصائياتك</b>\nأفضل تقييم: <b>{u['best_score']:.1f}/10</b> "
            f"({esc(title_for(u['best_score']))})\n"
            f"الترتيب: #{db.user_rank(m.from_user.id)}\nعدد الاختبارات: {u['tests_taken']}\n"
            f"آخر النتائج: {recent}", parse_mode="HTML")

    @r.message(Command("flagged"))
    async def cmd_flagged(m: Message):
        if m.from_user.id not in settings.admin_ids:
            return
        rows = db.suspicious_questions()
        if not rows:
            await m.answer("لا توجد أسئلة مشبوهة حاليًا ✅")
            return
        await m.answer("⚠️ أسئلة نسبة نجاحها ≤ 27% (قد تحتاج مراجعة):\n\n" + "\n".join(
            f"#{x['id']} ({x['pct']}% من {x['asked']}) {x['q']}" for x in rows[:20]))

    # ── الأزرار ─────────────────────────────────────────────
    @r.callback_query(F.data == "go")
    async def cb_go(c: CallbackQuery):
        await c.answer()
        await begin_test(c.bot, c.message.chat.id, c.from_user.id, c.from_user.full_name)

    @r.callback_query(F.data == "new")
    async def cb_new(c: CallbackQuery):
        await c.answer()
        await begin_test(c.bot, c.message.chat.id, c.from_user.id, c.from_user.full_name, force_new=True)

    @r.callback_query(F.data == "resume")
    async def cb_resume(c: CallbackQuery):
        await c.answer()
        await resume(c.bot, c.message.chat.id, c.from_user.id, c.from_user.full_name)

    @r.callback_query(F.data == "top")
    async def cb_top(c: CallbackQuery):
        await c.answer()
        await c.message.answer(top_text(), parse_mode="HTML")

    def own_active(c: CallbackQuery, sid: int):
        sess = db.get_session(sid)
        if not sess or sess["tg_id"] != c.from_user.id or sess["state"] != "active":
            return None
        return sess

    @r.callback_query(F.data.startswith("a:"))
    async def cb_answer(c: CallbackQuery):
        _, sid, pos, choice = c.data.split(":")
        sid, pos, choice = int(sid), int(pos), int(choice)
        sess = own_active(c, sid)
        if not sess or sess["current_pos"] != pos:
            await c.answer("هذا السؤال لم يعد نشطًا", show_alert=False)
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
            await c.answer("⏰ انتهى الوقت")
        elif correct:
            await c.answer("✅ صح!")
        else:
            import json
            q = db.get_question(row["question_id"])
            right = q.options[json.loads(row["option_order"])[row["correct_pos"]]]
            await c.answer(f"❌ غلط — الجواب: {right}"[:190])
        await next_or_finish(c.bot, c.message.chat.id, sid, pos, c.from_user.id, c.from_user.full_name)

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
        await next_or_finish(c.bot, c.message.chat.id, sid, pos, c.from_user.id, c.from_user.full_name)

    @r.callback_query(F.data.startswith("stop:"))
    async def cb_stop(c: CallbackQuery):
        sid = int(c.data.split(":")[1])
        sess = own_active(c, sid)
        await c.answer()
        if not sess:
            return
        cancel_timer(sid, sess["current_pos"])
        db.abandon_active(c.from_user.id)
        await safe_edit(c.bot, c.message.chat.id, sess["message_id"],
                        "تم إيقاف الاختبار. ارجع متى ما حبيت! 🎌", START_KB)

    return r


async def run(settings: Settings) -> None:
    db = DB(settings.db_path)
    n = db.load_questions(settings.questions_path)
    log.info("loaded %d questions", n)
    bot = Bot(settings.token)
    dp = Dispatcher()
    dp.include_router(build_router(settings, db))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
