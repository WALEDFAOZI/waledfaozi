"""تحويل أخطاء تيليجرام الخام إلى رسالة واضحة للمستخدم، مع الحل بالضبط.

الخطأ الخام (بالإنجليزي غالباً) ما يُعرض للمستخدم؛ نطابقه بأنماط معروفة ونقول له وش يسوي.
"""
from __future__ import annotations

# (نمط في نص الخطأ بحروف صغيرة، الرسالة بالعربي، الرسالة بالإنجليزي)
_PATTERNS = [
    ("bot was blocked by the user",
     "البوت محظور عندك. افتح البوت واضغط «إلغاء الحظر» أو start، ثم أعد المحاولة.",
     "The bot is blocked. Open the bot, unblock it or press start, then try again."),
    ("can't initiate conversation", 
     "البوت ما يقدر يراسلك في الخاص. افتح البوت واضغط start، ثم أعد المحاولة.",
     "The bot can't message you privately. Open the bot and press start, then try again."),
    ("chat not found",
     "البوت ما يشوف هذي المحادثة. تأكد أنه موجود فيها، وإذا كانت قناة فلازم يكون أدمن.",
     "The bot can't see this chat. Make sure it's in the chat (and an admin for channels)."),
    ("not enough rights",
     "البوت ينقصه صلاحية. أعطه صلاحية الإرسال أو النشر أو الحذف من إعدادات الأدمن.",
     "The bot lacks a permission. Give it the needed rights in the admin settings."),
    ("have no rights to send a message",
     "البوت ما عنده صلاحية إرسال الرسائل هنا. أعطه صلاحية «إرسال الرسائل».",
     "The bot can't send messages here. Give it the 'send messages' right."),
    ("message is too long",
     "النص طويل جداً على تيليجرام. جرّب تختصره.",
     "The text is too long for Telegram. Try a shorter one."),
    ("too many requests",
     "تيليجرام يطلب ننتظر شوي. جرّب بعد دقيقة.",
     "Telegram asked us to slow down. Try again in a minute."),
    ("message to edit not found",
     "الرسالة اللي تبي تعدلها ما عادت موجودة. ابدأ من جديد.",
     "That message no longer exists. Start again."),
    ("message can't be deleted",
     "ما قدر البوت يحذف هذي الرسالة. تأكد أن عنده صلاحية الحذف.",
     "The bot can't delete this message. Make sure it has the delete right."),
]

_DEFAULT_AR = "حدث خطأ غير متوقع. جرّب مرة ثانية، وإذا تكرر تواصل مع الأدمن."
_DEFAULT_EN = "Something unexpected happened. Try again, and contact the admin if it repeats."


def explain(err: object, lang: str = "ar") -> str:
    """نص مفهوم للمستخدم مع الحل. لا يعرض الخطأ الخام."""
    raw = str(err).lower()
    for pattern, ar, en in _PATTERNS:
        if pattern in raw:
            return en if lang == "en" else ar
    return _DEFAULT_EN if lang == "en" else _DEFAULT_AR
