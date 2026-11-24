"""تثبيت الاختبارات: كل اختبار يبدأ من حالة نظيفة، ولا يترك أثرًا على الذي بعده.

بعض الوحدات تحمل إعدادات قابلة للتعديل (مهل، فترات) وحالة على مستوى الوحدة (ألعاب جارية، طوابير).
الاختبارات تغيّرها أحيانًا؛ هنا نحفظ القيم الأصلية ونرجعها بعد كل اختبار، ونفرّغ الحالة قبل كل اختبار.
"""
import pytest

from otaku_bot import arcade, daily, group, mafia_game

# (الوحدة، اسم الإعداد) — قيم تُعدَّل في بعض الاختبارات
TUNABLE = [
    (group, "LOBBY_SECONDS"), (group, "CH_LOBBY_SECONDS"), (group, "Q_SECONDS"), (group, "CH_Q_SECONDS"),
    (group, "CHAT_COOLDOWN"), (group, "START_COOLDOWN"), (group, "PAUSE"),
    (daily, "REMIND_HOUR"), (arcade, "REMIND_SECS"),
]


def _clear_shared_state():
    """حالة الألعاب الجارية والطوابير: تُفرَّغ قبل كل اختبار حتى لا تتسرب من اختبار إلى آخر."""
    mafia_game.games.clear()
    mafia_game.cooldown.clear()
    mafia_game.POST_ROOT.clear()
    arcade.matches.clear()
    arcade.user_match.clear()
    arcade.invites.clear()
    for q in arcade.queue.values():
        q.clear()


@pytest.fixture(autouse=True)
def _isolated_state():
    saved = [(mod, name, getattr(mod, name)) for mod, name in TUNABLE]
    _clear_shared_state()
    yield
    for mod, name, value in saved:
        setattr(mod, name, value)
    _clear_shared_state()
