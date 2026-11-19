"""مرجع الرد لرسائل الألعاب داخل المجموعات المرتبطة بقناة.

إذا كتب اللاعب الأمر داخل تعليقات منشور، فالرسالة تكون ردًا على النسخة التلقائية
للمنشور في المجموعة (is_automatic_forward). نرد على تلك النسخة نفسها، فتبقى رسائل
البوت في تعليقات نفس المنشور بدل أن تظهر في أسفل المجموعة.
"""
from aiogram.types import Message


def anchor_id(msg: Message) -> int:
    """معرّف الرسالة التي نرد عليها: نسخة المنشور التلقائية إن وُجدت، وإلا الرسالة نفسها."""
    rt = msg.reply_to_message
    if rt is not None and getattr(rt, "is_automatic_forward", False):
        return rt.message_id
    return msg.message_id
