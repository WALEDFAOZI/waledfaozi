"""إشعار الأونلاين: مغلق افتراضيًا، يُفعَّل من الرئيسية، ويصل عند فتح طابور."""
import asyncio

from harness import Harness, run
from otaku_bot import online, online_notify


def dms(h, uid):
    return [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == uid]


def test_notification_is_off_by_default_and_fires_when_a_queue_opens():
    async def go():
        online.queue["quiz"].clear(); online.user_match.clear()
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        watcher = h.user(1, "Watcher")
        opener = h.user(2, "Opener")
        for u in (watcher, opener):
            h.db.upsert_user(u.id, u.first_name)
        assert online_notify.is_on(h.db, watcher.id) is False        # مغلق افتراضيًا
        await h.tap(opener, "on:j:quiz")                              # يفتح الطابور
        await asyncio.sleep(0.2)
        assert not dms(h, watcher.id)                                 # غير مشترك: لا إشعار
        await h.tap(watcher, "on:nt")                                 # يفعّل الإشعار
        assert online_notify.is_on(h.db, watcher.id) is True
        online.queue["quiz"].clear()
        await h.tap(opener, "on:j:quiz")                              # طابور جديد يُفتح
        await asyncio.sleep(0.3)
        msgs = dms(h, watcher.id)
        assert msgs and "طابور" in msgs[-1].text
        assert not dms(h, opener.id) or all("طابور" not in (c.text or "") for c in dms(h, opener.id))
        await h.tap(watcher, "on:nt")                                 # يطفئ
        assert online_notify.is_on(h.db, watcher.id) is False
    run(go())
