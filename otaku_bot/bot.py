from __future__ import annotations

import asyncio
import html
import json
import logging
import time
from urllib.parse import quote

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, InputMediaPhoto, Message)

from . import card
from .config import LEVELS
from .ctx import Ctx
from .quiz import (category_breakdown, compute_score, pick_category, pick_questions, progress_bar,
                   shuffle_options, title_for)
from .texts import cat_label, t
from .timeutil import week_start

log = logging.getLogger(__name__)
LETTERS = {"ar": ["أ", "ب", "ج", "د"], "en": ["A", "B", "C", "D"]}
GRACE_SECONDS = 2          # سماح لتأخر الشبكة
SUSPECT_FAST_RATIO = 0.7   # نسبة إجابات أسرع من ثانية تعتبر مشبوهة
MODE_SIZE = {"full": LEVELS * 5, "quick": 10, "category": 10, "sudden": LEVELS * 5}


def esc(s: str) -> str:
    return html.escape(str(s), quote=False)


def kb(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[r for r in rows if r])


def btn(text: str, data: str | None = None, url: str | None = None) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data, url=url)


def menu_kb(L: str, top: list[list[InlineKeyboardButton]] | None = None,
            images: bool = False) -> InlineKeyboardMarkup:
    """القائمة الرئيسية: كل ما يهم اللاعب ظاهر مباشرة (الاختبارات، الألعاب، المتصدرون، إحصائياتي، اللغة)."""
    quiz2 = [btn(t(L, "btn_sudden"), "sd")]
    if images:
        quiz2.append(btn(t(L, "btn_images"), "ct:images"))
    return kb(*(top or []),
              [btn(t(L, "sec_quiz"), "noop")],
              [btn(t(L, "btn_full"), "go")],
              [btn(t(L, "btn_quick"), "qk"), btn(t(L, "btn_cat"), "cats")],
              quiz2,
              [btn(t(L, "sec_games"), "noop")],
              [btn(t(L, "g_tf"), "g:tf")],
              [btn(t(L, "g_song"), "g:song")],
              [btn(t(L, "g_ord"), "g:ord")],
              [btn(t(L, "sec_more"), "noop")],
              [btn(t(L, "btn_top"), "lb:all"), btn(t(L, "btn_week"), "lb:week")],
              [btn(t(L, "btn_stats"), "st"), btn(t(L, "btn_lang"), "lg:toggle")])


def build_router(ctx: Ctx) -> Router:
    r = Router()
    db, rng, settings = ctx.db, ctx.rng, ctx.settings
    timers: dict[tuple[int, int], asyncio.Task] = {}
    sub_ok: dict[int, float] = {}      # من ثبت اشتراكه: لا نسأل تليجرام عنه ثانية قبل 5 دقائق (أسرع)
    me_cache: dict[str, str] = {}

    async def bot_username(bot: Bot) -> str:
        if "u" not in me_cache:
            me_cache["u"] = (await bot.get_me()).username
        return me_cache["u"]

    def lang(uid: int) -> str:
        return db.get_lang(uid)

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
        if time.time() - sub_ok.get(tg_id, 0) < 300:
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

    async def gate(bot: Bot, chat_id: int, tg_id: int) -> bool:
        ok = await subscribed(bot, tg_id)
        if ok:
            return True
        L = lang(tg_id)
        if ok is None:
            await bot.send_message(chat_id, t(L, "sub_unverifiable"))
        else:
            ch = ctx.channel()
            await bot.send_message(
                chat_id, t(L, "sub_required", ch=esc(ch)), parse_mode="HTML",
                reply_markup=kb([btn(t(L, "btn_subscribe"), url=f"https://t.me/{ch.lstrip('@')}")],
                                [btn(t(L, "btn_checked"), "chk")]))
        return False

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
        return text, kb(answers, [btn(t(L, "btn_stop"), f"stop:{sid}")]), q.image

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
                     kb([btn(t(L, "btn_next"), f"n:{sid}:{pos}")], [btn(t(L, "btn_stop"), f"stop:{sid}")]))

    async def advance_after(bot: Bot, chat_id: int, sid: int, pos: int, correct: bool) -> None:
        sess = db.get_session(sid)
        if sess["mode"] == "sudden" and not correct:
            await finish(bot, chat_id, sid)
        elif pos + 1 < db.session_len(sid):
            db.advance(sid, pos + 1)
            await send_question(bot, chat_id, sid, pos + 1)
        else:
            await finish(bot, chat_id, sid)

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
            if streak == len(answers) == db.session_len(sid):
                text += "\n" + t(L, "sudden_perfect")
            await drop_quiz_message()
            await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb(again))
            return

        score = compute_score(answers)
        suspicious = mode == "full" and db.fast_answer_ratio(sid) > SUSPECT_FAST_RATIO
        db.finish_session(sid, tg_id, score, mode, counted=not suspicious)
        title = title_for(score, L)
        brk = category_breakdown(answers)
        pct = db.percentile(score) if mode == "full" else None
        correct = sum(a.correct for a in answers)

        parts = [t(L, "fin_head", name=esc(name)), "", t(L, "res_score", score=f"{score:.1f}"),
                 t(L, "res_title", title=esc(title)), t(L, "res_correct", c=correct, t=len(answers))]
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
                parts += ["", t(L, "vs_head", name=esc(them_user["name"])),
                          t(L, "vs_line", me=f"{mine:.1f}", name=esc(them_user["name"]), them=f"{them:.1f}"),
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
        if db.session_wrong(sid):
            rows.append([btn(t(L, "btn_report"), f"rp:{sid}")])
        markup = kb(*rows)
        caption = "\n".join(parts)
        await drop_quiz_message()
        try:
            png = card.make_card(name, score, title, pct, brk, L)
            await bot.send_photo(chat_id, BufferedInputFile(png, "result.png"), caption=caption,
                                 reply_markup=markup, parse_mode="HTML")
        except Exception as e:  # noqa: BLE001  (الخط غير متوفر أو أي خطأ في الصورة → نص فقط)
            log.warning("card failed: %s", e)
            await bot.send_message(chat_id, caption, reply_markup=markup, parse_mode="HTML")

    # ── بدء الاختبار ────────────────────────────────────────
    async def begin(bot: Bot, chat_id: int, tg_id: int, name: str, mode: str = "full",
                    category: str | None = None, force_new: bool = False, challenge_of: int | None = None) -> None:
        db.upsert_user(tg_id, name)
        L = lang(tg_id)
        if not await gate(bot, chat_id, tg_id):
            return
        active = db.active_session(tg_id)
        if active and not force_new:
            await bot.send_message(
                chat_id, t(L, "resume_prompt", n=active["current_pos"] + 1, t=db.session_len(active["id"])),
                reply_markup=kb([btn(t(L, "btn_resume"), "resume"),
                                 btn(t(L, "btn_new"), f"nw:{mode}:{category or '-'}:{challenge_of or 0}")]))
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
        sid = db.create_session(tg_id, picked, mode=mode, challenge_of=challenge_of, category=category)
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

    # ── الأوامر ─────────────────────────────────────────────
    @r.message(Command("start"))
    async def cmd_start(m: Message, command: CommandObject):
        hint = "en" if (m.from_user.language_code or "").startswith("en") else "ar"
        db.upsert_user(m.from_user.id, m.from_user.full_name, hint)
        L = lang(m.from_user.id)
        extra, top = "", []
        arg = (command.args or "").strip()
        if arg.startswith("ch_") and arg[3:].isdigit():
            s = db.get_session(int(arg[3:]))
            if s and s["state"] == "finished" and s["mode"] == "full" and s["tg_id"] != m.from_user.id:
                friend = db.get_user(s["tg_id"])
                extra = t(L, "challenge_banner", name=esc(friend["name"]), score=f"{s['score']:.1f}",
                          title=esc(title_for(s["score"], L)))
                top = [[btn(t(L, "btn_accept"), f"cc:{s['id']}")]]
        await m.answer(t(L, "welcome") + extra, reply_markup=menu(L, top), parse_mode="HTML")

    @r.message(Command("help"))
    async def cmd_help(m: Message):
        await m.answer(t(lang(m.from_user.id), "help"))

    @r.message(Command("retry"))
    async def cmd_retry(m: Message):
        await begin(m.bot, m.chat.id, m.from_user.id, m.from_user.full_name)

    @r.message(Command("myid"))
    async def cmd_myid(m: Message):
        await m.answer(f"ID: <code>{m.from_user.id}</code>", parse_mode="HTML")

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
    def lb_view(uid: int, kind: str):
        L = lang(uid)
        extra = ""
        if kind == "week":
            since = week_start()
            rows = db.weekly_leaderboard(since)
            head = t(L, "lb_week")
            lines = [f"{i + 1}. {esc(x['name'] or '?')} — <b>{x['score']:.1f}</b>" for i, x in enumerate(rows)]
            rank = db.weekly_rank(uid, since)
            if rank:
                extra = t(L, "lb_you", rank=rank)
        elif kind == "sd":
            rows = db.sudden_leaderboard()
            head = t(L, "lb_sudden")
            lines = [f"{i + 1}. {esc(x['name'] or '?')} — <b>{x['best_sudden']}</b>" for i, x in enumerate(rows)]
        else:
            rows = db.leaderboard(10)
            head = t(L, "lb_all")
            lines = [f"{i + 1}. {esc(x['name'] or '?')} — <b>{x['best_score']:.1f}</b> ({esc(title_for(x['best_score'], L))})"
                     for i, x in enumerate(rows)]
            rank = db.user_rank(uid)
            if rank:
                extra = t(L, "lb_you", rank=rank)
        medals = ["🥇", "🥈", "🥉"]
        lines = [(medals[i] + l[l.index("."):][1:]) if i < 3 else l for i, l in enumerate(lines)]
        body = "\n".join(lines) if lines else t(L, "lb_empty")
        markup = kb([btn(t(L, "tab_all"), "lb:all"), btn(t(L, "tab_week"), "lb:week"), btn(t(L, "tab_sd"), "lb:sd")],
                    [btn(t(L, "btn_menu"), "menu")])
        return f"{head}\n\n{body}{extra}", markup

    @r.callback_query(F.data.startswith("lb:"))
    async def cb_lb(c: CallbackQuery):
        await c.answer()
        text, markup = lb_view(c.from_user.id, c.data.split(":")[1])
        try:
            await c.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        except TelegramBadRequest:
            await c.message.answer(text, parse_mode="HTML", reply_markup=markup)

    # ── القوائم والأوضاع ────────────────────────────────────
    @r.callback_query(F.data == "menu")
    async def cb_menu(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        await c.message.answer(t(L, "welcome"), reply_markup=menu(L), parse_mode="HTML")

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
        await c.message.answer(t(new, "welcome"), reply_markup=menu(new), parse_mode="HTML")

    @r.callback_query(F.data == "chk")
    async def cb_check(c: CallbackQuery):
        L = lang(c.from_user.id)
        ok = await subscribed(c.bot, c.from_user.id)
        if not ok:
            await c.answer(t(L, "sub_no") if ok is False else t(L, "sub_err"), show_alert=True)
            return
        await c.answer(t(L, "sub_ok"))
        await c.message.answer(t(L, "welcome"), reply_markup=menu(L), parse_mode="HTML")

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
        sid = int(c.data.split(":")[1])
        sess = own_active(c, sid)
        await c.answer()
        if not sess:
            return
        L = lang(c.from_user.id)
        cancel_timer(sid, sess["current_pos"])
        db.abandon_active(c.from_user.id)
        await render(c.bot, c.message.chat.id, sid, t(L, "stopped"), menu(L))

    # ── الإبلاغ عن الأسئلة (مقيَّد حتى لا يُساء استخدامه) ──
    # • يظهر زر الإبلاغ فقط بعد انتهاء الاختبار، وللأسئلة التي أخطأ فيها اللاعب نفسه.
    # • بلاغ واحد لكل مستخدم لكل سؤال، وحد يومي لكل مستخدم.
    # • لا يصل الأدمن إلا عند تجمّع عدة بلاغات مستقلة على نفس السؤال (العتبة من الإعدادات).
    def finished_own(c: CallbackQuery, sid: int):
        s = db.get_session(sid)
        return s if s and s["tg_id"] == c.from_user.id and s["state"] == "finished" else None

    @r.callback_query(F.data.startswith("rp:"))
    async def cb_report_list(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        sid = int(c.data.split(":")[1])
        if not finished_own(c, sid):
            await c.message.answer(t(L, "rp_closed"))
            return
        wrong = db.session_wrong(sid)[:8]
        if not wrong:
            await c.message.answer(t(L, "rp_none"))
            return
        rows = []
        for w in wrong:
            q = db.get_question(w["question_id"])
            rows.append([btn(f"{w['pos'] + 1}. {q.text(L)[:45]}", f"rq:{sid}:{w['pos']}")])
        await c.message.answer(t(L, "rp_pick"), reply_markup=kb(*rows))

    @r.callback_query(F.data.startswith("rq:"))
    async def cb_report_reason(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        _, sid, pos = c.data.split(":")
        sid, pos = int(sid), int(pos)
        if not finished_own(c, sid):
            return
        q = db.get_question(db.session_question(sid, pos)["question_id"])
        idx = [0, 1, 2, 3] + ([4] if q.image else [])
        await c.message.answer(t(L, "rp_reason"),
                               reply_markup=kb(*[[btn(t(L, f"rr_{i}"), f"rr:{sid}:{pos}:{i}")] for i in idx]))

    @r.callback_query(F.data.startswith("rr:"))
    async def cb_report_send(c: CallbackQuery):
        L = lang(c.from_user.id)
        _, sid, pos, ri = c.data.split(":")
        sid, pos, ri = int(sid), int(pos), int(ri)
        if not finished_own(c, sid) or not 0 <= ri <= 4:
            await c.answer(t(L, "rp_closed"))
            return
        row = db.session_question(sid, pos)
        if not row or row["is_correct"] != 0:
            await c.answer(t(L, "rp_closed"))
            return
        res = db.add_report(row["question_id"], c.from_user.id, t("ar", f"rr_{ri}"), ctx.reports_per_day())
        if res == "dup":
            await c.answer(t(L, "rp_dup"), show_alert=True)
        elif res == "limit":
            await c.answer(t(L, "rp_limit", n=ctx.reports_per_day()), show_alert=True)
        else:
            await c.answer(t(L, "rp_ok"), show_alert=True)
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

    return r
