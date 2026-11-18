"""تقييم حسب الدولة: اللاعب يختار دولته من أزرار، فيظهر ترتيبه بين لاعبي دولته وترتيب الدول.
(لا نطلب موقعه الجغرافي إطلاقًا: أخصّ وأبسط وبلا أي خدمة خارجية.)"""
from __future__ import annotations

import html
import logging

from aiogram import F, Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from .bot import btn, kb
from .ctx import Ctx
from .texts import t

log = logging.getLogger(__name__)
MIN_PLAYERS = 3          # أقل عدد لاعبين لتظهر الدولة في ترتيب الدول
TOP_N = 5                # عدد أفضل اللاعبين في حساب متوسط الدولة

COUNTRIES: dict[str, tuple[str, str]] = {
    "SA": ("السعودية", "Saudi Arabia"), "EG": ("مصر", "Egypt"), "IQ": ("العراق", "Iraq"), "AE": ("الإمارات", "UAE"),
    "KW": ("الكويت", "Kuwait"), "QA": ("قطر", "Qatar"), "BH": ("البحرين", "Bahrain"), "OM": ("عُمان", "Oman"),
    "JO": ("الأردن", "Jordan"), "SY": ("سوريا", "Syria"), "LB": ("لبنان", "Lebanon"), "PS": ("فلسطين", "Palestine"),
    "YE": ("اليمن", "Yemen"), "SD": ("السودان", "Sudan"), "LY": ("ليبيا", "Libya"), "TN": ("تونس", "Tunisia"),
    "DZ": ("الجزائر", "Algeria"), "MA": ("المغرب", "Morocco"), "MR": ("موريتانيا", "Mauritania"),
    "SO": ("الصومال", "Somalia"), "DJ": ("جيبوتي", "Djibouti"), "KM": ("جزر القمر", "Comoros"),
    "TR": ("تركيا", "Türkiye"), "JP": ("اليابان", "Japan"), "US": ("أمريكا", "USA"), "GB": ("بريطانيا", "UK"),
    "FR": ("فرنسا", "France"), "DE": ("ألمانيا", "Germany"), "ID": ("إندونيسيا", "Indonesia"), "MY": ("ماليزيا", "Malaysia"),
}
OTHER = "XX"


def flag(code: str) -> str:
    if code == OTHER or len(code) != 2:
        return "🌍"
    return "".join(chr(0x1F1E6 + ord(ch) - 65) for ch in code)


def name_of(code: str, L: str) -> str:
    if code == OTHER:
        return "Other" if L == "en" else "أخرى"
    ar, en = COUNTRIES[code]
    return en if L == "en" else ar


def label(code: str, L: str) -> str:
    return f"{flag(code)} {name_of(code, L)}"


def picker_markup(L: str):
    rows, row = [], []
    for code in COUNTRIES:
        row.append(btn(label(code, L), f"cp:{code}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    row.append(btn(label(OTHER, L), f"cp:{OTHER}"))
    rows.append(row)
    rows.append([btn(t(L, "cn_btn_skip"), "cn:skip")])
    return kb(*rows)


def build_countries_router(ctx: Ctx) -> Router:
    r = Router()
    db = ctx.db

    def lang(uid: int) -> str:
        return db.get_lang(uid)

    def esc(s) -> str:
        return html.escape(str(s), quote=False)

    # ── القائمة الرئيسية للقسم ─────────────────────────────
    def menu_view(uid: int):
        L = lang(uid)
        code = db.get_country(uid)
        if not code:
            return t(L, "cn_not_set"), picker_markup(L)
        text = t(L, "cn_current", c=label(code, L))
        rk = db.country_rank(uid)
        if rk:
            text += "\n" + t(L, "cn_your_rank", rank=rk)
        return text, kb([btn(t(L, "cn_btn_top"), "cn:top"), btn(t(L, "cn_btn_rank"), "cn:rank")],
                        [btn(t(L, "cn_btn_change"), "cn:set")],
                        [btn(t(L, "btn_menu"), "menu")])

    @r.message(Command("country"))
    async def cmd_country(m: Message):
        db.upsert_user(m.from_user.id, m.from_user.full_name)
        text, markup = menu_view(m.from_user.id)
        await m.answer(text, parse_mode="HTML", reply_markup=markup)

    @r.callback_query(F.data == "cn:menu")
    async def cb_menu(c: CallbackQuery):
        await c.answer()
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        text, markup = menu_view(c.from_user.id)
        await c.message.answer(text, parse_mode="HTML", reply_markup=markup)

    @r.callback_query(F.data == "cn:set")
    async def cb_set(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        await c.message.answer(t(L, "cn_pick"), reply_markup=picker_markup(L))

    @r.callback_query(F.data == "cn:skip")
    async def cb_skip(c: CallbackQuery):
        await c.answer()
        db.mark_country_asked(c.from_user.id)
        try:
            await c.message.delete()
        except TelegramAPIError:
            pass

    # ── اختيار الدولة (بالأزرار، ونفس المسار يُستخدم بعد الموقع) ──
    @r.callback_query(F.data.regexp(r"^cp:([A-Z]{2})$"))
    async def cb_pick(c: CallbackQuery):
        code = c.data.split(":")[1]
        L = lang(c.from_user.id)
        if code != OTHER and code not in COUNTRIES:
            await c.answer()
            return
        db.upsert_user(c.from_user.id, c.from_user.full_name)
        db.set_country(c.from_user.id, code)
        await c.answer(t(L, "cn_saved", c=label(code, L)))
        text, markup = menu_view(c.from_user.id)
        await c.message.answer(text, parse_mode="HTML", reply_markup=markup)

    # ── متصدرو دولتي + ترتيب الدول ─────────────────────────
    @r.callback_query(F.data == "cn:top")
    async def cb_top(c: CallbackQuery):
        await c.answer()
        uid, L = c.from_user.id, lang(c.from_user.id)
        code = db.get_country(uid)
        if not code:
            await c.message.answer(t(L, "cn_not_set"), reply_markup=picker_markup(L))
            return
        rows = db.country_players(code, 10)
        medals = ["🥇", "🥈", "🥉"]
        lines = [f"{medals[i] if i < 3 else f'{i + 1}.'} {esc(x['name'] or '?')} — <b>{x['best_score']:.1f}</b>"
                 for i, x in enumerate(rows)]
        text = t(L, "cn_top_title", c=label(code, L)) + "\n\n" + ("\n".join(lines) if lines else t(L, "cn_no_players"))
        rk = db.country_rank(uid)
        if rk:
            text += "\n\n" + t(L, "cn_your_rank", rank=rk)
        await c.message.answer(text, parse_mode="HTML", reply_markup=kb(
            [btn(t(L, "cn_btn_rank"), "cn:rank"), btn(t(L, "btn_menu"), "menu")]))

    @r.callback_query(F.data == "cn:rank")
    async def cb_rank(c: CallbackQuery):
        await c.answer()
        uid, L = c.from_user.id, lang(c.from_user.id)
        board = db.countries_ranking(MIN_PLAYERS, TOP_N)
        medals = ["🥇", "🥈", "🥉"]
        lines = [f"{medals[i] if i < 3 else f'{i + 1}.'} {label(x['code'], L)} — <b>{x['score']:.1f}</b> ({x['players']})"
                 for i, x in enumerate(board[:10])]
        text = t(L, "cn_rank_title", top=TOP_N, min=MIN_PLAYERS) + "\n\n" + ("\n".join(lines) if lines else t(L, "cn_no_countries"))
        mine = db.get_country(uid)
        pos = next((i + 1 for i, x in enumerate(board) if x["code"] == mine), None)
        if mine and pos:
            text += "\n\n" + t(L, "cn_country_pos", c=label(mine, L), pos=pos)
        await c.message.answer(text, parse_mode="HTML", reply_markup=kb(
            [btn(t(L, "cn_btn_top"), "cn:top"), btn(t(L, "btn_menu"), "menu")]))

    return r


async def maybe_ask_country(bot: Bot, ctx: Ctx, chat_id: int, uid: int) -> None:
    """بعد أول اختبار كامل نسأل مرة واحدة فقط عن دولة اللاعب (يتخطى بضغطة)."""
    db = ctx.db
    if db.get_country(uid) or db.country_asked(uid):
        return
    db.mark_country_asked(uid)
    L = db.get_lang(uid)
    try:
        await bot.send_message(chat_id, t(L, "cn_ask_first"), reply_markup=picker_markup(L))
    except TelegramAPIError as e:
        log.warning("country prompt failed: %s", e)
