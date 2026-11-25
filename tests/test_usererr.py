"""أخطاء تيليجرام تُشرح للمستخدم بالحل، بدون النص الخام."""
from otaku_bot.usererr import explain


def test_known_telegram_errors_get_a_clear_fix_in_arabic_and_english():
    assert "start" in explain("Forbidden: bot was blocked by the user")
    assert "أدمن" in explain("Bad Request: chat not found")
    assert "صلاحية" in explain("Bad Request: not enough rights to pin a message")
    assert explain("Bad Request: chat not found", "en").startswith("The bot can't see")


def test_unknown_errors_never_show_the_raw_text():
    assert explain("some weird internal thing") == "حدث خطأ غير متوقع. جرّب مرة ثانية، وإذا تكرر تواصل مع الأدمن."
    assert "weird" not in explain("some weird internal thing")
