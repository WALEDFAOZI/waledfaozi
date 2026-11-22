"""ألعاب المجموعات: غرفة انتظار، أسئلة بعدّاد، ردود على صاحب الأمر، هوية القناة/المجموعة، الصلاحيات."""
import asyncio
import datetime as dt
from pathlib import Path

import pytest
from aiogram.types import CallbackQuery, Chat, Message, MessageEntity, Update, User

from harness import Harness, run
from otaku_bot import group

GROUP = Chat(id=-1001, type="supergroup", title="شلة الأوتاكو")


@pytest.fixture(autouse=True)
def fast():
    old = (group.LOBBY_SECONDS, group.Q_SECONDS, group.PAUSE, group.CHAT_COOLDOWN, group.START_COOLDOWN,
           group.CH_LOBBY_SECONDS, group.CH_Q_SECONDS)
    (group.LOBBY_SECONDS, group.Q_SECONDS, group.PAUSE, group.CHAT_COOLDOWN, group.START_COOLDOWN,
     group.CH_LOBBY_SECONDS, group.CH_Q_SECONDS) = 0.5, 0.6, 0.02, 0, 0, 0.8, 1.2
    yield
    (group.LOBBY_SECONDS, group.Q_SECONDS, group.PAUSE, group.CHAT_COOLDOWN, group.START_COOLDOWN,
     group.CH_LOBBY_SECONDS, group.CH_Q_SECONDS) = old


def gmsg(user, text, mid=7, chat=GROUP, sender_chat=None, reply_to=None):
    ents = [MessageEntity(type="bot_command", offset=0, length=len(text.split()[0]))] if text.startswith("/") else None
    return Message(message_id=mid, date=dt.datetime.now(), chat=chat, from_user=user, text=text, entities=ents,
                   sender_chat=sender_chat, reply_to_message=reply_to)


async def gsay(h, user, text, mid=7, **kw):
    h.uid += 1
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, message=gmsg(user, text, mid, **kw)))


async def gtap(h, user, data, msg_id=500, reply_to=None):
    h.uid += 1
    m = Message(message_id=msg_id, date=dt.datetime.now(), chat=GROUP, text=".", reply_to_message=reply_to)
    cb = CallbackQuery(id=str(h.uid), from_user=user, chat_instance="g", data=data, message=m)
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, callback_query=cb))


def shown_text(c):
    """نص أي رسالة ظهرت في الجولة: نص، أو تعليق صورة، أو تعديل تعليق أو وسائط."""
    t = getattr(c, "text", None) or getattr(c, "caption", None)
    if not t and getattr(c, "media", None) is not None:
        t = getattr(c.media, "caption", None)
    return t or ""


def sent(h):
    return [c for c in h.session.calls if type(c).__name__ in ("SendMessage", "SendPhoto") and c.chat_id == GROUP.id]


def shows(h):
    """كل ما ظهر في المجموعة: رسائل جديدة + تعديلات الرسالة الحيّة."""
    return [c for c in h.session.calls if type(c).__name__ in ("SendMessage", "SendPhoto", "EditMessageText", "EditMessageCaption", "EditMessageMedia")
            and c.chat_id == GROUP.id]


def buttons(call):
    return [b.callback_data for row in call.reply_markup.inline_keyboard for b in row] if call.reply_markup else []


def last_with(h, prefix):
    for c in reversed(shows(h)):
        if any((d or "").startswith(prefix) for d in buttons(c)):
            return c
    return None


async def play_out(h, users, timeout=8.0):
    """يضغط (الخيار 0) لكل لاعب على كل سؤال جديد حتى تنتهي اللعبة."""
    done, t0 = set(), asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - t0 < timeout:
        if any("انتهت اللعبة" in (getattr(c, "text", None) or getattr(c, "caption", None) or "") for c in shows(h)):
            await asyncio.sleep(0.05)
            return True
        c = last_with(h, "gp:a:")
        if c is not None and id(c) not in done:
            done.add(id(c))
            data = [d for d in buttons(c) if d.startswith("gp:a:")][0]
            for u in users:
                await gtap(h, u, data)
        await asyncio.sleep(0.05)
    return False


def start_lobby(h, host, kind="quiz", mid=7, **kw):
    return gsay(h, host, f"/{kind}", mid, **kw)


def test_full_game_replies_to_command_and_saves_results():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await start_lobby(h, a, "quiz", mid=77)
        lobby = sent(h)[0]
        gid = buttons(lobby)[0].split(":")[2]
        assert "Ali" in lobby.text and lobby.reply_parameters.message_id == 77
        await gtap(h, a, f"gp:j:{gid}")
        await gtap(h, b, f"gp:j:{gid}")
        await gtap(h, b, f"gp:j:{gid}")                         # انضمام مكرر لا يضاعفه
        assert await play_out(h, [a, b]), "اللعبة لم تنتهِ"
        msgs = sent(h)
        assert len(msgs) == 1                                   # رسالة حيّة واحدة فقط: تُعدَّل ولا تتراكم
        edits = [c for c in h.session.calls if type(c).__name__ in ("EditMessageCaption", "EditMessageMedia") and c.chat_id == GROUP.id]
        assert len(edits) >= 20                                 # الأسئلة والعدّاد والكشف كلها تعديلات
        assert not any(type(c).__name__ == "DeleteMessage" for c in h.session.calls)   # لا تُحذف الحيّة في النهاية
        assert all(c.reply_parameters and c.reply_parameters.message_id == 77 for c in msgs)   # الرد على صاحب الأمر دائمًا
        final = [shown_text(c) for c in shows(h) if "انتهت اللعبة" in shown_text(c)][-1]
        assert "Ali" in final and "Bob" in final
        assert len(h.db.conn.execute("SELECT 1 FROM group_results WHERE chat_id=?", (GROUP.id,)).fetchall()) == 2
        await gsay(h, a, "/gtop", mid=80)
        assert "متصدرو المجموعة" in sent(h)[-1].text and sent(h)[-1].reply_parameters.message_id == 80
        assert h.db.get_user(1)["best_score"] == 0               # لا يمس التقييم الفردي
    run(go())


def test_too_few_players_busy_and_stop():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await start_lobby(h, a)
        await start_lobby(h, b, mid=9)                          # لعبة شغالة
        assert any("فيه لعبة شغالة" in (c.text or "") for c in shows(h))
        await asyncio.sleep(0.9)
        edits = [c for c in h.session.calls if type(c).__name__ in ("EditMessageText", "EditMessageCaption", "EditMessageMedia")]
        assert any("ما اكتمل العدد" in shown_text(e) for e in edits)
        # إيقاف: غير المضيف وغير الأدمن مرفوض، والمضيف مقبول
        await start_lobby(h, a, mid=11)
        await gsay(h, b, "/gstop", mid=12)
        assert any("لصاحب الأمر" in (c.text or "") for c in shows(h))
        await gsay(h, a, "/gstop", mid=13)
        await asyncio.sleep(0.1)
        assert any("تم إيقاف اللعبة" in (c.text or "") for c in shows(h))
        h.session.admins = {2}
        await start_lobby(h, a, mid=14)
        await gsay(h, b, "/gstop", mid=15)                      # أدمن المجموعة يقدر
        await asyncio.sleep(0.1)
        assert sum("تم إيقاف اللعبة" in (c.text or "") for c in shows(h)) == 2
    run(go())


def test_channel_and_anonymous_admin_are_registered_by_name():
    async def go():
        h = Harness()
        chan = Chat(id=-100777, type="channel", title="قناة الأنمي")
        ch_user = User(id=136817688, is_bot=True, first_name="Channel")
        await start_lobby(h, ch_user, mid=21, sender_chat=chan)
        assert "قناة الأنمي" in sent(h)[0].text and sent(h)[0].reply_parameters.message_id == 21
        await gsay(h, ch_user, "/gstop", mid=22, sender_chat=GROUP)       # مجموعة (أدمن مخفي) يقدر يوقف
        await asyncio.sleep(0.1)
        h2 = Harness()
        anon = User(id=1087968824, is_bot=True, first_name="Group")
        await start_lobby(h2, anon, mid=31, sender_chat=GROUP)
        assert "شلة الأوتاكو" in sent(h2)[0].text
    run(go())


def test_bot_admin_is_hidden_and_excluded_from_group_board():
    async def go():
        h = Harness()
        owner, b = h.user(9, "OwnerReal"), h.user(2, "Bob")
        h.db.upsert_user(9, "OwnerReal"); h.db.add_admin(9, owner=True)
        await start_lobby(h, b, mid=41)
        gid = buttons(sent(h)[0])[0].split(":")[2]
        await gtap(h, owner, f"gp:j:{gid}")
        await gtap(h, b, f"gp:j:{gid}")
        assert await play_out(h, [owner, b])
        everything = " ".join((c.text or "") for c in shows(h))
        assert "OwnerReal" not in everything and "مجهول" in everything
        assert [r["name"] for r in h.db.group_top(GROUP.id)] == ["Bob"]
    run(go())


def test_private_features_do_not_leak_into_groups_and_menu_flow():
    async def go():
        h = Harness(admin_ids=(9,))
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await gsay(h, a, "/start")
        assert any("/play" in (c.text or "") for c in sent(h)) and not any(type(c).__name__ == "SendPhoto" for c in sent(h))
        n = len(h.session.calls)
        await gsay(h, h.user(9, "Boss"), "/admin")
        await gsay(h, a, "/top")
        assert len(h.session.calls) == n                         # لا شيء من لوحة الأدمن/الخاص يظهر في المجموعة
        # قائمة الاختيار: أي عضو يقدر يختار نوع اللعبة ويبدأها
        cmd = gmsg(a, "/play", mid=51)
        await gsay(h, a, "/play", mid=51)
        menu = sent(h)[-1]
        assert menu.reply_parameters.message_id == 51 and "gp:n:quiz" in buttons(menu)
        await gtap(h, b, "gp:n:tf", reply_to=cmd)
        lobby = [c for c in sent(h) if "تبدأ بعد" in (c.text or "")][-1]
        assert "صح أم غلط" in lobby.text and lobby.reply_parameters.message_id == 51 and "Bob" in lobby.text
    run(go())


def test_subscription_required_to_join_and_toggle_off():
    async def go():
        h = Harness(channel="@Anime1Galaxy")
        h.session.member = True
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await start_lobby(h, a)
        gid = buttons(sent(h)[0])[0].split(":")[2]
        h.session.member = False
        before = len(sent(h))
        await gtap(h, b, f"gp:j:{gid}")
        assert len(sent(h)) == before                            # تنبيه فقط، لا رسالة في المجموعة
        h.session.member = True
        await gtap(h, b, f"gp:j:{gid}")
        await gsay(h, a, "/gstop", mid=8)
        await asyncio.sleep(0.1)
        h.db.set_setting("grp_enabled", "0")
        await asyncio.sleep(0.05)
        await start_lobby(h, a, mid=61)
        assert any("متوقفة" in (c.text or "") for c in sent(h))
    run(go())


def test_every_game_kind_builds_and_sudden_eliminates():
    async def go():
        for kind in ("quiz", "sudden", "tf", "song", "char", "quote", "order"):
            h = Harness()
            a, b = h.user(1, "Ali"), h.user(2, "Bob")
            await start_lobby(h, a, kind, mid=70)
            gid = buttons(sent(h)[0])[0].split(":")[2]
            await gtap(h, a, f"gp:j:{gid}")
            await gtap(h, b, f"gp:j:{gid}")
            assert await play_out(h, [a, b], timeout=12), kind
            assert all(c.reply_parameters.message_id == 70 for c in sent(h)), kind
    run(go())


def test_main_menu_group_button_and_start_play_in_group_and_group_ranking_button():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        await h.say(a, "/start")
        from harness import last_menu_call
        assert "gpm" in {x.callback_data for row in last_menu_call(h).reply_markup.inline_keyboard for x in row}
        await h.tap(a, "gpm")
        urls = [x.url for c in h.session.calls if getattr(c, "reply_markup", None) is not None
                for row in c.reply_markup.inline_keyboard for x in row if x.url]
        assert any("startgroup=play" in u for u in urls)
        # الإضافة من الزر ترسل /start play في المجموعة → تظهر قائمة الألعاب كردّ
        await gsay(h, a, "/start play", mid=90)
        menu = sent(h)[-1]
        assert menu.reply_parameters.message_id == 90 and "gp:n:quiz" in buttons(menu) and "gp:t" in buttons(menu)
        # نتائج سابقة + زر الترتيب
        h.db.upsert_user(1, "Ali"); h.db.upsert_user(2, "Bob")
        h.db.add_group_result(GROUP.id, 1, 900, "quiz", True)
        h.db.add_group_result(GROUP.id, 1, 700, "tf", True)
        h.db.add_group_result(GROUP.id, 2, 500, "quiz", False)
        n = len(sent(h))
        cmd = gmsg(a, "/play", mid=95)
        await gtap(h, b, "gp:t", reply_to=cmd)
        board = sent(h)[-1]
        assert len(sent(h)) == n + 1 and board.reply_parameters.message_id == 95
        assert "Ali" in board.text and "🏆2" in board.text and "🎮2" in board.text and "⭐1600" in board.text
        await gtap(h, b, "gp:t", reply_to=cmd)                    # ضغط سريع ثانٍ: نافذة منبثقة بلا رسالة جديدة
        assert len(sent(h)) == n + 1
    run(go())


def test_group_button_is_second_row_and_full_width():
    async def go():
        h = Harness()
        await h.say(h.user(1), "/start")
        from harness import last_menu_call
        rows = last_menu_call(h).reply_markup.inline_keyboard
        assert [b.callback_data for b in rows[0]] == ["go"] and [b.callback_data for b in rows[1]] == ["qk"] and [b.callback_data for b in rows[2]] == ["on:m", "dy:m"] and [b.callback_data for b in rows[3]] == ["gpm", "gpc"] and [b.callback_data for b in rows[4]] == ["du:new", "iv"]
    run(go())


# ───────────── مسابقات القنوات ─────────────
CHAN = Chat(id=-1002, type="channel", title="قناة الأنمي")


def chan_sent(h):
    return [c for c in h.session.calls if type(c).__name__ in ("SendMessage", "SendPhoto") and c.chat_id == CHAN.id]


def chan_final(h):
    """آخر رسالة في القناة تحمل نص النتيجة النهائية (رسالة جديدة أو تعديل)."""
    return [c for c in chan_shows(h) if "انتهت اللعبة" in shown_text(c)][-1]


def chan_shows(h):
    return [c for c in h.session.calls if type(c).__name__ in ("SendMessage", "SendPhoto", "EditMessageText", "EditMessageCaption", "EditMessageMedia")
            and c.chat_id == CHAN.id]


async def ctap(h, user, data, msg_id=600):
    h.uid += 1
    m = Message(message_id=msg_id, date=dt.datetime.now(), chat=CHAN, text=".")
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, callback_query=CallbackQuery(
        id=str(h.uid), from_user=user, chat_instance="c", data=data, message=m)))


async def bot_added_to_channel(h, user, rights=True):
    from aiogram.types import ChatMemberAdministrator, ChatMemberLeft, ChatMemberUpdated
    bot_u = User(id=999, is_bot=True, first_name="bot", username="otaku_test_bot")
    new = ChatMemberAdministrator(user=bot_u, can_be_edited=False, is_anonymous=False, can_manage_chat=True,
                                  can_delete_messages=True, can_manage_video_chats=False, can_restrict_members=False,
                                  can_promote_members=False, can_change_info=False, can_invite_users=True,
                                  can_post_stories=False, can_edit_stories=False, can_delete_stories=False, can_send_welcome_messages=False,
                                  can_post_messages=rights, can_edit_messages=rights)
    ev = ChatMemberUpdated(chat=CHAN, from_user=user, date=dt.datetime.now(), old_chat_member=ChatMemberLeft(user=bot_u),
                           new_chat_member=new)
    h.uid += 1
    await h.dp.feed_update(h.bot, Update(update_id=h.uid, my_chat_member=ev))


async def chan_play_out(h, users, timeout=10.0):
    done, t0 = set(), asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - t0 < timeout:
        if any("انتهت اللعبة" in shown_text(c) for c in chan_sent(h) + [c for c in h.session.calls if type(c).__name__ in ("EditMessageCaption", "EditMessageMedia") and c.chat_id == CHAN.id]):
            return True
        for c in reversed(chan_shows(h)):
            ds = [d for d in buttons(c) if (d or "").startswith("gp:a:")]
            if ds:
                if id(c) not in done:
                    done.add(id(c))
                    for u in users:
                        await ctap(h, u, ds[0])
                break
        await asyncio.sleep(0.05)
    return False


def test_channel_contest_flow_single_live_message_and_final_top():
    async def go():
        h = Harness(channel="@Anime1Galaxy")
        h.session.member = True
        owner = h.user(5, "Owner")
        h.db.upsert_user(5, "Owner")
        await bot_added_to_channel(h, owner)
        dm = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == 5]
        assert dm and f"ch:n:{CHAN.id}:quiz" in buttons(dm[-1]) and h.db.channel_owner(CHAN.id) == 5
        stranger = h.user(6, "Eve")
        await h.tap(stranger, f"ch:n:{CHAN.id}:quiz")             # غير مالك/أدمن: مرفوض
        assert not chan_sent(h)
        group.CH_LOBBY_SECONDS = 30                                 # مهلة طويلة؛ نبدأ يدويًا بعد انضمام الجميع (بلا اعتماد على سرعة الجهاز)
        await h.tap(owner, f"ch:n:{CHAN.id}:quiz")
        lobby = chan_sent(h)[0]
        assert buttons(lobby)[0].startswith("gp:j:") and buttons(lobby)[1].startswith("gp:u:") and len([d for d in buttons(lobby) if d]) == 2      # مشاركة + إلغاء مشاركتي (+ رابط الاشتراك)
        assert lobby.reply_parameters is None and "تبدأ بعد" in lobby.text
        assert [b.text for row in lobby.reply_markup.inline_keyboard for b in row] == ["✋ شارك", "↩️ إلغاء مشاركتي", "💬 قناتنا"]
        gid = buttons(lobby)[0].split(":")[2]
        players = [h.user(100 + i, f"P{i}") for i in range(300)]       # أعداد كبيرة
        for u in players:
            await ctap(h, u, f"gp:j:{gid}")
        await h.tap(owner, f"ch:s:{CHAN.id}")                       # ابدأ الآن من الخاص
        assert await chan_play_out(h, players, timeout=45), "المسابقة لم تنتهِ"
        assert len(chan_sent(h)) == 1                              # رسالة حيّة واحدة فقط: تُعدَّل إلى النتيجة النهائية
        assert not any(type(c).__name__ == "DeleteMessage" and c.chat_id == CHAN.id for c in h.session.calls)
        final = [shown_text(c) for c in chan_shows(h) if "انتهت اللعبة" in shown_text(c)][-1]
        assert "👥 300" in final and chan_sent(h)[0].reply_parameters is None
        rows = h.db.conn.execute("SELECT COUNT(*) n FROM group_results WHERE chat_id=?", (CHAN.id,)).fetchone()["n"]
        assert rows == group.CH_KEEP                               # أفضل 50 فقط في القاعدة
        assert h.db.conn.execute("SELECT COUNT(*) n FROM users WHERE tg_id>=100").fetchone()["n"] == group.CH_KEEP
        everything = " ".join((getattr(c, "text", None) or getattr(c, "caption", None) or "") for c in chan_shows(h))
        assert "Owner" not in everything and "المضيف" not in everything and "Host" not in everything   # لا معلومات عن المنظّم في القناة
        assert all(getattr(c, "reply_parameters", None) is None for c in chan_sent(h))
        assert h.db.conn.execute("SELECT COUNT(*) n FROM group_results WHERE tg_id=5").fetchone()["n"] == 0   # المنظّم ليس مشاركًا إلا إذا ضغط «شارك»
    run(go())


def test_channel_play_post_is_deleted_and_menu_goes_to_owner_and_menu_button():
    async def go():
        h = Harness()
        owner = h.user(5, "Owner")
        h.db.upsert_user(5, "Owner")
        h.db.link_channel(CHAN.id, 5, CHAN.title)
        h.uid += 1
        m = Message(message_id=33, date=dt.datetime.now(), chat=CHAN, text="/play",
                    entities=[MessageEntity(type="bot_command", offset=0, length=5)])
        await h.dp.feed_update(h.bot, Update(update_id=h.uid, channel_post=m))
        assert any(type(c).__name__ == "DeleteMessage" and c.chat_id == CHAN.id and c.message_id == 33 for c in h.session.calls)
        assert any(type(c).__name__ == "SendMessage" and c.chat_id == 5 and f"ch:n:{CHAN.id}:tf" in buttons(c)
                   for c in h.session.calls)
        # زر القائمة الرئيسية
        await h.say(owner, "/start")
        from harness import last_menu_call
        assert "gpc" in {x.callback_data for row in last_menu_call(h).reply_markup.inline_keyboard for x in row}
        await h.tap(owner, "gpc")
        urls = [x.url for c in h.session.calls if getattr(c, "reply_markup", None) is not None
                for row in c.reply_markup.inline_keyboard for x in row if x.url]
        assert any("startchannel=play" in u and "post_messages" in u for u in urls)
        assert any(f"ch:m:{CHAN.id}" in buttons(c) for c in h.session.calls if getattr(c, "reply_markup", None) is not None)
    run(go())


def test_channel_publish_failure_reason_test_button_and_dm_fallback():
    async def go():
        h = Harness()
        owner = h.user(5, "Owner")
        h.db.upsert_user(5, "Owner")
        h.db.link_channel(CHAN.id, 5, CHAN.title)
        # فشل النشر في القناة (لا صلاحية): سبب واضح في التنبيه ولا لعبة عالقة
        h.session.blocked_chats.add(CHAN.id)
        await h.tap(owner, f"ch:n:{CHAN.id}:quiz")
        ans = [c for c in h.session.calls if type(c).__name__ == "AnswerCallbackQuery" and getattr(c, "show_alert", False)]
        assert ans and "Forbidden" in (ans[-1].text or "")
        await h.tap(owner, f"ch:t:{CHAN.id}")
        ans = [c for c in h.session.calls if type(c).__name__ == "AnswerCallbackQuery" and getattr(c, "show_alert", False)]
        assert "Forbidden" in (ans[-1].text or "")
        h.session.blocked_chats.discard(CHAN.id)
        await h.tap(owner, f"ch:t:{CHAN.id}")                       # الآن ينجح ويحذف رسالة الاختبار
        ans = [c for c in h.session.calls if type(c).__name__ == "AnswerCallbackQuery" and getattr(c, "show_alert", False)]
        assert "ينشر ويحذف" in (ans[-1].text or "")
        assert any(type(c).__name__ == "DeleteMessage" and c.chat_id == CHAN.id for c in h.session.calls)
        await h.tap(owner, f"ch:n:{CHAN.id}:quiz")                  # وبعد الإصلاح تظهر رسالة المشاركة
        assert chan_sent(h) and "✋ شارك" in [b.text for row in chan_sent(h)[-1].reply_markup.inline_keyboard for b in row]
        # /play في القناة والمنظّم لا يستقبل الخاص: تنبيه مؤقت بالقناة بدل صمت
        h2 = Harness()
        h2.db.upsert_user(5, "Owner"); h2.db.link_channel(CHAN.id, 5, CHAN.title)
        h2.session.blocked_chats.add(5)
        h2.uid += 1
        m = Message(message_id=34, date=dt.datetime.now(), chat=CHAN, text="/play",
                    entities=[MessageEntity(type="bot_command", offset=0, length=5)])
        await h2.dp.feed_update(h2.bot, Update(update_id=h2.uid, channel_post=m))
        assert any("افتح البوت بالخاص" in (c.text or "") for c in chan_sent(h2))
    run(go())


def test_channel_contest_runs_with_a_single_participant_and_empty_lobby_message():
    async def go():
        h = Harness()
        owner, solo = h.user(5, "Owner"), h.user(7, "Solo")
        h.db.upsert_user(5, "Owner"); h.db.link_channel(CHAN.id, 5, CHAN.title)
        await h.tap(owner, f"ch:n:{CHAN.id}:tf")
        gid = buttons(chan_sent(h)[0])[0].split(":")[2]
        await ctap(h, solo, f"gp:j:{gid}")                          # مشارك واحد فقط: تبدأ المسابقة
        assert await chan_play_out(h, [solo], timeout=15)
        assert any("👥 1" in shown_text(c) for c in chan_shows(h))
        h2 = Harness()                                              # ولو لم يشارك أحد: رسالة واضحة
        h2.db.upsert_user(5, "Owner"); h2.db.link_channel(CHAN.id, 5, CHAN.title)
        await h2.tap(h2.user(5, "Owner"), f"ch:n:{CHAN.id}:tf")
        await asyncio.sleep(1.2)
        edits = [c for c in h2.session.calls if type(c).__name__ in ("EditMessageText", "EditMessageCaption", "EditMessageMedia") and c.chat_id == CHAN.id]
        assert any("ما شارك أحد" in shown_text(e) for e in edits)
    run(go())


def test_channel_contest_requires_subscription_and_shows_subscribe_button():
    async def go():
        h = Harness(channel="@Anime1Galaxy")
        h.session.member = True
        owner, a, b = h.user(5, "Owner"), h.user(10, "Ann"), h.user(11, "Bob")
        h.db.upsert_user(5, "Owner"); h.db.link_channel(CHAN.id, 5, CHAN.title)
        group.CH_LOBBY_SECONDS = 20
        await h.tap(owner, f"ch:n:{CHAN.id}:tf")
        gid = buttons(chan_sent(h)[0])[0].split(":")[2]

        def clear_cache():
            for cell in h.ctx.subscribed.__closure__:
                if isinstance(cell.cell_contents, dict):
                    cell.cell_contents.clear()
        h.session.member = False                                   # غير مشترك: لا يشارك
        await ctap(h, a, f"gp:j:{gid}")
        alerts = [c for c in h.session.calls if type(c).__name__ == "AnswerCallbackQuery" and getattr(c, "show_alert", False)]
        assert alerts and "تشترك في قناتنا @Anime1Galaxy" in (alerts[-1].text or "")
        clear_cache()
        h.session.member = True
        await ctap(h, a, f"gp:j:{gid}")
        await ctap(h, b, f"gp:j:{gid}")
        await h.tap(owner, f"ch:s:{CHAN.id}")
        # زر الاشتراك تحت الخيارات
        for _ in range(60):
            qc = [c for c in chan_shows(h) if any((d or "").startswith("gp:a:") for d in buttons(c))]
            if qc:
                break
            await asyncio.sleep(0.05)
        urls = [x.url for row in qc[-1].reply_markup.inline_keyboard for x in row if x.url]
        assert urls == ["https://t.me/Anime1Galaxy"]
        # أحدهما يغادر القناة أثناء المسابقة: لا يدخل النتيجة النهائية
        clear_cache()
        done = False
        t0 = asyncio.get_event_loop().time()
        answered = set()
        while asyncio.get_event_loop().time() - t0 < 20 and not done:
            if any("انتهت اللعبة" in shown_text(c) for c in chan_sent(h) + [c for c in h.session.calls if type(c).__name__ in ("EditMessageCaption", "EditMessageMedia") and c.chat_id == CHAN.id]):
                break
            for c in reversed(chan_shows(h)):
                ds = [d for d in buttons(c) if (d or "").startswith("gp:a:")]
                if ds:
                    if id(c) not in answered:
                        answered.add(id(c))
                        await ctap(h, a, ds[0]); await ctap(h, b, ds[0])
                    break
            await asyncio.sleep(0.05)
        final = chan_final(h)
        assert "انتهت اللعبة" in final.text
        assert [x.url for row in final.reply_markup.inline_keyboard for x in row if x.url] == [
            "https://t.me/otaku_test_bot?start=src_contest", "https://t.me/Anime1Galaxy"]
        # ... وعند الكشف تبقى أزرار الاشتراك
        reveals = [c for c in h.session.calls if type(c).__name__ in ("EditMessageText", "EditMessageCaption", "EditMessageMedia") and c.chat_id == CHAN.id and "الجواب" in shown_text(c)]
        assert reveals and all(any(x.url for row in c.reply_markup.inline_keyboard for x in row) for c in reveals)
    run(go())


def test_channel_final_excludes_player_who_left_our_channel():
    async def go():
        h = Harness(channel="@Anime1Galaxy")
        h.session.member = True
        owner, a = h.user(5, "Owner"), h.user(10, "Ann")
        h.db.upsert_user(5, "Owner"); h.db.link_channel(CHAN.id, 5, CHAN.title)
        group.CH_LOBBY_SECONDS = 20
        await h.tap(owner, f"ch:n:{CHAN.id}:tf")
        gid = buttons(chan_sent(h)[0])[0].split(":")[2]
        await ctap(h, a, f"gp:j:{gid}")
        await h.tap(owner, f"ch:s:{CHAN.id}")
        t0 = asyncio.get_event_loop().time()
        answered, left = set(), False
        while asyncio.get_event_loop().time() - t0 < 20:
            if any("انتهت اللعبة" in shown_text(c) for c in chan_sent(h) + [c for c in h.session.calls if type(c).__name__ in ("EditMessageCaption", "EditMessageMedia") and c.chat_id == CHAN.id]):
                break
            for c in reversed(chan_shows(h)):
                ds = [d for d in buttons(c) if (d or "").startswith("gp:a:")]
                if ds:
                    if id(c) not in answered:
                        answered.add(id(c))
                        await ctap(h, a, ds[0])
                        if len(answered) == 9 and not left:                # قبل آخر سؤال يغادر القناة
                            left = True
                            h.session.member = False
                            for cell in h.ctx.subscribed.__closure__:
                                if isinstance(cell.cell_contents, dict):
                                    cell.cell_contents.clear()
                    break
            await asyncio.sleep(0.05)
        final = chan_final(h)
        assert "انتهت اللعبة" in final.text and "Ann" not in final.text
        assert h.db.conn.execute("SELECT COUNT(*) n FROM group_results WHERE tg_id=10").fetchone()["n"] == 0
    run(go())


def test_leave_before_start_final_has_try_button_not_play_hint_in_channel_and_group():
    async def go():
        # القناة
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        owner, a, b = h.user(5, "Owner"), h.user(10, "Ann"), h.user(11, "Bob")
        h.db.upsert_user(5, "Owner"); h.db.link_channel(CHAN.id, 5, CHAN.title)
        group.CH_LOBBY_SECONDS = 20
        await h.tap(owner, f"ch:n:{CHAN.id}:tf")
        gid = buttons(chan_sent(h)[0])[0].split(":")[2]
        await ctap(h, a, f"gp:j:{gid}"); await ctap(h, b, f"gp:j:{gid}")
        await ctap(h, a, f"gp:u:{gid}")                                         # آن تنسحب قبل البدء
        await ctap(h, a, f"gp:u:{gid}")                                         # مرة ثانية: لا شيء
        lobby_edits = [c for c in h.session.calls if type(c).__name__ in ("EditMessageText", "EditMessageCaption", "EditMessageMedia") and c.chat_id == CHAN.id]
        await h.tap(owner, f"ch:s:{CHAN.id}")
        assert await chan_play_out(h, [a, b], timeout=20)
        final = chan_final(h)
        assert "/play" not in final.text and "لعبة جديدة" not in final.text           # حُذف السطر الأخير
        assert "Bob" in final.text and "Ann" not in final.text                        # آن لم تعد مشاركة
        btn_try = [x for row in final.reply_markup.inline_keyboard for x in row if x.url and "src_contest" in x.url]
        assert btn_try and "اختبار الأوتاكو" in btn_try[0].text and "👥 1" in final.text
        # بعد البدء لا يُسمح بالانسحاب
        await ctap(h, b, f"gp:u:{gid}")
        alerts = [c for c in h.session.calls if type(c).__name__ == "AnswerCallbackQuery" and getattr(c, "show_alert", False)]
        assert alerts
        # المجموعة بنفس الطريقة
        g2 = Harness()
        g2.db.fast_answer_ratio = lambda sid: 0.0
        x, y = g2.user(1, "Ali"), g2.user(2, "Bob")
        await start_lobby(g2, x, "tf", mid=70)
        gid2 = buttons(sent(g2)[0])[0].split(":")[2]
        assert any(d == f"gp:u:{gid2}" for d in buttons(sent(g2)[0]))
        await gtap(g2, x, f"gp:j:{gid2}"); await gtap(g2, y, f"gp:j:{gid2}")
        await gtap(g2, y, f"gp:u:{gid2}")                                          # بوب ينسحب
        await gtap(g2, y, f"gp:j:{gid2}")                                          # ثم يعود
        assert await play_out(g2, [x, y])
        fin = [c for c in shows(g2) if "انتهت اللعبة" in shown_text(c)][-1]
        assert "/play" not in fin.text and "Bob" in fin.text
        assert any(b2.url and "src_contest" in b2.url for row in fin.reply_markup.inline_keyboard for b2 in row)
        assert "gp:t" in buttons(fin)
        # قياس المصدر
        await g2.say(g2.user(77, "New"), "/start src_contest")
        assert g2.db.conn.execute("SELECT COUNT(*) n FROM events WHERE kind='src_contest'").fetchone()["n"] == 1
    run(go())


def test_lobby_is_three_minutes_and_countdown_actually_ticks():
    async def go():
        old = group.LOBBY_SECONDS
        group.LOBBY_SECONDS = 6
        try:
            h = Harness()
            await start_lobby(h, h.user(1, "Ali"), "tf", mid=80)
            await asyncio.sleep(4.5)
            edits = [shown_text(c) for c in h.session.calls if type(c).__name__ in ("EditMessageText", "EditMessageCaption", "EditMessageMedia") and c.chat_id == GROUP.id]
            nums = {int(x.split("تبدأ بعد <b>")[1].split("</b>")[0]) for x in edits if "تبدأ بعد" in x}
            assert len(nums) >= 2, nums                      # العدّاد يتغيّر بدل أن يبقى ثابتًا
        finally:
            group.LOBBY_SECONDS = old
    run(go())


def test_default_lobby_is_180_seconds():
    src = Path(group.__file__).read_text(encoding="utf-8")       # الاختبارات تخفّض القيمة، فنتحقق من الكود نفسه
    assert "LOBBY_SECONDS = 180" in src and "CH_LOBBY_SECONDS = 180" in src


def test_group_play_menu_lists_mafia_and_spy_first_and_buttons_start_them():
    async def go():
        from otaku_bot import mafia_game as MG, spy_game as SG
        h = Harness()
        host = h.user(1, "Ali")
        h.db.upsert_user(1, "Ali")
        h.uid += 1
        m = Message(message_id=900, date=dt.datetime.now(), chat=GROUP, text="/play",
                    from_user=host, entities=[MessageEntity(type="bot_command", offset=0, length=5)])
        await h.dp.feed_update(h.bot, Update(update_id=h.uid, message=m))
        menu = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == GROUP.id][-1]
        rows = menu.reply_markup.inline_keyboard
        assert [b.callback_data for b in rows[0]] == ["mf:new"] and [b.callback_data for b in rows[1]] == ["sp:new"]
        await gtap(h, host, "mf:new")
        assert GROUP.id in MG.games
        MG.games[GROUP.id].task.cancel()
        await asyncio.sleep(0.05)
        MG.games.clear()
        await gtap(h, host, "sp:new")
        assert GROUP.id in SG.games
        SG.games[GROUP.id].task.cancel()
        await asyncio.sleep(0.05)
        SG.games.clear()
    run(go())


def test_command_in_post_comments_replies_to_the_post_copy():
    """الأمر داخل تعليقات منشور: نرد على النسخة التلقائية للمنشور لتبقى رسائل البوت في تعليقات نفس المنشور."""
    async def go():
        h = Harness()
        a = h.user(1, "Ali")
        post_copy = Message(message_id=40, date=dt.datetime.now(), chat=GROUP, is_automatic_forward=True)
        await start_lobby(h, a, "quiz", mid=77, reply_to=post_copy)
        lobby = sent(h)[0]
        assert lobby.reply_parameters.message_id == 40
    run(go())


def test_comment_play_menu_lets_the_sender_pick_a_game():
    """/play داخل تعليقات منشور: صاحب الأمر يختار نوع اللعبة، ويصير هو المضيف لا القناة."""
    async def go():
        h = Harness()
        a = h.user(1, "Ali")
        post_copy = Message(message_id=40, date=dt.datetime.now(), chat=GROUP, is_automatic_forward=True)
        cmd = gmsg(a, "/play", mid=77, reply_to=post_copy)
        h.uid += 1
        await h.dp.feed_update(h.bot, Update(update_id=h.uid, message=cmd))
        menu = sent(h)[-1]
        assert "gp:n:quiz" in buttons(menu) and menu.reply_parameters.message_id == 40   # القائمة ترد على نسخة المنشور
        await gtap(h, a, "gp:n:quiz", msg_id=78, reply_to=post_copy)
        lobby = sent(h)[-1]
        assert "Ali" in lobby.text and "gp:j:" in buttons(lobby)[0] and lobby.reply_parameters.message_id == 40
    run(go())


def test_anyone_can_pick_a_game_from_the_menu():
    """أي عضو يقدر يختار نوع اللعبة من قائمة /play، ويصير هو المضيف."""
    async def go_one(key):
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        cmd = gmsg(a, "/play", mid=77)
        await gtap(h, b, key, msg_id=78, reply_to=cmd)
        assert sent(h), key
    run(go_one("mf:new"))
    run(go_one("sp:new"))
    run(go_one("gp:n:quiz"))


