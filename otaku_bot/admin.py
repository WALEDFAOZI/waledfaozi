"""لوحة تحكم المالك داخل تليجرام: كل شيء من /admin بدون الرجوع للكود.

كيف يعرف البوت أنك المالك؟
  1) عند أول تشغيل بلا مشرفين يطبع البوت في السجل (Console) «كود تفعيل» لمرة واحدة؛ أرسله له: /claim الكود
  2) أو ضع رقمك في ADMIN_IDS في ملف .env (تعرف رقمك من /myid).
المالك وحده يضيف/يحذف المشرفين.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram import BaseMiddleware
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from . import anilist
from .bot import btn, esc, kb
from .config import CATEGORY_LABELS
from .ctx import Ctx
from .texts import t


class Flow(StatesGroup):
    wait = State()          # ننتظر رسالة نصية/صورة من المشرف؛ نوع المطلوب في data["act"]


class IsAdmin(BaseFilter):
    def __init__(self, ctx: Ctx):
        self.ctx = ctx

    async def __call__(self, event) -> bool:
        u = getattr(event, "from_user", None)
        return bool(u and self.ctx.is_admin(u.id))


class ClearPending(BaseMiddleware):
    """أي زر في اللوحة (عدا خطوات المعالج نفسه) يُلغي الإدخال المعلّق، حتى لا يُفسَّر كلامك العادي بالغلط."""
    KEEP = ("ad:aa:", "ad:ad:", "ad:ac:", "ad:ae:")

    async def __call__(self, handler, event, data):
        d = getattr(event, "data", None) or ""
        state = data.get("state")
        if state is not None and d.startswith("ad:") and not d.startswith(self.KEEP):
            await state.clear()
        return await handler(event, data)


HOME = kb(
    [btn("📊 الإحصائيات", "ad:stats"), btn("🚩 البلاغات", "ad:rep")],
    [btn("➕ سؤال جديد", "ad:add"), btn("🔎 بحث/تعديل سؤال", "ad:find")],
    [btn("⚙️ الإعدادات", "ad:set"), btn("👥 المشرفون", "ad:adm")],
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
    r.message.filter(IsAdmin(ctx))
    r.callback_query.filter(IsAdmin(ctx))
    r.callback_query.outer_middleware(ClearPending())

    @r.message(Command("cancel"))
    async def cmd_cancel(m: Message, state: FSMContext):
        await state.clear()
        await m.answer("تم الإلغاء ✅", reply_markup=kb(BACK))

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
        await m.answer("🛠 <b>لوحة التحكم</b>", parse_mode="HTML", reply_markup=HOME)

    @r.callback_query(F.data == "ad:home")
    async def cb_home(c: CallbackQuery, state: FSMContext):
        await state.clear()
        await c.answer()
        await c.message.answer("🛠 <b>لوحة التحكم</b>", parse_mode="HTML", reply_markup=HOME)

    @r.message(Command("flagged"))
    async def cmd_flagged(m: Message):
        rows = db.suspicious_questions()
        await m.answer("لا توجد أسئلة مشبوهة ✅" if not rows else "⚠️ نسبة نجاحها ≤ 27%:\n\n" + "\n".join(
            f"#{x['id']} ({x['pct']}% من {x['asked']}) {x['q']}" for x in rows[:20]))

    # ── الإحصائيات ──────────────────────────────────────────
    @r.callback_query(F.data == "ad:stats")
    async def cb_stats(c: CallbackQuery):
        await c.answer()
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
            f"🚩 أسئلة عليها بلاغات مفتوحة: {s['open_reports']}")
        await c.message.answer(text, parse_mode="HTML", reply_markup=kb(BACK))

    # ── البلاغات ────────────────────────────────────────────
    @r.callback_query(F.data == "ad:rep")
    async def cb_reports(c: CallbackQuery):
        await c.answer()
        rows = db.open_reports_grouped()
        if not rows:
            await c.message.answer("لا توجد بلاغات مفتوحة 🎉", reply_markup=kb(BACK))
            return
        thr = ctx.report_threshold()
        btns = [[btn(f"{'🔴' if x['n'] >= thr else '🟡'} #{x['qid']} ({x['n']}) {x['q'][:30]}", f"ad:rv:{x['qid']}")]
                for x in rows]
        await c.message.answer(f"🚩 البلاغات المفتوحة (🔴 = وصلت العتبة {thr}):", reply_markup=kb(*btns, BACK))

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
                f"حد المستخدم اليومي: <b>{ctx.reports_per_day()}</b>")
        markup = kb(
            [btn("⏱ " + (str(v) if v else "بدون"), f"ad:st:{v}") for v in (0, 15, 20, 30, 45, 60)],
            [btn(f"⏳ {v}", f"ad:cd:{v}") for v in (0, 10, 30, 60, 120)],
            [btn(f"🚩 عتبة {v}", f"ad:rt:{v}") for v in (1, 2, 3, 5)],
            [btn(f"🚩 يوميًا {v}", f"ad:rd:{v}") for v in (1, 3, 5, 10)],
            [btn("📢 تغيير/تعطيل القناة", "ad:ch")], BACK)
        return text, markup

    @r.callback_query(F.data == "ad:set")
    async def cb_settings(c: CallbackQuery):
        await c.answer()
        text, markup = settings_view()
        await c.message.answer(text, parse_mode="HTML", reply_markup=markup)

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
        await c.message.answer("👥 المشرفون الحاليون:\n" + "\n".join(
            f"• {i}{' 👑' if ctx.is_owner(i) else ''}" for i in ids),
            reply_markup=kb(*rows, [btn("➕ إضافة مشرف", "ad:addadm")], BACK))

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
        await c.message.answer(
            "🖼 <b>أسئلة «من هذه الشخصية؟»</b>\nأجلب ~200 شخصية من AniList (وJikan كبديل). الاسم والصورة يأتيان "
            "من سجل واحد في المصدر فلا يختلفان، والأشهر = الأسهل.\n\n"
            "💡 تقدر أيضًا إضافة صورك الخاصة من «➕ سؤال جديد».",
            parse_mode="HTML", reply_markup=kb([btn("▶️ ابدأ الجلب", "ad:img:go")], BACK))

    @r.callback_query(F.data == "ad:img:go")
    async def cb_img_go(c: CallbackQuery):
        await c.answer("جارٍ الجلب… قد يأخذ دقيقة")
        note = await c.message.answer("⏳ أجلب الشخصيات…")
        try:
            qs, src = await anilist.fetch_image_questions(post=fetch_post, get=fetch_get)
        except Exception as e:  # noqa: BLE001
            await note.edit_text(f"❌ فشل الجلب: {e}\nغالبًا الاستضافة تحجب هذه المواقع. "
                                 "استخدم «➕ سؤال جديد» وأرسل صورك بنفسك.", reply_markup=kb(BACK))
            return
        n = db.upsert_questions(qs)
        await note.edit_text(f"✅ أضفت/حدّثت {n} سؤال صورة من {src}.\nراجع عيّنة من «🔎 بحث» وعطّل أي سؤال تراه غلطًا.",
                             reply_markup=kb(BACK))

    # ── النسخة الاحتياطية ───────────────────────────────────
    @r.callback_query(F.data == "ad:bak")
    async def cb_backup(c: CallbackQuery):
        await c.answer()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "otaku-backup.db"
            db.backup_to(str(p))
            await c.message.answer_document(FSInputFile(p), caption="💾 نسخة كاملة من قاعدة البيانات (أسئلة، لاعبون، نتائج).")
        await c.message.answer("احتفظ بها في مكان آمن. للاستعادة ضعها باسم otaku.db بدل القاعدة الحالية.", reply_markup=kb(BACK))

    return r


# تُستبدل في الاختبارات
fetch_post = anilist.default_post
fetch_get = anilist.default_get
