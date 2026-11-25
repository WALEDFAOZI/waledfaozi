"""أوامر الشطرنج في الخاص والمجموعات والقنوات: كل مكان يفتح نفس اللعبة (Mini App) برابط startapp."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyParameters

from . import chess_engine as CE
from .texts import t
from .thread_anchor import anchor_id

log = logging.getLogger(__name__)
_BOT_USERNAME = {"u": ""}


def set_username(u: str) -> None:
    _BOT_USERNAME["u"] = (u or "").lstrip("@")


def play_markup(gid: int) -> InlineKeyboardMarkup:
    url = f"https://t.me/{_BOT_USERNAME['u']}?startapp=chess_{gid}"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="♟ العب الآن", url=url)]])


def build_chess_router(ctx) -> Router:
    db = ctx.db
    r = Router(name="chess")

    @r.message(Command("chess"))
    @r.channel_post(Command("chess"))
    async def cmd_chess(m: Message):
        L = db.group_lang(m.chat.id) if m.chat.type != "private" else db.get_lang(m.from_user.id)
        if not db.game_on("chess"):
            await m.answer(t(L, "chess_off"))
            return
        if not _BOT_USERNAME["u"]:
            await m.answer(t(L, "chess_not_ready"))
            return
        if m.from_user is None:
            await m.answer(t(L, "chess_need_user"))
            return
        name = (m.from_user.first_name or "?")[:32]
        gid = CE.create(db.conn, m.from_user.id, name, m.chat.id, m.message_id)
        kw = {}
        if m.chat.type != "channel":
            kw["reply_parameters"] = ReplyParameters(message_id=anchor_id(m), allow_sending_without_reply=True)
        try:
            await m.bot.send_message(m.chat.id, t(L, "chess_lobby", name=name), parse_mode="HTML",
                                     reply_markup=play_markup(gid), **kw)
        except TelegramAPIError:
            log.warning("chess: cannot post lobby in %s", m.chat.id)

    return r


async def announce_result(bot: Bot, db, gid: int) -> None:
    """بعد انتهاء اللعبة: نتيجة في الشات الأصلي، ونتيجة في الخاص لكل لاعب، وتسجيل الإحصائيات."""
    v = CE.view(db.conn, gid, None)
    if not v or v["state"] != "done":
        return
    white, black = CE.players(db.conn, gid)
    res = v["result"]
    g = db.conn.execute("SELECT origin_chat, origin_msg FROM chess_games WHERE id=?", (gid,)).fetchone()
    for uid, color in ((white, "white"), (black, "black")):
        if uid is None:
            continue
        outcome = "draw" if res == "draw" else ("win" if res == color else "lose")
        db.record_outcome(uid, "chess", outcome)
        L = db.get_lang(uid)
        try:
            await bot.send_message(uid, t(L, "chess_result_" + outcome, name=v["white_name"] if color == "black" else v["black_name"]),
                                   parse_mode="HTML")
        except TelegramAPIError:
            pass
    if g and g["origin_chat"]:
        L = db.group_lang(g["origin_chat"])
        line = (t(L, "chess_result_draw_chat") if res == "draw"
                else t(L, "chess_result_win_chat", name=v["white_name"] if res == "white" else v["black_name"]))
        try:
            await bot.send_message(g["origin_chat"], line, parse_mode="HTML",
                                   reply_parameters=ReplyParameters(message_id=g["origin_msg"], allow_sending_without_reply=True)
                                   if g["origin_msg"] else None)
        except TelegramAPIError:
            pass
