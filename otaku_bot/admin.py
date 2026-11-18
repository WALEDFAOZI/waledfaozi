"""لوحة تحكم المالك داخل تليجرام: كل شيء من /admin بدون الرجوع للكود.

كيف يعرف البوت أنك المالك؟
  1) عند أول تشغيل بلا مشرفين يطبع البوت في السجل (Console) «كود تفعيل» لمرة واحدة؛ أرسله له: /claim الكود
  2) أو ضع رقمك في ADMIN_IDS في ملف .env (تعرف رقمك من /myid).
المالك وحده يضيف/يحذف المشرفين.
"""
from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import time
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from aiogram import BaseMiddleware
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from . import anilist
from .backup import chat_status_text, enabled as backup_enabled, last_backup_text, make_zip, send_chat_backup
from .growth import growth_text, refresh_count
from .bot import btn, esc, kb
from .config import CATEGORY_LABELS
from .ctx import Ctx
from .content import ANIME_HELP, TF_HELP, parse_anime, parse_tf
from .games import item_key, load_games
from .recommend import hkey, load_anime
from .texts import t

log = logging.getLogger(__name__)
BROADCAST_GAP = 300          # أقل مدة بين رسالتين جماعيتين (ثواني) لتفادي الإرسال بالخطأ


class Flow(StatesGroup):
    wait = State()          # ننتظر رسالة نصية/صورة من المشرف؛ نوع المطلوب في data["act"]


class IsAdmin(BaseFilter):
    def __init__(self, ctx: Ctx):
        self.ctx = ctx

    async def __call__(self, event) -> bool:
        u = getattr(event, "from_user", None)
        return bool(u and self.ctx.is_admin(u.id))


async def nav(c: CallbackQuery, text: str, markup, parse_mode: str | None = "HTML") -> None:
    """يحدّث رسالة اللوحة مكانها (أسرع وبلا ازدحام)؛ وإن تعذّر (مثلًا الرسالة صورة) يرسل جديدة."""
    try:
        await c.message.edit_text(text, parse_mode=parse_mode, reply_markup=markup)
    except TelegramAPIError as e:
        if "not modified" in str(e).lower():
            return
        await c.message.answer(text, parse_mode=parse_mode, reply_markup=markup)


class ClearPending(BaseMiddleware):
    """أي زر في اللوحة (عدا خطوات المعالج نفسه) يُلغي الإدخال المعلّق، حتى لا يُفسَّر كلامك العادي بالغلط."""
    KEEP = ("ad:aa:", "ad:ad:", "ad:ac:", "ad:ae:", "ad:bs:", "ad:bg:")

    async def __call__(self, handler, event, data):
        d = getattr(event, "data", None) or ""
        state = data.get("state")
        if state is not None and d.startswith("ad:") and not d.startswith(self.KEEP):
            await state.clear()
        return await handler(event, data)


def home_kb(pending: int = 0):
    return kb(
        [btn("📊 الإحصائيات", "ad:stats"), btn("🚩 البلاغات", "ad:rep")],
        [btn("➕ سؤال جديد", "ad:add"), btn("🔎 بحث/تعديل سؤال", "ad:find")],
        [btn(f"💡 الاقتراحات ({pending})", "ad:sg"), btn("📣 رسالة جماعية", "ad:bc")],
        [btn("⚙️ الإعدادات", "ad:set"), btn("👥 المشرفون", "ad:adm")],
        [btn("📚 المحتوى (صح/غلط، أنمي)", "ad:ct")],
        [btn("🖼 جلب أسئلة صور", "ad:img"), btn("💾 نسخة احتياطية", "ad:bak")],
    )


BACK = [btn("🏠 لوحة التحكم", "ad:home")]


def fmt_q(q, src: str, reports: int = 0) -> str:
    opts = "\n".join(f"{'✅' if i == q.answer else '▫️'} {i + 1}) {esc(o)}" for i, o in enumerate(q.options))
    en = f"\n🇬🇧 {esc(q.q_en)}\n" + " | ".join(esc(o) for o in q.options_en) if q.q_en and q.options_en else ""
    pct = f"{100 * q.correct / q.asked:.0f}% من {q.asked}" if q.asked else "لا إجابات بعد"
    return (f"<b>#{q.id}</b> {'🟢 مفعّل' if q.active else '🔴 معطّل'} · {src}\n"
            f"📂 {CATEGORY_LABELS.get(q.category, q.category)} · صعوبة أساسية {q.base_difficulty:g} "
            f"(فعلية {q.difficulty:.1f})\n📈 نسبة النجاح: {pct}"
            + (f"\n🖼 بصورة" if q.image else "") + (f"\n🚩 بلاغات مفتوحة: {reports}" if reports else "")
            + f"\n\n<b>{esc(q.q)}</b>\n{opts}{en}")


def q_actions(qid: int, active: bool, deletable: bool):
    rows = [
        [btn("✏️ النص", f"ad:e:{qid}:q"), btn("📝 الخيارات", f"ad:e:{qid}:o")],
        [btn("✅ الجواب", f"ad:e:{qid}:a"), btn("🎚 الصعوبة", f"ad:e:{qid}:d")],
        [btn("📂 التصنيف", f"ad:e:{qid}:c"), btn("🖼 الصورة", f"ad:e:{qid}:i")],
        [btn("🇬🇧 الإنجليزي", f"ad:e:{qid}:en"),
         btn("🚫 تعطيل" if active else "✅ تفعيل", f"ad:t:{qid}")],
    ]
    if deletable:
        rows.append([btn("🗑 حذف نهائي", f"ad:x:{qid}")])
    rows.append(BACK)
    return kb(*rows)


def parse_en(text: str):
    """سطر السؤال ثم 4 خيارات (5 أسطر)."""
    lines = [x.strip() for x in text.strip().splitlines() if x.strip()]
    return (lines[0], lines[1:5]) if len(lines) == 5 else None


def build_admin_router(ctx: Ctx) -> Router:
    r = Router()
    db = ctx.db
    r.message.filter(F.chat.type == "private")                    # لوحة الأدمن في الخاص فقط
    r.callback_query.filter(F.message.chat.type == "private")
    r.message.filter(IsAdmin(ctx))
    r.callback_query.filter(IsAdmin(ctx))
    r.callback_query.outer_middleware(ClearPending())

    async def show_q(target: Message, qid: int, edit: bool = False):
        q = db.get_question(qid)
        if not q:
            await target.answer("السؤال غير موجود.")
            return
        src = db.question_source(qid)
        text = fmt_q(q, src, db.open_report_count(qid))
        markup = q_actions(qid, q.active, src != "file")
        if edit:
            try:
                await target.edit_text(text, parse_mode="HTML", reply_markup=markup)
                return
            except TelegramAPIError:
                pass
        if q.image:
            photo = q.image[3:] if q.image.startswith("tg:") else q.image
            try:
                await target.answer_photo(photo, caption=text[:1000], parse_mode="HTML", reply_markup=markup)
                return
            except TelegramAPIError:
                text += "\n⚠️ تعذّر عرض الصورة" + ("" if q.image.startswith("tg:") else f"\n🔗 {esc(q.image)}")
        await target.answer(text, parse_mode="HTML", reply_markup=markup)

    @r.message(Command("admin"))
    async def cmd_admin(m: Message, state: FSMContext):
        await state.clear()
        await m.answer("🛠 <b>لوحة التحكم</b>", parse_mode="HTML", reply_markup=home_kb(db.pending_count()))

    @r.callback_query(F.data == "ad:home")
    async def cb_home(c: CallbackQuery, state: FSMContext):
        await state.clear()
        await c.answer()
        await nav(c, "🛠 <b>لوحة التحكم</b>", home_kb(db.pending_count()))

    @r.message(Command("flagged"))
    async def cmd_flagged(m: Message):
        rows = db.suspicious_questions()
        await m.answer("لا توجد أسئلة مشبوهة ✅" if not rows else "⚠️ نسبة نجاحها ≤ 27%:\n\n" + "\n".join(
            f"#{x['id']} ({x['pct']}% من {x['asked']}) {x['q']}" for x in rows[:20]))

    # ── الإحصائيات ──────────────────────────────────────────
    @r.callback_query(F.data == "ad:stats")
    async def cb_stats(c: CallbackQuery):
        await c.answer()
        await refresh_count(c.bot, ctx, max_age=3600)          # قياس عدد مشتركي القناة (مرة كل ساعة كحد أقصى)
        s = db.admin_stats()
        done = f"{100 * s['finished_7d'] / s['started_7d']:.0f}%" if s["started_7d"] else "—"
        avg = f"{s['avg_score']:.1f}" if s["avg_score"] is not None else "—"
        modes = "، ".join(f"{k}: {v}" for k, v in s["modes"].items()) or "—"
        cats = "\n".join(f"  • {CATEGORY_LABELS.get(k, k)}: {100 * a:.0f}% ({n})" for k, a, n in s["cat_acc"]) or "  —"
        hard = "\n".join(f"  #{i} {esc(q[:40])} — {p:.0f}% ({n})" for i, q, p, n in s["hardest"]) or "  —"
        easy = "\n".join(f"  #{i} {esc(q[:40])} — {p:.0f}% ({n})" for i, q, p, n in s["easiest"]) or "  —"
        text = (
            "📊 <b>إحصائيات البوت</b>\n\n"
            f"👥 المستخدمون: <b>{s['users']}</b> (اليوم +{s['new_today']}، 7 أيام +{s['new_7d']})\n"
            f"🔥 نشطون اليوم: <b>{s['active_today']}</b> · آخر 7 أيام: <b>{s['active_7d']}</b>\n"
            f"🔁 عادوا لاختبارين فأكثر: {s['returning']}\n\n"
            f"✅ اختبارات منتهية: {s['finished_total']} (اليوم {s['finished_today']}، 7 أيام {s['finished_7d']})\n"
            f"📉 نسبة الإكمال (7 أيام): {done}\n⭐ متوسط التقييم (الكامل): {avg}\n🎮 الأوضاع: {modes}\n\n"
            f"🎯 نسبة الصحة حسب التصنيف:\n{cats}\n\n🧗 أصعب الأسئلة:\n{hard}\n\n🌱 أسهل الأسئلة:\n{easy}\n\n"
            f"📚 البنك: {s['bank_active']} مفعّل ({s['bank_disabled']} معطّل) · 🇬🇧 {s['bank_en']} · 🖼 {s['bank_img']}\n"
            f"🚩 أسئلة عليها بلاغات مفتوحة: {s['open_reports']}\n"
            f"💡 اقتراحات تنتظر المراجعة: {s['pending_suggestions']} · 🚫 حظروا البوت: {s['blocked_users']}\n"
            f"👥 مجموعات جرّبت الألعاب الجماعية: {db.group_count()}\n"
            f"\n{growth_text(ctx)}\n"
            f"🕒 {time.strftime('%H:%M:%S', time.gmtime(time.time() + 3 * 3600))} (توقيت مكة)")
        await nav(c, text, kb(BACK))

    # ── البلاغات ────────────────────────────────────────────
    @r.callback_query(F.data == "ad:rep")
    async def cb_reports(c: CallbackQuery):
        await c.answer()
        rows, games = db.open_reports_grouped(), db.game_reports_grouped()
        if not rows and not games:
            await nav(c, "لا توجد بلاغات مفتوحة 🎉", kb(BACK), None)
            return
        thr = ctx.report_threshold()
        btns = [[btn(f"{'🔴' if x['n'] >= thr else '🟡'} #{x['qid']} ({x['n']}) {x['q'][:30]}", f"ad:rv:{x['qid']}")]
                for x in rows]
        btns += [[btn(f"{'🔴' if x['n'] >= thr else '🟡'} 🎮 ({x['n']}) {x['label'][:34]}", f"ad:gv:{x['kind']}:{x['key']}")]
                 for x in games]
        await nav(c, f"🚩 البلاغات المفتوحة (🔴 = وصلت العتبة {thr}):", kb(*btns, BACK), None)

    # بلاغات عناصر الألعاب: التعديل الدائم في data/games.json، لكن يمكنك هنا إخفاء العنصر فورًا من اللعبة
    @r.callback_query(F.data.regexp(r"^ad:gv:(tf|song|ord|char|quote|anime):[0-9a-f]{12}$"))
    async def cb_game_review(c: CallbackQuery):
        await c.answer()
        _, _, kind, key = c.data.split(":")
        info = db.game_report_info(kind, key)
        if not info:
            await c.message.answer("هذا البلاغ تمّت مراجعته.", reply_markup=kb(BACK))
            return
        reasons = "\n".join(f"  • {k}: {v}" for k, v in info["reasons"].items())
        rows = [[btn("🙈 تجاهل البلاغات", f"ad:gd:{kind}:{key}")]]
        if kind != "ord":
            rows.insert(0, [btn("🚫 أخفِه من اللعبة", f"ad:gh:{kind}:{key}")])
        await c.message.answer(f"🎮 <b>بلاغ على عنصر لعبة</b> ({info['n']})\n{esc(info['label'])}\n\nالأسباب:\n{esc(reasons)}",
                               parse_mode="HTML", reply_markup=kb(*rows, BACK))

    @r.callback_query(F.data.regexp(r"^ad:gh:(tf|song|char|quote|anime):[0-9a-f]{12}$"))
    async def cb_game_hide(c: CallbackQuery):
        _, _, kind, key = c.data.split(":")
        db.hide_game_item(key)
        db.close_game_reports(kind, key, "resolved")
        await c.answer("🚫 أُخفي من اللعبة", show_alert=True)

    @r.callback_query(F.data.regexp(r"^ad:gd:(tf|song|ord|char|quote|anime):[0-9a-f]{12}$"))
    async def cb_game_dismiss(c: CallbackQuery):
        _, _, kind, key = c.data.split(":")
        db.close_game_reports(kind, key, "dismissed")
        await c.answer("🙈 تم تجاهل البلاغات", show_alert=True)

    @r.callback_query(F.data.startswith("ad:rv:"))
    async def cb_review(c: CallbackQuery):
        await c.answer()
        qid = int(c.data.split(":")[2])
        reasons = "\n".join(f"  • {k}: {v}" for k, v in db.report_reasons(qid).items()) or "  —"
        await c.message.answer(f"🚩 أسباب البلاغات على #{qid}:\n{reasons}")
        await show_q(c.message, qid)
        await c.message.answer("بعد المراجعة:", reply_markup=kb(
            [btn("🙈 تجاهل البلاغات", f"ad:dm:{qid}")], BACK))

    @r.callback_query(F.data.startswith("ad:dm:"))
    async def cb_dismiss(c: CallbackQuery):
        db.close_reports(int(c.data.split(":")[2]), "dismissed")
        await c.answer("تم تجاهل البلاغات", show_alert=True)

    # ── عرض/تعديل سؤال ──────────────────────────────────────
    # ── المحتوى: عبارات صح/غلط وأنمي من اللوحة (تُحفظ في القاعدة فتشملها النسخ الاحتياطية) ──
    @r.callback_query(F.data == "ad:ct")
    async def cb_content(c: CallbackQuery):
        await c.answer()
        await nav(c, "📚 <b>إدارة المحتوى</b>\nما تضيفه هنا يظهر فورًا في البوت ولا يحتاج إعادة رفع.",
                  kb([btn("➕ عبارة صح/غلط", "ad:ctf"), btn("➕ أنمي", "ad:can")],
                     [btn(f"🙈 المخفيّات ({len(db.game_hidden())})", "ad:hid")], BACK))

    @r.callback_query(F.data.in_({"ad:ctf", "ad:can"}))
    async def cb_content_add(c: CallbackQuery, state: FSMContext):
        await c.answer()
        act = "ctf" if c.data == "ad:ctf" else "can"
        await state.set_state(Flow.wait)
        await state.update_data(act=act)
        await c.message.answer(TF_HELP if act == "ctf" else ANIME_HELP, parse_mode="HTML",
                               reply_markup=kb([btn("إلغاء", "ad:ct")]))

    def hidden_labels() -> dict[str, str]:
        labels = {item_key(x[0]): "✅❌ " + x[0] for x in load_games()["tf"]}
        labels.update({item_key(row[0]): "✅❌ " + row[0] for _, row in db.extras("tf")})
        labels.update({hkey(a): "🎬 " + a["ar"] for a in load_anime() + [a for _, a in db.extras("anime")]})
        return labels

    @r.callback_query(F.data == "ad:hid")
    async def cb_hidden(c: CallbackQuery):
        await c.answer()
        labels = hidden_labels()
        hid = sorted(db.game_hidden())[:25]
        if not hid:
            await nav(c, "لا يوجد شيء مخفي ✅", kb([btn("⬅️ المحتوى", "ad:ct")]))
            return
        await nav(c, "🙈 المخفيّات (اضغط لإعادة الإظهار):",
                  kb(*[[btn(("↩️ " + labels.get(k, "عنصر لعبة " + k))[:50], f"ad:uh:{k}")] for k in hid],
                     [btn("⬅️ المحتوى", "ad:ct")]))

    @r.callback_query(F.data.regexp(r"^ad:uh:[0-9a-f]{12}$"))
    async def cb_unhide(c: CallbackQuery):
        db.unhide_game_item(c.data.split(":")[2])
        await c.answer("↩️ أُعيد", show_alert=True)

    @r.callback_query(F.data == "ad:find")
    async def cb_find(c: CallbackQuery, state: FSMContext):
        await c.answer()
        await state.set_state(Flow.wait)
        await state.update_data(act="find")
        await c.message.answer("أرسل رقم السؤال أو جزءًا من نصه (عربي/English):")

    @r.callback_query(F.data.regexp(r"^ad:q:\d+$"))
    async def cb_open_q(c: CallbackQuery):
        await c.answer()
        await show_q(c.message, int(c.data.split(":")[2]))

    @r.callback_query(F.data.startswith("ad:t:"))
    async def cb_toggle(c: CallbackQuery):
        qid = int(c.data.split(":")[2])
        q = db.get_question(qid)
        db.set_question_active(qid, not q.active)
        if q.active:                          # التعطيل يُغلق البلاغات المفتوحة عليه
            db.close_reports(qid, "resolved")
        await c.answer("تم التعطيل" if q.active else "تم التفعيل")
        await show_q(c.message, qid, edit=True)

    @r.callback_query(F.data.startswith("ad:x:"))
    async def cb_delete(c: CallbackQuery):
        qid = int(c.data.split(":")[2])
        ok = db.delete_question(qid)
        await c.answer("🗑 حُذف" if ok else "أسئلة الملف لا تُحذف (عطّلها بدل ذلك)", show_alert=True)

    PROMPTS = {
        "q": "أرسل نص السؤال الجديد:",
        "o": "أرسل 4 خيارات، كل خيار في سطر:",
        "i": "أرسل الصورة الجديدة (كصورة)، أو أرسل كلمة «حذف» لإزالتها:",
        "en": "أرسل النسخة الإنجليزية (5 أسطر: السؤال ثم 4 خيارات بنفس ترتيب العربي)، أو «حذف» لإزالتها:",
    }

    @r.callback_query(F.data.regexp(r"^ad:e:\d+:(q|o|i|en|a|d|c)$"))
    async def cb_edit(c: CallbackQuery, state: FSMContext):
        await c.answer()
        _, _, qid, field = c.data.split(":")
        qid = int(qid)
        q = db.get_question(qid)
        if field in PROMPTS:
            await state.set_state(Flow.wait)
            await state.update_data(act="edit", qid=qid, field=field)
            await c.message.answer(PROMPTS[field])
        elif field == "a":
            await c.message.answer("اختر الجواب الصحيح:", reply_markup=kb(
                [btn(str(i + 1), f"ad:sa:{qid}:{i}") for i in range(len(q.options))]))
        elif field == "d":
            await c.message.answer("اختر الصعوبة الأساسية:", reply_markup=kb(
                [btn(str(i), f"ad:sd:{qid}:{i}") for i in range(1, 6)],
                [btn(str(i), f"ad:sd:{qid}:{i}") for i in range(6, 11)]))
        else:
            await c.message.answer("اختر التصنيف:", reply_markup=kb(
                *[[btn(lbl, f"ad:sc:{qid}:{k}")] for k, lbl in CATEGORY_LABELS.items()]))

    @r.callback_query(F.data.regexp(r"^ad:s[adc]:\d+:"))
    async def cb_set_simple(c: CallbackQuery):
        _, kind, qid, val = c.data.split(":")
        qid = int(qid)
        if kind == "sa":
            db.update_question(qid, answer=int(val))
        elif kind == "sd":
            db.update_question(qid, base_difficulty=float(val))
        else:
            db.update_question(qid, category=val)
        await c.answer("✅ تم الحفظ")
        await show_q(c.message, qid)

    # ── إضافة سؤال جديد (معالج خطوة بخطوة) ─────────────────
    @r.callback_query(F.data == "ad:add")
    async def cb_add(c: CallbackQuery, state: FSMContext):
        await c.answer()
        await state.set_state(Flow.wait)
        await state.update_data(act="add", step="text", draft={})
        await c.message.answer("➕ <b>سؤال جديد</b>\nأرسل نص السؤال.\n"
                               "💡 لسؤال <b>بصورة</b>: أرسل الصورة ومعها النص كتعليق.",
                               parse_mode="HTML", reply_markup=kb([btn("إلغاء", "ad:home")]))

    async def add_next(m: Message, state: FSMContext, step: str, draft: dict):
        await state.update_data(step=step, draft=draft)
        if step == "options":
            await m.answer("أرسل 4 خيارات، كل خيار في سطر:")
        elif step == "answer":
            await m.answer("اختر الجواب الصحيح:", reply_markup=kb(
                [btn(str(i + 1), f"ad:aa:{i}") for i in range(4)]))
        elif step == "diff":
            await m.answer("اختر الصعوبة (1 سهل جدًا … 10 صعب جدًا):", reply_markup=kb(
                [btn(str(i), f"ad:ad:{i}") for i in range(1, 6)], [btn(str(i), f"ad:ad:{i}") for i in range(6, 11)]))
        elif step == "cat":
            await m.answer("اختر التصنيف:", reply_markup=kb(
                *[[btn(lbl, f"ad:ac:{k}")] for k, lbl in CATEGORY_LABELS.items()]))
        elif step == "en":
            await m.answer("🇬🇧 أرسل النسخة الإنجليزية (5 أسطر: السؤال ثم 4 خيارات بنفس الترتيب)، أو تخطَّ:",
                           reply_markup=kb([btn("تخطّي ⏭", "ad:ae:skip")]))

    async def save_new(m: Message, state: FSMContext, draft: dict):
        qid = db.add_question(draft["text"], draft["options"], draft["answer"], draft["cat"], draft["diff"],
                              image=draft.get("image"), q_en=draft.get("q_en"), options_en=draft.get("options_en"))
        await state.clear()
        await m.answer(f"✅ تمت الإضافة برقم #{qid}")
        await show_q(m, qid)

    async def pick(c: CallbackQuery, state: FSMContext, key: str, value, nxt: str):
        data = await state.get_data()
        if data.get("act") != "add":
            await c.answer("انتهت الجلسة، ابدأ من جديد")
            return
        await c.answer()
        draft = data["draft"]
        draft[key] = value
        await add_next(c.message, state, nxt, draft)

    @r.callback_query(F.data.regexp(r"^ad:aa:\d$"))
    async def cb_aa(c: CallbackQuery, state: FSMContext):
        await pick(c, state, "answer", int(c.data.split(":")[2]), "diff")

    @r.callback_query(F.data.regexp(r"^ad:ad:\d+$"))
    async def cb_ad(c: CallbackQuery, state: FSMContext):
        await pick(c, state, "diff", int(c.data.split(":")[2]), "cat")

    @r.callback_query(F.data.startswith("ad:ac:"))
    async def cb_ac(c: CallbackQuery, state: FSMContext):
        await pick(c, state, "cat", c.data.split(":")[2], "en")

    @r.callback_query(F.data == "ad:ae:skip")
    async def cb_ae(c: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        if data.get("act") != "add":
            await c.answer("انتهت الجلسة")
            return
        await c.answer()
        await save_new(c.message, state, data["draft"])

    # ── استقبال رسائل المشرف حسب الحالة ────────────────────
    @r.message(Flow.wait, ~F.text.startswith("/"))
    async def on_input(m: Message, state: FSMContext):
        data = await state.get_data()
        act = data.get("act")
        text = (m.text or m.caption or "").strip()
        photo = f"tg:{m.photo[-1].file_id}" if m.photo else None

        if act in ("ctf", "can"):
            if act == "ctf":
                row, err = parse_tf(text)
            else:
                known = {a["key"] for a in load_anime()} | {a["key"] for _, a in db.extras("anime")}
                row, err = parse_anime(text, known)
            if err:
                await m.answer(f"❌ {err}\nصحّح وأرسل ثانية، أو اضغط إلغاء.", reply_markup=kb([btn("إلغاء", "ad:ct")]))
                return
            await state.clear()
            db.add_extra("tf" if act == "ctf" else "anime", row)
            await m.answer("✅ أُضيف ويظهر في البوت فورًا.", reply_markup=kb([btn("➕ إضافة أخرى", f"ad:{act}")],
                                                                              [btn("⬅️ المحتوى", "ad:ct")]))
            return

        if act == "find":
            await state.clear()
            if text.isdigit():
                await show_q(m, int(text))
                return
            rows = db.search_questions(text)
            if not rows:
                await m.answer("ما لقيت شيئًا.", reply_markup=kb(BACK))
                return
            await m.answer("النتائج:", reply_markup=kb(
                *[[btn(f"{'🔴' if x['flagged'] else '🟢'} #{x['id']} {x['q'][:40]}", f"ad:q:{x['id']}")] for x in rows], BACK))

        elif act == "add":
            draft, step = data["draft"], data["step"]
            if step == "text":
                if photo:
                    draft["image"] = photo
                if not text:
                    await state.update_data(draft=draft)
                    await m.answer("✅ استلمت الصورة. الآن أرسل نص السؤال:" if photo else "أرسل نصًا للسؤال.")
                    return
                draft["text"] = text
                await add_next(m, state, "options", draft)
            elif step == "options":
                opts = [x.strip() for x in text.splitlines() if x.strip()]
                if len(opts) != 4 or len(set(opts)) != 4:
                    await m.answer("لازم 4 خيارات مختلفة، كل واحد في سطر. أعد المحاولة:")
                    return
                draft["options"] = opts
                await add_next(m, state, "answer", draft)
            elif step == "en":
                parsed = parse_en(text)
                if not parsed:
                    await m.answer("لازم 5 أسطر بالضبط (السؤال + 4 خيارات)، أو اضغط تخطّي:")
                    return
                draft["q_en"], draft["options_en"] = parsed
                await save_new(m, state, draft)

        elif act == "edit":
            qid, field = data["qid"], data["field"]
            q = db.get_question(qid)
            if field == "q" and text:
                db.update_question(qid, q=text)
            elif field == "o":
                opts = [x.strip() for x in text.splitlines() if x.strip()]
                if len(opts) != 4 or len(set(opts)) != 4:
                    await m.answer("لازم 4 خيارات مختلفة. أعد المحاولة:")
                    return
                db.update_question(qid, options=opts)
            elif field == "i":
                if photo:
                    db.update_question(qid, image=photo)
                elif text == "حذف":
                    db.update_question(qid, image=None)
                elif text.startswith("https://"):
                    db.update_question(qid, image=text)
                else:
                    await m.answer("أرسل صورة، أو رابط https، أو «حذف».")
                    return
            elif field == "en":
                if text == "حذف":
                    db.update_question(qid, q_en=None, options_en=None)
                else:
                    parsed = parse_en(text)
                    if not parsed:
                        await m.answer("لازم 5 أسطر بالضبط. أعد المحاولة:")
                        return
                    db.update_question(qid, q_en=parsed[0], options_en=parsed[1])
            else:
                await m.answer("لم أفهم، أعد المحاولة:")
                return
            await state.clear()
            await m.answer("✅ تم الحفظ")
            await show_q(m, qid)

        elif act == "bcast":
            if not text and not photo:
                await m.answer("أرسل نصًا أو صورة.")
                return
            if len(text) > 1000 and photo or len(text) > 4000:
                await m.answer("النص طويل جدًا (الحد 4000 حرف، أو 1000 مع صورة).")
                return
            await state.update_data(act="bcast_ready", bc_text=text, bc_photo=(photo[3:] if photo else None))
            await send_one(m.bot, m.chat.id, text, photo[3:] if photo else None)         # معاينة
            n_all, n_ar, n_en = (len(audience(a)) for a in ("all", "ar", "en"))
            await m.answer("👆 هذه معاينة رسالتك. اختر الجمهور:", reply_markup=kb(
                [btn(f"👥 الكل ({n_all})", "ad:bs:all")],
                [btn(f"🇸🇦 العربية ({n_ar})", "ad:bs:ar"), btn(f"🇬🇧 English ({n_en})", "ad:bs:en")],
                [btn("📤 أرسلها لي فقط (تجربة)", "ad:bs:me")], [btn("❌ إلغاء", "ad:home")]))

        elif act == "channel":
            await state.clear()
            val = "" if text.lower() in ("off", "تعطيل") else text if text.startswith("@") else f"@{text}"
            db.set_setting("required_channel", val)
            await m.answer(f"✅ القناة الآن: {val or 'معطّلة'}")

        elif act == "addadmin":
            await state.clear()
            if not ctx.is_owner(m.from_user.id):
                return
            if not text.lstrip("-").isdigit():
                await m.answer("أرسل رقم المستخدم (يعرفه من /myid).")
                return
            db.add_admin(int(text))
            await m.answer(f"✅ أضفت المشرف {text}")

    # ── الإعدادات ───────────────────────────────────────────
    def settings_view():
        ch = ctx.channel() or "معطّل"
        text = ("⚙️ <b>الإعدادات</b>\n\n"
                f"⏱ مؤقت السؤال: <b>{ctx.timer() or 'بدون'}</b> ثانية\n"
                f"⏳ الانتظار بين الاختبارات الكاملة: <b>{ctx.cooldown()}</b> دقيقة\n"
                f"📢 قناة الاشتراك الإجباري: <b>{esc(ch)}</b>\n"
                f"🚩 عتبة إشعار البلاغات: <b>{ctx.report_threshold()}</b> بلاغات مستقلة · "
                f"حد المستخدم اليومي: <b>{ctx.reports_per_day()}</b>\n"
                f"💾 النسخة الأسبوعية التلقائية: <b>{'✅ مفعّلة' if backup_enabled(ctx) else '❌ متوقفة'}</b> "
                f"(آخر نسخة: {last_backup_text(ctx)})\n{chat_status_text(ctx)}")
        markup = kb(
            [btn("⏱ " + (str(v) if v else "بدون"), f"ad:st:{v}") for v in (0, 15, 20, 30, 45, 60)],
            [btn(f"⏳ {v}", f"ad:cd:{v}") for v in (0, 10, 30, 60, 120)],
            [btn(f"🚩 عتبة {v}", f"ad:rt:{v}") for v in (1, 2, 3, 5)],
            [btn(f"🚩 يوميًا {v}", f"ad:rd:{v}") for v in (1, 3, 5, 10)],
            [btn("💾 تفعيل النسخ الأسبوعي", "ad:ab:1"), btn("💾 إيقافه", "ad:ab:0")],
            [btn("🛟 أرسل نسخة لقناة النسخ الآن", "ad:cb")],
            [btn("👥 ألعاب المجموعات: " + ("✅ تعمل (اضغط للإيقاف)" if db.get_setting("grp_enabled", "1") == "1" else "❌ متوقفة (اضغط للتشغيل)"), "ad:grp")],
            [btn("📢 تغيير/تعطيل القناة", "ad:ch")], BACK)
        return text, markup

    @r.callback_query(F.data == "ad:grp")
    async def cb_groups_toggle(c: CallbackQuery):
        on = db.get_setting("grp_enabled", "1") == "1"
        db.set_setting("grp_enabled", "0" if on else "1")
        await c.answer("👥 أُوقفت ألعاب المجموعات" if on else "👥 عادت ألعاب المجموعات", show_alert=True)
        text, markup = settings_view()
        await nav(c, text, markup)

    @r.callback_query(F.data == "ad:set")
    async def cb_settings(c: CallbackQuery):
        await c.answer()
        text, markup = settings_view()
        await nav(c, text, markup)

    @r.callback_query(F.data.regexp(r"^ad:(st|cd|rt|rd):\d+$"))
    async def cb_set_value(c: CallbackQuery):
        _, kind, v = c.data.split(":")
        key = {"st": "timer_seconds", "cd": "cooldown_minutes", "rt": "report_threshold", "rd": "reports_per_day"}[kind]
        db.set_setting(key, v)
        await c.answer("✅ تم الحفظ")
        text, markup = settings_view()
        try:
            await c.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        except TelegramAPIError:
            pass

    @r.callback_query(F.data.regexp(r"^ad:ab:[01]$"))
    async def cb_auto_backup(c: CallbackQuery):
        db.set_setting("auto_backup", c.data.split(":")[2])
        await c.answer("✅ تم الحفظ")
        text, markup = settings_view()
        await nav(c, text, markup)

    @r.callback_query(F.data == "ad:cb")
    async def cb_chat_backup(c: CallbackQuery):
        await c.answer("⏳ أرسل النسخة…")
        ok, msg = await send_chat_backup(c.bot, ctx)
        await c.message.answer(("✅ " if ok else "❌ ") + msg)

    @r.callback_query(F.data == "ad:ch")
    async def cb_channel(c: CallbackQuery, state: FSMContext):
        await c.answer()
        await state.set_state(Flow.wait)
        await state.update_data(act="channel")
        await c.message.answer("أرسل معرّف القناة مثل @Anime1Galaxy (والبوت لازم يكون أدمن فيها)، أو أرسل «تعطيل»:")

    # ── المشرفون (للمالك فقط) ───────────────────────────────
    @r.callback_query(F.data == "ad:adm")
    async def cb_admins(c: CallbackQuery):
        await c.answer()
        if not ctx.is_owner(c.from_user.id):
            await c.message.answer("هذا القسم للمالك فقط.")
            return
        ids = ctx.admin_ids()
        rows = [[btn(f"🗑 {i}", f"ad:rm:{i}")] for i in ids if i != c.from_user.id and not ctx.is_owner(i)]
        await nav(c, "👥 المشرفون الحاليون:\n" + "\n".join(
            f"• {i}{' 👑' if ctx.is_owner(i) else ''}" for i in ids),
            kb(*rows, [btn("➕ إضافة مشرف", "ad:addadm")], BACK), None)

    @r.callback_query(F.data == "ad:addadm")
    async def cb_add_admin(c: CallbackQuery, state: FSMContext):
        await c.answer()
        if not ctx.is_owner(c.from_user.id):
            return
        await state.set_state(Flow.wait)
        await state.update_data(act="addadmin")
        await c.message.answer("أرسل رقم تليجرام للمشرف الجديد (يعرفه بإرسال /myid للبوت):")

    @r.callback_query(F.data.startswith("ad:rm:"))
    async def cb_rm_admin(c: CallbackQuery):
        if not ctx.is_owner(c.from_user.id):
            await c.answer()
            return
        ok = db.remove_admin(int(c.data.split(":")[2]))
        await c.answer("✅ أُزيل" if ok else "لا يمكن إزالة هذا الحساب", show_alert=True)

    # ── جلب أسئلة الصور ─────────────────────────────────────
    @r.callback_query(F.data == "ad:img")
    async def cb_img(c: CallbackQuery):
        await c.answer()
        await nav(c,
            "🖼 <b>أسئلة «من هذه الشخصية؟»</b>\nأجلب ~200 شخصية من AniList (وJikan كبديل). الاسم والصورة يأتيان "
            "من سجل واحد في المصدر فلا يختلفان، والأشهر = الأسهل.\n\n"
            "💡 تقدر أيضًا إضافة صورك الخاصة من «➕ سؤال جديد».",
            kb([btn("▶️ ابدأ الجلب", "ad:img:go")], BACK))

    @r.callback_query(F.data == "ad:img:go")
    async def cb_img_go(c: CallbackQuery):
        await c.answer("بدأ الجلب… سأردّ عليك خلال دقيقة كحد أقصى")
        note = await c.message.answer("⏳ أتصل بـ AniList ثم Jikan (لن أنتظر أكثر من ~50 ثانية)…")
        try:
            qs, src = await anilist.fetch_image_questions(post=fetch_post, get=fetch_get)
        except Exception as e:  # noqa: BLE001
            await note.edit_text(f"❌ فشل الجلب: {e or 'انتهت المهلة'}\nغالبًا الاستضافة تحجب هذه المواقع. "
                                 "استخدم «➕ سؤال جديد» وأرسل صورك بنفسك.", reply_markup=kb(BACK))
            return
        n = db.upsert_questions(qs)
        await note.edit_text(f"✅ أضفت/حدّثت {n} سؤال صورة من {src}.\nراجع عيّنة من «🔎 بحث» وعطّل أي سؤال تراه غلطًا.",
                             reply_markup=kb(BACK))

    # ── اقتراحات اللاعبين ───────────────────────────────────
    @r.callback_query(F.data == "ad:sg")
    async def cb_suggestions(c: CallbackQuery):
        await c.answer()
        rows = db.pending_suggestions(10)
        if not rows:
            await nav(c, "لا توجد اقتراحات تنتظر المراجعة 🎉", kb(BACK), None)
            return
        btns = [[btn(f"#{x['id']} {x['q'][:40]}", f"ad:sv:{x['id']}")] for x in rows]
        await nav(c, f"💡 اقتراحات تنتظر المراجعة ({db.pending_count()}):", kb(*btns, BACK), None)

    def sg_card(sg: dict) -> str:
        opts = "\n".join(f"{'✅' if i == 0 else '▫️'} {esc(o)}" for i, o in enumerate(sg["options"]))
        return f"💡 <b>اقتراح #{sg['id']}</b> من {sg['tg_id']}\n\n<b>{esc(sg['q'])}</b>\n{opts}"

    @r.callback_query(F.data.regexp(r"^ad:sv:\d+$"))
    async def cb_sg_view(c: CallbackQuery):
        await c.answer()
        sg = db.get_suggestion(int(c.data.split(":")[2]))
        if not sg or sg["status"] != "pending":
            await c.message.answer("هذا الاقتراح تمّت مراجعته.", reply_markup=kb(BACK))
            return
        await c.message.answer(sg_card(sg), parse_mode="HTML", reply_markup=kb(
            [btn("✅ قبول", f"ad:sga:{sg['id']}"), btn("❌ رفض", f"ad:sgr:{sg['id']}")], [btn("◀️ الاقتراحات", "ad:sg")]))

    @r.callback_query(F.data.regexp(r"^ad:sga:\d+$"))
    async def cb_sg_accept(c: CallbackQuery):
        await c.answer()
        sid = int(c.data.split(":")[2])
        await c.message.answer("اختر التصنيف:", reply_markup=kb(
            *[[btn(lbl, f"ad:sgc:{sid}:{k}")] for k, lbl in CATEGORY_LABELS.items()]))

    @r.callback_query(F.data.regexp(r"^ad:sgc:\d+:\w+$"))
    async def cb_sg_cat(c: CallbackQuery):
        await c.answer()
        _, _, sid, cat = c.data.split(":")
        await c.message.answer("اختر الصعوبة (1 سهل … 10 صعب):", reply_markup=kb(
            [btn(str(i), f"ad:sgd:{sid}:{cat}:{i}") for i in range(1, 6)],
            [btn(str(i), f"ad:sgd:{sid}:{cat}:{i}") for i in range(6, 11)]))

    @r.callback_query(F.data.regexp(r"^ad:sgd:\d+:\w+:\d+$"))
    async def cb_sg_done(c: CallbackQuery):
        _, _, sid, cat, diff = c.data.split(":")
        sg = db.get_suggestion(int(sid))
        if not sg or sg["status"] != "pending" or cat not in CATEGORY_LABELS:
            await c.answer("تمّت مراجعته أو غير صالح", show_alert=True)
            return
        order = [0, 1, 2, 3]
        ctx.rng.shuffle(order)
        qid = db.add_question(sg["q"], [sg["options"][i] for i in order], order.index(0), cat, int(diff), source="user")
        db.set_suggestion_status(sg["id"], "approved", qid)
        await c.answer("✅ أُضيف للبنك")
        try:
            L = db.get_lang(sg["tg_id"])
            await c.bot.send_message(sg["tg_id"], t(L, "sg_accepted", q=esc(sg["q"])), parse_mode="HTML")
        except TelegramAPIError:
            pass
        await show_q(c.message, qid)

    @r.callback_query(F.data.regexp(r"^ad:sgr:\d+$"))
    async def cb_sg_reject(c: CallbackQuery):
        db.set_suggestion_status(int(c.data.split(":")[2]), "rejected")
        await c.answer("❌ رُفض", show_alert=True)

    # ── رسالة جماعية ────────────────────────────────────────
    async def send_one(bot: Bot, chat_id: int, text: str, photo: str | None) -> None:
        if photo:
            await bot.send_photo(chat_id, photo, caption=text or None)
        else:
            await bot.send_message(chat_id, text)

    @r.callback_query(F.data == "ad:bc")
    async def cb_broadcast(c: CallbackQuery, state: FSMContext):
        await c.answer()
        await state.set_state(Flow.wait)
        await state.update_data(act="bcast")
        await c.message.answer("📣 <b>رسالة جماعية</b>\nأرسل الرسالة (نصًا، أو صورة ومعها النص كتعليق).\n"
                               "سأعرض لك معاينة، ثم تختار الجمهور وتؤكد قبل الإرسال.\nللإلغاء: /cancel", parse_mode="HTML")

    def audience(aud: str):
        return db.broadcast_targets(aud if aud in ("ar", "en") else None)

    @r.callback_query(F.data.regexp(r"^ad:bs:(all|ar|en|me)$"))
    async def cb_bc_audience(c: CallbackQuery, state: FSMContext):
        await c.answer()
        data = await state.get_data()
        if data.get("act") != "bcast_ready":
            await c.message.answer("انتهت الجلسة. ابدأ من «📣 رسالة جماعية».", reply_markup=kb(BACK))
            return
        aud = c.data.split(":")[2]
        if aud == "me":
            await send_one(c.bot, c.message.chat.id, data["bc_text"], data["bc_photo"])
            await c.message.answer("📤 هذه تجربة وصلتك أنت فقط. اختر الجمهور للإرسال الفعلي.")
            return
        wait = float(db.get_setting("last_broadcast", "0") or 0) + BROADCAST_GAP - time.time()
        if wait > 0:
            await c.message.answer(f"⏳ انتظر {int(wait // 60) + 1} دقيقة قبل رسالة جماعية أخرى (حماية من الإرسال بالخطأ).")
            return
        n = len(audience(aud))
        await c.message.answer(f"⚠️ سيُرسَل هذا إلى <b>{n}</b> مستخدم. متأكد؟", parse_mode="HTML", reply_markup=kb(
            [btn("✅ نعم، أرسل", f"ad:bg:{aud}")], [btn("❌ إلغاء", "ad:home")]))

    async def run_broadcast(bot: Bot, admin_chat: int, targets: list[int], text: str, photo: str | None) -> dict:
        sent = blocked = failed = 0
        note = await bot.send_message(admin_chat, f"📣 بدأ الإرسال إلى {len(targets)} مستخدم…")
        for i, uid in enumerate(targets, 1):
            try:
                try:
                    await send_one(bot, uid, text, photo)
                except TelegramRetryAfter as e:           # تليجرام يطلب التمهّل
                    await asyncio.sleep(e.retry_after)
                    await send_one(bot, uid, text, photo)
                sent += 1
            except TelegramForbiddenError:                # حظر البوت: نتوقف عن مراسلته
                db.mark_blocked(uid)
                blocked += 1
            except TelegramAPIError:
                failed += 1
            await asyncio.sleep(0.04)                     # ~25 رسالة/ثانية (حد تليجرام 30)
            if i % 100 == 0:
                try:
                    await note.edit_text(f"📣 {i}/{len(targets)} …")
                except TelegramAPIError:
                    pass
        result = {"sent": sent, "blocked": blocked, "failed": failed}
        await bot.send_message(admin_chat, f"✅ انتهى الإرسال\n📬 وصلت: {sent}\n🚫 حظروا البوت: {blocked}\n⚠️ فشلت: {failed}")
        return result

    @r.callback_query(F.data.regexp(r"^ad:bg:(all|ar|en)$"))
    async def cb_bc_go(c: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        if data.get("act") != "bcast_ready":
            await c.answer("انتهت الجلسة", show_alert=True)
            return
        wait = float(db.get_setting("last_broadcast", "0") or 0) + BROADCAST_GAP - time.time()
        if wait > 0:
            await c.answer("انتظر قليلًا قبل رسالة جماعية أخرى", show_alert=True)
            return
        targets = audience(c.data.split(":")[2])
        db.set_setting("last_broadcast", str(time.time()))
        await state.clear()
        await c.answer("بدأ الإرسال في الخلفية ✅")
        ctx.tasks.append(asyncio.create_task(
            run_broadcast(c.bot, c.message.chat.id, targets, data["bc_text"], data["bc_photo"])))

    # ── النسخة الاحتياطية ───────────────────────────────────
    @r.callback_query(F.data == "ad:bak")
    async def cb_backup(c: CallbackQuery):
        await c.answer("⏳ أجهّز النسخة…")
        with tempfile.TemporaryDirectory() as d:
            path = make_zip(ctx, Path(d))                       # مضغوطة فتُرفع أسرع
            await c.message.answer_document(FSInputFile(path), caption="💾 نسخة كاملة من قاعدة البيانات (أسئلة، لاعبون، نتائج). "
                                            "للاستعادة: فك الضغط وضع otaku.db مكان القاعدة ثم أعد التشغيل.")
        await c.message.answer("تم ✅ احتفظ بها في مكان آمن.", reply_markup=kb(BACK))

    return r


# تُستبدل في الاختبارات
fetch_post = anilist.default_post
fetch_get = anilist.default_get
