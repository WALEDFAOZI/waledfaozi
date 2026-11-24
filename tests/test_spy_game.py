"""برا السالفة على المجموعات: الانضمام، الجولات، التصويت الخاص، والتخمين."""
import asyncio
import datetime as dt

import pytest
from aiogram.types import CallbackQuery, Chat, Message, MessageEntity, Update

from harness import Harness, run
from otaku_bot import spy_game as S

GROUP = Chat(id=-3001, type="supergroup", title="برا السالفة")


@pytest.fixture(autouse=True)
def fast():
    names = ("NEXT_SECS", "ASK_SECS", "ANSWER_SECS", "VOTE_SECS", "REVOTE_SECS", "GUESS_SECS", "LOBBY_SECS", "EDIT_GAP", "COOLDOWN_SECS")
    old = {n: getattr(S, n) for n in names}
    S.NEXT_SECS = S.ASK_SECS = S.ANSWER_SECS = S.VOTE_SECS = S.REVOTE_SECS = S.GUESS_SECS = 6
    S.LOBBY_SECS, S.EDIT_GAP, S.COOLDOWN_SECS = 4, 0.2, 0
    S.games.clear()
    yield
    for n, v in old.items():
        setattr(S, n, v)
    S.games.clear()


async def gcmd(h, user, text, mid):
    h.uid += 1
    ents = [MessageEntity(type="bot_command", offset=0, length=len(text.split()[0]))] if text.startswith("/") else None
    m = Message(message_id=mid, date=dt.datetime.now(), chat=GROUP, from_user=user, text=text, entities=ents)
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, message=m))


async def gsay(h, user, text, mid=700):
    h.uid += 1
    m = Message(message_id=mid, date=dt.datetime.now(), chat=GROUP, from_user=user, text=text)
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, message=m))


async def gtap(h, user, data, mid=600):
    h.uid += 1
    m = Message(message_id=mid, date=dt.datetime.now(), chat=GROUP, text=".")
    cb = CallbackQuery(id=str(h.uid), from_user=user, chat_instance="g", data=data, message=m)
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, callback_query=cb))


async def wait_until(cond, timeout=20.0):
    t0 = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - t0 < timeout:
        if cond():
            return True
        await asyncio.sleep(0.1)
    return False


def group_texts(h):
    return [(getattr(c, "text", None) or getattr(c, "caption", None) or "") for c in h.session.calls
            if type(c).__name__ in ("SendMessage", "SendPhoto", "EditMessageText", "EditMessageCaption", "EditMessageMedia")
            and c.chat_id == GROUP.id]


def test_full_game_rounds_vote_and_guess():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 5)]
        by_id = {u.id: u for u in users}
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        host = users[0]
        await gcmd(h, host, "/spy", 11)
        g = S.games[GROUP.id]
        for u in users[1:]:
            await gtap(h, u, f"sp:j:{g.gid}")
        await gtap(h, host, f"sp:s:{g.gid}")
        assert await wait_until(lambda: g.state == "play")
        out = next(p.uid for p in g.players.values() if p.outsider)
        ins = [u for u in g.players if u != out]
        char_en = g.char["en"]
        # الداخل يعرف الشخصية، والبرا لا يعرفها
        assert any(char_en in (c.text or "") for u in ins for c in h.session.calls
                   if getattr(c, "chat_id", None) == u and type(c).__name__ == "SendMessage")
        assert not any(char_en in (c.text or "") for c in h.session.calls
                       if getattr(c, "chat_id", None) == out and type(c).__name__ == "SendMessage")
        assert any("تم توزيع الأدوار" in x for x in group_texts(h))
        # 10 جولات: المضيف يضغط التالي، والبوت يختار السائل والمجيب
        for r in range(1, S.ROUNDS + 1):
            assert await wait_until(lambda: g.round == r)
            await asyncio.sleep(0.3)
            await gtap(h, host, f"sp:n:{g.gid}")
            assert await wait_until(lambda: g.cur is not None and g.question is None and g.round == r)
            asker, target = g.cur
            await gsay(h, by_id[asker], "سؤال عن الشخصية؟")
            assert await wait_until(lambda: g.question is not None)
            await gsay(h, by_id[target], "جواب عام")
            assert await wait_until(lambda: g.answer is not None)
        # بعد 10 جولات: الكل يختار التصويت
        assert await wait_until(lambda: g.state == "choose")
        for u in users:
            await gtap(h, u, f"sp:c:{g.gid}:vote")
        assert await wait_until(lambda: g.state == "vote")
        for u in users:
            target = out if u.id != out else ins[0]
            pm = next(x for x in users if x.id == u.id)
            await h.tap(pm, f"sp:v:{g.gid}:{target}")
        assert await wait_until(lambda: g.caught is not None or g.state == "done")
        assert g.caught == out
        idx = next(i for i, o in enumerate(g.guess_opts) if o["en"] == char_en)
        await gtap(h, by_id[out], f"sp:g:{g.gid}:{idx}")
        assert await wait_until(lambda: g.state == "done")
        assert any("فاز <b>برا السالفة</b>" in x for x in group_texts(h))     # التخمين الصحيح = فوز البرا
        assert len(h.db.conn.execute("SELECT 1 FROM group_results WHERE chat_id=? AND kind='spy'", (GROUP.id,)).fetchall()) == 4
        assert GROUP.id not in S.games
    run(go())


def test_names_are_removed_from_group_and_outsider_only_guesses_when_caught():
    async def go():
        h = Harness()
        users = [h.user(i, f"P{i}") for i in range(1, 5)]
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, users[0], "/spy", 12)
        g = S.games[GROUP.id]
        for u in users[1:]:
            await gtap(h, u, f"sp:j:{g.gid}")
        await gtap(h, users[0], f"sp:s:{g.gid}")
        assert await wait_until(lambda: g.state == "play")
        await gtap(h, users[0], f"sp:n:{g.gid}")
        assert await wait_until(lambda: g.cur is not None and g.question is None)
        asker = next(x for x in users if x.id == g.cur[0])
        await gsay(h, asker, f"هل هي {g.char['en']}؟")                  # اسم الشخصية في المجموعة
        assert any(type(c).__name__ == "DeleteMessage" for c in h.session.calls) or any("حذفت رسالتك" in x or "ما أقدر أحذفها" in x for x in group_texts(h))
        assert g.question is None                                          # الرسالة لم تُحسب سؤالًا
        out = next(p for p in g.players.values() if p.outsider)
        await gtap(h, next(x for x in users if x.id == out.uid), f"sp:g:{g.gid}:0")
        assert not S.games or g.guessed is None                            # لا تخمين قبل الكشف
        g.task.cancel()
    run(go())


def test_vote_prompt_after_each_round_and_forced_vote_at_the_cap():
    """القاعدة: بعد الجولة الأخيرة سؤال «تصويت أم جولة إضافية»، والاستمرار يضيف جولة واحدة فقط، وعند الحد الأقصى تصويت إجباري."""
    async def go():
        old = (S.ROUNDS, S.EXTRA_MAX)
        S.ROUNDS, S.EXTRA_MAX = 2, 2
        try:
            h = Harness()
            h.db.fast_answer_ratio = lambda sid: 0.0
            users = [h.user(i, f"P{i}") for i in range(1, 5)]
            by_id = {u.id: u for u in users}
            for u in users:
                h.db.upsert_user(u.id, u.first_name)
            host = users[0]
            await gcmd(h, host, "/spy", 11)
            g = S.games[GROUP.id]
            for u in users[1:]:
                await gtap(h, u, f"sp:j:{g.gid}")
            await gtap(h, host, f"sp:s:{g.gid}")
            assert await wait_until(lambda: g.state == "play")

            async def play_round(r):
                assert await wait_until(lambda: g.round == r)
                await asyncio.sleep(0.3)
                await gtap(h, host, f"sp:n:{g.gid}")
                assert await wait_until(lambda: g.cur is not None and g.question is None and g.round == r)
                asker, target = g.cur
                await gsay(h, by_id[asker], "سؤال؟")
                assert await wait_until(lambda: g.question is not None)
                await gsay(h, by_id[target], "جواب")
                assert await wait_until(lambda: g.answer is not None)

            await play_round(1)
            await play_round(2)
            assert await wait_until(lambda: g.state == "choose")         # بعد الجولة 2: السؤال
            for u in users:
                await gtap(h, u, f"sp:c:{g.gid}:more")                   # الأغلبية: استمرار
            assert await wait_until(lambda: g.extra == 1 and g.state == "play")
            await play_round(3)                                          # جولة واحدة فقط
            assert await wait_until(lambda: g.state == "choose")         # ثم السؤال من جديد
            for u in users:
                await gtap(h, u, f"sp:c:{g.gid}:more")
            assert await wait_until(lambda: g.extra == 2)
            await play_round(4)                                          # الحد الأقصى: بعدها تصويت إجباري
            assert await wait_until(lambda: g.state == "vote")
            assert g.round == 4
        finally:
            S.ROUNDS, S.EXTRA_MAX = old
    run(go())


def test_each_round_is_a_new_message_and_old_buttons_are_removed():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        users = [h.user(i, f"P{i}") for i in range(1, 5)]
        by_id = {u.id: u for u in users}
        for u in users:
            h.db.upsert_user(u.id, u.first_name)
        host = users[0]
        await gcmd(h, host, "/spy", 11)
        g = S.games[GROUP.id]
        for u in users[1:]:
            await gtap(h, u, f"sp:j:{g.gid}")
        await gtap(h, host, f"sp:s:{g.gid}")
        assert await wait_until(lambda: g.state == "play")
        ask_ids = []
        for r in (1, 2):
            await gtap(h, host, f"sp:n:{g.gid}")
            assert await wait_until(lambda: g.cur is not None and g.question is None and g.round == r)
            ask_ids.append(g.live)
            if r == 1:
                first = g.live
            await gsay(h, by_id[g.cur[0]], "سؤال؟")
            assert await wait_until(lambda: g.question is not None)
            await gsay(h, by_id[g.cur[1]], "جواب")
            assert await wait_until(lambda: g.answer is not None)
        assert len(set(ask_ids)) == 2 and all(ask_ids)                     # كل جولة رسالة جديدة، لا تعديل للأولى
        stripped = [c for c in h.session.calls if type(c).__name__ == "EditMessageReplyMarkup"
                    and c.chat_id == GROUP.id and c.message_id == first and c.reply_markup is None]
        assert stripped                                                    # أزرار الجولة الأولى أُزيلت
    run(go())
