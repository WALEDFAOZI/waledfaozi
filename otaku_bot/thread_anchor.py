"""مرجع الرد لرسائل الألعاب داخل المجموعات المرتبطة بقناة.

إذا كتب اللاعب الأمر داخل تعليقات منشور، فالرسالة تكون ردًا على النسخة التلقائية
للمنشور في المجموعة (is_automatic_forward). نرد على تلك النسخة نفسها، فتبقى رسائل
البوت في تعليقات نفس المنشور بدل أن تظهر في أسفل المجموعة.
"""
from aiogram.types import Message, ReplyParameters

ANON_ADMIN_ID = 1087968824  # GroupAnonymousBot


def identity(m: Message) -> tuple[int, str]:
    """(المعرّف, الاسم) لصاحب الرسالة: القناة/المجموعة إن كان يرسل باسمها، وإلا المستخدم."""
    if m.sender_chat is not None:
        return m.sender_chat.id, (m.sender_chat.title or "قناة")
    if m.from_user is not None and m.from_user.id == ANON_ADMIN_ID:
        return m.chat.id, (m.chat.title or "المجموعة")
    u = m.from_user
    return (u.id, u.full_name) if u else (0, "؟")


def anchor_id(msg: Message) -> int:
    """معرّف الرسالة التي نرد عليها: نسخة المنشور التلقائية إن وُجدت، وإلا الرسالة نفسها."""
    rt = msg.reply_to_message
    if rt is not None and getattr(rt, "is_automatic_forward", False):
        return rt.message_id
    return msg.message_id


async def reply_anchored(m: Message, text: str, markup=None, **kw) -> None:
    """رد على الأمر نفسه، وفي تعليقات المنشور يُرد على نسخة المنشور (لا على تعليق صاحب الأمر)."""
    from aiogram.exceptions import TelegramAPIError
    try:
        await m.bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=markup,
                                 reply_parameters=ReplyParameters(message_id=anchor_id(m), allow_sending_without_reply=True),
                                 **kw)
    except TelegramAPIError:
        pass
