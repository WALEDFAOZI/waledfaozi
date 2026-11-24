"""ردود البوت المؤقتة في المجموعات تُحذف وحدها بعد مدة قصيرة، والنتائج تبقى."""
import asyncio

from aiogram.types import MessageEntity

from harness import Harness
from otaku_bot import group
from test_mafia_game import GROUP, gcmd


def deletes(h):
    return [c for c in h.session.calls if type(c).__name__ == "DeleteMessage" and c.chat_id == GROUP.id]


def test_stop_notice_is_deleted_after_the_delay():
    async def go():
        old = group.NOTICE_SECS
        group.NOTICE_SECS = 0.1
        try:
            h = Harness()
            await gcmd(h, h.user(1, "Ali"), "/gstop", 700)     # لا توجد لعبة: رد مؤقت
            notices = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == GROUP.id]
            assert notices and not deletes(h)                   # ما زال ظاهرًا لحظة إرساله
            await asyncio.sleep(0.4)
            assert len(deletes(h)) == 1                         # ثم اختفى
        finally:
            group.NOTICE_SECS = old
    asyncio.run(go())
