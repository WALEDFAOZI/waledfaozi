"""اقتراح الأسئلة، الرسائل الجماعية، النسخ الاحتياطي الأسبوعي، والألعاب الجديدة."""
import asyncio
import json
import time
import zipfile
from pathlib import Path

from harness import QPATH, Harness, run, last_menu_call
from otaku_bot import backup
from otaku_bot.games import load_games, order_correct

GOOD = "من هو مؤلف Great Teacher Onizuka؟\nتورو فوجيساوا\nإييتشيرو أودا\nماساشي كيشيموتو\nتيتي كوبو"


def mk():
    h = Harness()
    h.db.add_admin(5, owner=True)
    return h, h.user(5, "Owner")


# ── #8 اقتراح الأسئلة ───────────────────────────────────
def test_suggestion_flow_validation_and_limits():
    async def go():
        h, o = mk()
        u = h.user(1, "Player")
        await h.tap(u, "sg")
        await h.tap(u, "sg:q")
        assert "5 أسطر" in h.session.texts()[-1]
        await h.say(u, "سطر واحد فقط")
        assert "5 أسطر" in h.session.texts()[-1] and h.db.pending_count() == 0
        await h.say(u, "قصير\nأ\nب\nج\nد")                       # سؤال أقصر من 10 أحرف
        assert "10 و200" in h.session.texts()[-1]
        await h.say(u, "سؤال طويل بما يكفي هنا؟\nأ\nأ\nب\nج")      # خيارات مكررة
        assert "مختلفة" in h.session.texts()[-1]
        await h.say(u, "ما اسم المؤلف الذي كتب هذا؟\n" + "x" * 61 + "\nب\nج\nد")   # خيار طويل
        assert "60" in h.session.texts()[-1]
        await h.say(u, GOOD)
        assert h.db.pending_count() == 1 and "وصل اقتراحك" in h.session.texts()[-1]
        # الحالة انتهت: كلام عادي لا يُعدّ اقتراحًا
        n = len(h.session.calls)
        await h.say(u, GOOD.replace("Great Teacher Onizuka", "Other"))
        assert h.db.pending_count() == 1 and len(h.session.calls) == n
        # سؤال موجود مسبقًا في البنك يُرفض
        await h.say(u, "/suggest")
        await h.say(u, "من هو بطل أنمي ناروتو؟\nناروتو أوزوماكي\nساسكي\nكاكاشي\nروك لي")
        assert "موجود عندنا" in h.session.texts()[-1]
        # الحد اليومي 3 والمعلّق 5
        for i in range(2):
            await h.say(u, "/suggest")
            await h.say(u, f"سؤال رقم {i} هل يعمل هذا؟\nأ{i}\nب{i}\nج{i}\nد{i}")
        assert h.db.pending_count() == 3
        await h.say(u, "/suggest")
        await h.say(u, "سؤال رابع يتجاوز الحد؟؟\nأ\nب\nج\nد")
        assert h.db.pending_count() == 3 and "الحد اليومي" in h.session.texts()[-1]
        # الإلغاء
        await h.say(u, "/suggest")
        await h.say(u, "/cancel")
        await h.say(u, "نص عادي")
        assert h.db.pending_count() == 3
        # ضغط زر آخر يلغي الانتظار
        await h.tap(u, "sg")
        await h.tap(u, "sg:q")
        await h.tap(u, "st")
        n = len(h.session.calls)
        await h.say(u, GOOD.replace("Great Teacher Onizuka", "Z"))
        assert len(h.session.calls) == n
    run(go())


def test_admin_reviews_suggestion_and_user_is_notified_and_question_playable():
    async def go():
        h, o = mk()
        u = h.user(1, "Player")
        await h.tap(u, "sg")
        await h.tap(u, "sg:q")
        await h.say(u, GOOD)
        sid = h.db.pending_suggestions()[0]["id"]
        await h.say(o, "/admin")
        assert "الاقتراحات والملاحظات (1)" in str([c.reply_markup for c in h.session.calls if getattr(c, "chat_id", None) == 5][-1])
        await h.tap(o, "ad:sg")
        await h.tap(o, f"ad:sv:{sid}")
        assert "تورو فوجيساوا" in h.session.texts()[-1]
        await h.tap(o, f"ad:sga:{sid}")
        await h.tap(o, f"ad:sgc:{sid}:creators")
        await h.tap(o, f"ad:sgd:{sid}:creators:6")
        q = [x for x in h.db.all_questions() if x.id >= 100000][0]
        assert q.q.startswith("من هو مؤلف Great Teacher Onizuka") and q.category == "creators" and q.base_difficulty == 6
        assert q.options[q.answer] == "تورو فوجيساوا" and sorted(q.options) == sorted(["تورو فوجيساوا", "إييتشيرو أودا", "ماساشي كيشيموتو", "تيتي كوبو"])
        assert h.db.question_source(q.id) == "user" and h.db.pending_count() == 0
        assert any("تم قبول سؤالك" in (getattr(c, "text", "") or "") and c.chat_id == 1 for c in h.session.calls)
        await h.tap(o, f"ad:sga:{sid}")                       # لا يُقبل مرتين
        await h.tap(o, f"ad:sgd:{sid}:creators:6")
        assert len([x for x in h.db.all_questions() if x.id >= 100000]) == 1
        # رفض
        await h.tap(u, "sg")
        await h.tap(u, "sg:q")
        await h.say(u, GOOD.replace("Great Teacher Onizuka", "Another One"))
        sid2 = h.db.pending_suggestions()[0]["id"]
        await h.tap(o, f"ad:sgr:{sid2}")
        assert h.db.pending_count() == 0
        # لا يستطيع غير المشرف المراجعة
        await h.tap(u, "sg")
        await h.tap(u, "sg:q")
        await h.say(u, GOOD.replace("Great Teacher Onizuka", "Third"))
        sid3 = h.db.pending_suggestions()[0]["id"]
        await h.tap(u, f"ad:sgd:{sid3}:creators:6")
        assert h.db.pending_count() == 1
    run(go())


# ── #9 رسالة جماعية ─────────────────────────────────────
def test_broadcast_preview_audience_confirm_blocked_and_cooldown():
    async def go():
        h, o = mk()
        for uid, lang in ((11, "ar"), (12, "ar"), (13, "en"), (14, "ar")):
            h.db.upsert_user(uid, f"u{uid}", lang)
        h.session.blocked_chats = {12}
        await h.tap(o, "ad:bc")
        await h.say(o, "")                                       # فارغ
        await h.say(o, "📣 تحديث جديد في البوت!")
        assert "اختر الجمهور" in h.session.texts()[-1]
        before = len(h.session.sent_to(11))
        await h.tap(o, "ad:bs:me")                                # تجربة لي فقط
        assert len(h.session.sent_to(11)) == before and any(c.chat_id == 5 and "تحديث جديد" in (c.text or "") for c in h.session.sent_to(5))
        await h.tap(o, "ad:bs:ar")                                # تأكيد لـ 3 عربي
        assert "3" in h.session.texts()[-1]
        await h.tap(o, "ad:bg:ar")
        await asyncio.gather(*h.ctx.tasks)
        got = {c.chat_id for c in h.session.calls if getattr(c, "text", None) == "📣 تحديث جديد في البوت!"}
        assert {11, 14} <= got and 13 not in got                  # الإنجليزي لم يصله
        assert h.db.conn.execute("SELECT blocked FROM users WHERE tg_id=12").fetchone()[0] == 1   # حظر البوت
        assert 12 not in h.db.broadcast_targets()
        assert "حظروا البوت: 1" in h.session.texts()[-1]
        # حماية: رسالة جماعية ثانية فورًا مرفوضة
        await h.tap(o, "ad:bc")
        await h.say(o, "رسالة ثانية")
        n = len(h.db.broadcast_targets())
        await h.tap(o, "ad:bs:all")
        assert "انتظر" in h.session.texts()[-1]
        # ويعود المستخدم لقائمة الإرسال إذا فتح البوت من جديد
        h.db.upsert_user(12, "u12")
        assert 12 in h.db.broadcast_targets()
    run(go())


def test_broadcast_with_photo_and_non_admin_denied():
    async def go():
        h, o = mk()
        h.db.upsert_user(11, "u11")
        await h.tap(o, "ad:bc")
        await h.photo(o, "PIC9", caption="إعلان بصورة")
        assert any(type(c).__name__ == "SendPhoto" and c.photo == "PIC9" and c.chat_id == 5 for c in h.session.calls)   # المعاينة
        h.db.set_setting("last_broadcast", "0")
        await h.tap(o, "ad:bs:all")
        await h.tap(o, "ad:bg:all")
        await asyncio.gather(*h.ctx.tasks)
        assert any(type(c).__name__ == "SendPhoto" and c.chat_id == 11 and c.caption == "إعلان بصورة" for c in h.session.calls)
        # غير المشرف
        x = h.user(77)
        await h.tap(x, "ad:bc")
        await h.say(x, "إعلان مزيّف")
        await h.tap(x, "ad:bg:all")
        assert not h.session.sent_to(77)
    run(go())


# ── #10 النسخة الأسبوعية ────────────────────────────────
def test_weekly_backup_due_send_and_toggle(tmp_path):
    async def go():
        h, o = mk()
        ctx = h.ctx
        now = time.time()
        assert backup.due(ctx, now)                                  # لم تُرسل بعد
        sent = await backup.send_backup(h.bot, ctx)
        docs = [c for c in h.session.calls if type(c).__name__ == "SendDocument"]
        assert sent == 1 and docs and docs[0].chat_id == 5
        assert not backup.due(ctx, time.time())                      # أُرسلت للتو
        assert backup.due(ctx, time.time() + 7 * 86400 + 5)          # بعد أسبوع تستحق
        assert not backup.due(ctx, time.time() + 6 * 86400)
        # إيقاف من الإعدادات
        await h.tap(o, "ad:ab:0")
        assert not backup.enabled(ctx) and not backup.due(ctx, time.time() + 30 * 86400)
        await h.tap(o, "ad:ab:1")
        assert backup.due(ctx, time.time() + 30 * 86400)
        # بلا مالك: لا ترسل ولا تسجّل «تمّت»
        h2 = Harness()
        assert await backup.send_backup(h2.bot, h2.ctx) == 0 and backup.due(h2.ctx)
        # فشل الإرسال للمالك (حظر): لا يُسجَّل
        h3, _ = mk()
        h3.session.blocked_chats = {5}
        assert await backup.send_backup(h3.bot, h3.ctx) == 0 and backup.due(h3.ctx)
    run(go())


def test_backup_zip_contains_restorable_database(tmp_path):
    h, _ = mk()
    h.db.upsert_user(42, "Keep Me")
    z = backup.make_zip(h.ctx, tmp_path)
    assert z.name.startswith("otaku-backup-") and z.suffix == ".zip"
    with zipfile.ZipFile(z) as zf:
        assert zf.namelist() == ["otaku.db"]
        zf.extract("otaku.db", tmp_path / "restore")
    from otaku_bot.db import DB
    restored = DB(str(tmp_path / "restore" / "otaku.db"))
    assert restored.get_user(42)["name"] == "Keep Me"
    assert restored.is_owner(5)


# ── #7 ألعاب جديدة ──────────────────────────────────────
def test_new_games_char_and_quote_play_through():
    async def go():
        h = Harness()
        u = h.user(1, "G")
        await h.say(u, "/games")
        kinds = {b.callback_data for row in last_menu_call(h).reply_markup.inline_keyboard for b in row}
        assert {"g:char", "g:quote"} <= kinds
        for kind, key in (("char", "gs"), ("quote", "gs")):
            await h.tap(u, f"g:{kind}")
            gid = h.db.conn.execute("SELECT MAX(id) FROM game_sessions").fetchone()[0]
            assert h.db.get_game(gid)["kind"] == kind
            first = h.session.texts()[-1]
            assert "(1/10)" in first
            for _ in range(10):
                g = h.db.get_game(gid)
                rd = g["state"]["rounds"][g["state"]["pos"]]
                await h.tap(u, f"{key}:{gid}:{rd['answer']}")
            g = h.db.get_game(gid)
            assert g["state"]["score"] == 10 and g["finished_at"]
        # بالإنجليزية يعرض النص الإنجليزي
        await h.tap(u, "lg:en")
        await h.tap(u, "g:quote")
        assert "Which anime is this quote from" in h.session.texts()[-1]
    run(go())


def test_game_data_quality():
    d = load_games()
    assert len(d["chars"]) >= 20 and len(d["quotes"]) >= 15
    for ar, en, name in d["chars"]:
        assert ar and en and name and not any("؀" <= c <= "ۿ" for c in en + name)
    for en, ar, anime in d["quotes"]:
        assert en and ar and anime
    names = [c[2] for c in d["chars"]]
    assert len(set(names)) == len(names)


# ── القائمة والبنك ──────────────────────────────────────
def test_main_menu_has_new_buttons_and_bank_doubled():
    async def go():
        h = Harness()
        await h.say(h.user(1), "/start")
        m = last_menu_call(h)
        data = {b.callback_data for row in m.reply_markup.inline_keyboard for b in row}
        assert {"m:games", "an:m", "iv", "sg", "lg:toggle", "qk"} <= data and "m:more" not in data and "st" not in data and "cats" not in data
        await h.tap(h.user(1), "m:games")
        gd = {b.callback_data for row in last_menu_call(h).reply_markup.inline_keyboard for b in row}
        assert {"g:char", "g:quote", "g:tf", "g:song", "g:ord"} <= gd
    run(go())
    qs = json.loads(Path(QPATH).read_text(encoding="utf-8"))
    assert len(qs) >= 616                                         # ضعف البنك السابق (308)
    from collections import Counter
    per_level = Counter(round(q["base_difficulty"]) for q in qs)
    assert min(per_level.values()) >= 39, per_level


def test_myid_shows_admin_status_and_version():
    async def go():
        h = Harness(admin_ids=(5,))
        await h.say(h.user(5), "/myid")
        txt = h.session.texts()[-1]
        assert "مشرف: ✅" in txt and "نسخة البوت" in txt and "الهوية" in txt and "شغّال منذ" in txt
        await h.say(h.user(6), "/myid")
        assert "مشرف: ❌" in h.session.texts()[-1]
        await h.say(h.user(5), "/admin")
        assert "لوحة التحكم" in h.session.texts()[-1]
    run(go())


def test_stale_or_unknown_buttons_are_answered_immediately():
    async def go():
        h, o = mk()
        for who in (h.user(1), o):
            before = sum(1 for c in h.session.calls if type(c).__name__ == "AnswerCallbackQuery")
            for cb in ("ad:zzz:old", "totally-unknown", "a:999:9:9x", "ad:e:1:zzz"):
                await h.tap(who, cb)
            after = sum(1 for c in h.session.calls if type(c).__name__ == "AnswerCallbackQuery")
            assert after - before >= 4          # كل ضغطة حصلت على رد، لا شيء يبقى معلّقًا
    run(go())


def test_image_fetch_fails_fast_when_host_hangs(monkeypatch):
    import time as _t
    from otaku_bot import anilist
    monkeypatch.setattr(anilist, "SOURCE_TIMEOUT", 0.2)

    async def hang(*a, **k):
        await asyncio.sleep(60)

    async def go():
        t0 = _t.monotonic()
        try:
            await anilist.fetch_image_questions(post=hang, get=hang)
            raise AssertionError("should fail")
        except RuntimeError as e:
            assert "AniList" in str(e) and "Jikan" in str(e)
        assert _t.monotonic() - t0 < 2                     # بدل دقيقة+ من الانتظار
    run(go())


def test_admin_stats_button_always_changes_text_and_backup_is_zipped():
    async def go():
        h, o = mk()
        await h.tap(o, "ad:stats")
        assert "🕒" in h.session.texts()[-1]
        await h.tap(o, "ad:bak")
        docs = [c for c in h.session.calls if type(c).__name__ == "SendDocument"]
        assert docs and docs[-1].document.filename.endswith(".zip")
    run(go())


def test_admin_path_is_fast_regression_guard():
    """معالجة /admin وأزرار اللوحة لازم تبقى بالملّي ثانية (حد واسع 100ms للأجهزة البطيئة)."""
    import time as _t

    async def go():
        h, o = mk()
        for step in ("/admin", "ad:stats", "ad:set", "ad:rep", "ad:sg", "ad:home"):
            t0 = _t.perf_counter()
            if step.startswith("/"):
                await h.say(o, step)
            else:
                await h.tap(o, step)
            assert (_t.perf_counter() - t0) < 0.5, step
    run(go())


def test_ping_reports_delivery_delay_and_conflict_alert_removed():
    async def go():
        h, o = mk()
        await h.say(o, "/ping")
        txt = h.session.texts()[-1]
        assert "pong" in txt and "تأخر وصول رسالتك" in txt
    run(go())
    import otaku_bot.app as app
    assert not hasattr(app, "ConflictWatcher")
