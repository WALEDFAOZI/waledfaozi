"""رابط دعوة خاص بقناة الاشتراك الإجباري، عشان نعرف كم شخص دخل القناة عن طريقه.

- البوت ينشئ رابطًا واحدًا (name=otaku-gate) ويحفظه في الإعدادات، ويُستعمل في زر «اشترك».
- لما أحد ينضم عبر هذا الرابط، تيليجرام يرسل تحديث chat_member فيه invite_link؛ نسجّل الحدث مرة واحدة لكل شخص.
- إن تعذّر إنشاء الرابط (البوت ليس أدمنًا بصلاحية الدعوات) يرجع الرابط العام، فلا ينكسر الاشتراك.
"""
from __future__ import annotations

import json
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatMemberUpdated

log = logging.getLogger(__name__)

KEY = "gate_invite"
EVENT = "gate_link_join"
JOINED = ("member", "administrator", "creator", "restricted")


def _saved(db) -> dict:
    try:
        return json.loads(db.get_setting(KEY) or "{}")
    except ValueError:
        return {}


def public_url(channel: str) -> str:
    return f"https://t.me/{channel.lstrip('@')}"


async def invite_url(bot: Bot, db, channel: str) -> str:
    """رابط الدعوة الخاص للقناة (يُنشأ مرة واحدة ويُعاد استعماله)."""
    saved = _saved(db)
    if saved.get("ch") == channel and saved.get("url"):
        return saved["url"]
    try:
        link = await bot.create_chat_invite_link(channel, name="otaku-gate")
    except TelegramAPIError as e:
        log.warning("cannot create invite link for %s (is the bot an admin with invite rights?): %s", channel, e)
        return public_url(channel)
    db.set_setting(KEY, json.dumps({"ch": channel, "url": link.invite_link}))
    return link.invite_link


def on_join(ev: ChatMemberUpdated, db, channel: str) -> bool:
    """يسجّل من دخل القناة عبر رابطنا الخاص. يرجع True إن سُجّل حدث جديد."""
    if not channel or ev.chat.type != "channel" or not ev.invite_link:
        return False
    if (ev.chat.username or "").lower() != channel.lstrip("@").lower():
        return False
    if ev.old_chat_member.status in JOINED or ev.new_chat_member.status not in JOINED:
        return False
    saved = _saved(db)
    if not saved.get("url") or ev.invite_link.invite_link != saved["url"]:
        return False
    user = ev.new_chat_member.user
    if user.is_bot or db.has_event(user.id, EVENT):
        return False
    db.log_event(user.id, EVENT)
    return True
