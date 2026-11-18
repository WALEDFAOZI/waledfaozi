"""حماية التقدم: لا يضيع شيء حتى لو انمسح القرص."""
import re
import sqlite3
import time
import zipfile
from dataclasses import replace
from pathlib import Path

from harness import QPATH, Harness, run
from otaku_bot import backup
from otaku_bot.config import Settings
from otaku_bot.db import DB

ROOT = Path(__file__).resolve().parent.parent
CHAT = "-1001234567890"


def settings_for(path, chat=CHAT):
    return Settings(token="1:fake", db_path=str(path), questions_path=QPATH, timer_seconds=0, cooldown_minutes=0,
                    admin_ids=(), required_channel="", backup_chat=chat, backup_hours=6)


def seed_progress(h):
    """يصنع «تقدمًا» حقيقيًا: لاعبون ونتائج وسؤال أضافه الأدمن وإعدادات وبلاغ."""
    db = h.db
    for uid, name, best in ((1, "Sara", 9.1), (2, "Khalid", 7.4), (3, "Noor", 5.0)):
        db.upsert_user(uid, name)
        sid = db.create_session(uid, [(q, [0, 1, 2, 3], q.answer) for q in db.all_questions()[:50]])
        db.finish_session(sid, uid, best)
        db.set_country(uid, "SA")
    db.set_best_sudden(1, 17)
    qid = db.add_question("سؤال أضافه المالك؟", ["a", "b", "c", "d"], 2, "anime", 4, q_en="Owner question?", options_en=["a", "b", "c", "d"])
    db.set_setting("timer_seconds", "45")
    db.add_report(qid, 2, "x", 10)
    return qid


def test_chat_backup_is_sent_silently_and_pinned():
    async def go():
        h = Harness(backup_chat=CHAT)
        h.db.add_admin(5, owner=True)
        seed_progress(h)
        assert backup.chat_due(h.ctx)
        ok, msg = await backup.send_chat_backup(h.bot, h.ctx)
        assert ok and "الإرسال والتثبيت" in msg
        sent = [c for c in h.session.calls if type(c).__name__ == "SendDocument" and str(c.chat_id) == CHAT]
        pins = [c for c in h.session.calls if type(c).__name__ == "PinChatMessage"]
        assert len(sent) == 1 and sent[0].disable_notification is True       # بلا إزعاج للمالك
        assert len(pins) == 1 and pins[0].disable_notification is True
        assert h.session.pinned is not None and h.session.pinned.document.file_id in h.session.files
        assert not backup.chat_due(h.ctx, time.time() + 5 * 3600) and backup.chat_due(h.ctx, time.time() + 6 * 3600 + 5)
        assert "✅ مضبوطة" in backup.chat_status_text(h.ctx)
        # التثبيت آخر نسخة: نسخة ثانية تستبدل المثبّتة
        first = h.session.pinned.message_id
        await backup.send_chat_backup(h.bot, h.ctx)
        assert h.session.pinned.message_id != first
    run(go())


def test_wiped_disk_restores_everything_automatically(tmp_path):
    async def go():
        h = Harness(backup_chat=CHAT)
        h.db.add_admin(5, owner=True)
        qid = seed_progress(h)
        await backup.send_chat_backup(h.bot, h.ctx)
        # «سيرفر جديد»: لا قاعدة إطلاقًا
        new_path = tmp_path / "fresh" / "otaku.db"
        status = await backup.restore_if_empty(h.bot, settings_for(new_path))
        assert status == "restored"
        db = DB(str(new_path))
        assert [(u["name"], u["best_score"]) for u in db.leaderboard(10)] == [("Sara", 9.1), ("Khalid", 7.4), ("Noor", 5.0)]
        assert db.get_user(1)["best_sudden"] == 17 and db.get_country(1) == "SA"
        assert db.get_question(qid).q == "سؤال أضافه المالك؟" and db.is_owner(5)
        assert db.get_setting("timer_seconds") == "45" and db.open_report_count(qid) == 1
        assert db.user_rank(2) == 2 and db.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        # قاعدة فارغة (0 لاعبين) موجودة: تُستبدل أيضًا
        empty = tmp_path / "empty.db"
        DB(str(empty)).conn.close()
        assert await backup.restore_if_empty(h.bot, settings_for(empty)) == "restored"
        assert DB(str(empty)).get_user(1)["name"] == "Sara"
        # ملف تالف: يُحفظ جانبًا ثم تُستعاد النسخة
        bad = tmp_path / "bad.db"
        bad.write_bytes(b"this is not sqlite at all" * 100)
        assert await backup.restore_if_empty(h.bot, settings_for(bad)) == "restored"
        assert list(tmp_path.glob("bad.db.corrupt-*")) and DB(str(bad)).get_user(2)["name"] == "Khalid"
    run(go())


def test_restore_never_overwrites_a_database_that_has_players(tmp_path):
    async def go():
        h = Harness(backup_chat=CHAT)
        seed_progress(h)
        await backup.send_chat_backup(h.bot, h.ctx)                         # نسخة فيها 3 لاعبين
        live = tmp_path / "live.db"
        db = DB(str(live))
        db.upsert_user(99, "NewerPlayer")
        db.conn.commit()
        db.conn.close()
        assert await backup.restore_if_empty(h.bot, settings_for(live)) == "kept"
        assert DB(str(live)).get_user(99)["name"] == "NewerPlayer" and DB(str(live)).get_user(1) is None
    run(go())


def test_restore_failure_modes_never_crash_and_start_fresh(tmp_path):
    async def go():
        h = Harness(backup_chat=CHAT)
        seed_progress(h)
        await backup.send_chat_backup(h.bot, h.ctx)
        good = h.session.pinned
        p = lambda n: tmp_path / n / "otaku.db"   # noqa: E731
        assert await backup.restore_if_empty(h.bot, settings_for(p("a"), chat="")) == "no-backup-chat"
        h.session.chat_error = True
        assert await backup.restore_if_empty(h.bot, settings_for(p("b"))) == "chat-unreachable"
        h.session.chat_error = False
        h.session.pinned = None
        assert await backup.restore_if_empty(h.bot, settings_for(p("c"))) == "no-pinned-backup"
        # مثبّتة لكن ليست ملفًا
        # ملف فاسد (ليس zip)
        fid = good.document.file_id
        h.session.pinned = good
        original = h.session.files[fid]
        h.session.files[fid] = b"garbage"
        assert await backup.restore_if_empty(h.bot, settings_for(p("d"))) == "bad-zip"
        # zip فيه قاعدة تالفة
        import io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("otaku.db", b"not a database")
        h.session.files[fid] = buf.getvalue()
        assert await backup.restore_if_empty(h.bot, settings_for(p("e"))) == "bad-db"
        # zip بلا ملف القاعدة
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("other.txt", b"x")
        h.session.files[fid] = buf.getvalue()
        assert await backup.restore_if_empty(h.bot, settings_for(p("f"))) == "bad-zip"
        # بعد الفشل: لا قاعدة نصف مستعادة تُترك
        assert not p("e").exists() and not p("f").exists()
        # وبعد إصلاح الملف تنجح الاستعادة
        h.session.files[fid] = original
        assert await backup.restore_if_empty(h.bot, settings_for(p("g"))) == "restored"
    run(go())


def test_pin_or_send_failures_are_reported_and_do_not_crash():
    async def go():
        h = Harness(backup_chat=CHAT)
        seed_progress(h)
        h.session.pin_error = True
        ok, msg = await backup.send_chat_backup(h.bot, h.ctx)
        assert ok and "التثبيت فشل" in msg and "تثبيت" in h.db.get_setting("chat_backup_error")
        assert "⚠️" in backup.chat_status_text(h.ctx)
        h.session.pin_error = False
        h.session.blocked_chats = {int(CHAT)}
        ok, msg = await backup.send_chat_backup(h.bot, h.ctx)
        assert not ok and "تعذّر الإرسال" in msg
        h.session.blocked_chats = set()
        assert (await backup.send_chat_backup(h.bot, h.ctx))[0]
        assert h.db.get_setting("chat_backup_error") == ""
        h2 = Harness()                                                     # بلا BACKUP_CHAT_ID
        assert (await backup.send_chat_backup(h2.bot, h2.ctx))[0] is False and not backup.chat_due(h2.ctx)
        assert "❌ غير مضبوطة" in backup.chat_status_text(h2.ctx)
    run(go())


def test_admin_can_trigger_chat_backup_and_sees_status():
    async def go():
        h = Harness(backup_chat=CHAT, admin_ids=(5,))
        o = h.user(5)
        await h.tap(o, "ad:set")
        assert "قناة النسخ الاحتياطي" in h.session.texts()[-1]
        await h.tap(o, "ad:cb")
        assert h.session.pinned is not None and "✅" in h.session.texts()[-1]
        await h.tap(h.user(77), "ad:cb")                                    # غير المشرف: لا شيء
        assert sum(1 for c in h.session.calls if type(c).__name__ == "SendDocument") == 1
    run(go())


def test_chatid_command_in_group_and_channel():
    async def go():
        import datetime as dt
        from aiogram.types import Chat, Message, MessageEntity, Update
        h = Harness()
        await h.say(h.user(1), "/chatid")
        assert "chat id:" in h.session.texts()[-1]
        h.uid += 1
        post = Message(message_id=1, date=dt.datetime.now(), chat=Chat(id=-1001234567890, type="channel", title="B"),
                       text="/chatid", entities=[MessageEntity(type="bot_command", offset=0, length=7)])
        await h.dp.feed_update(h.bot, Update(update_id=h.uid, channel_post=post))
        assert "-1001234567890" in h.session.texts()[-1]
    run(go())


def test_database_survives_restarts_upgrades_and_question_reloads(tmp_path):
    path = tmp_path / "otaku.db"
    db = DB(str(path))
    db.load_questions(QPATH)
    db.upsert_user(1, "Sara")
    sid = db.create_session(1, [(q, [0, 1, 2, 3], q.answer) for q in db.all_questions()[:50]])
    db.finish_session(sid, 1, 8.8)
    db.add_admin(5, owner=True)
    db.conn.commit()
    db.conn.close()
    for _ in range(3):                                                     # إعادة تشغيل + إعادة تحميل الأسئلة + ترقية
        again = DB(str(path))
        again.load_questions(QPATH)
        assert again.get_user(1)["best_score"] == 8.8 and again.is_owner(5)
        assert again.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
        again.conn.close()


def test_no_code_path_deletes_players_or_their_progress():
    """حارس ثابت: لا يوجد في الكود أي أمر يحذف اللاعبين أو نتائجهم أو يُسقط جداول."""
    banned = [r"DELETE\s+FROM\s+users", r"DELETE\s+FROM\s+sessions", r"DELETE\s+FROM\s+session_questions",
              r"DELETE\s+FROM\s+game_scores", r"DELETE\s+FROM\s+user_seen", r"DROP\s+TABLE", r"TRUNCATE",
              r"UPDATE\s+users\s+SET\s+best_score\s*=\s*0"]
    for f in (ROOT / "otaku_bot").glob("*.py"):
        src = f.read_text(encoding="utf-8")
        for pat in banned:
            assert not re.search(pat, src, re.I), f"{f.name}: {pat}"
    # الحذف الوحيد المسموح: أسئلة أضافها المالك/المقترحة، وصلاحيات مشرف، وليس بيانات اللاعبين
    allowed = {"DELETE FROM questions", "DELETE FROM admins"}
    found = set()
    for f in (ROOT / "otaku_bot").glob("*.py"):
        found |= {m.group(0).upper().replace("  ", " ") for m in re.finditer(r"DELETE\s+FROM\s+\w+", f.read_text(encoding="utf-8"), re.I)}
    assert {x.replace("\n", " ") for x in found} <= {a.upper() for a in allowed}


def test_wipe_guard_env_and_docs_mention_backup_chat():
    assert "BACKUP_CHAT_ID" in (ROOT / ".env.example").read_text(encoding="utf-8")
    s = Settings.from_env()
    assert s.backup_hours >= 1
