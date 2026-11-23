"""فحص شامل للوحة الأدمن بسيناريوهات واقعية (ما يفعله المالك فعلًا بالأزرار)."""
from harness import Harness, run


def mk():
    h = Harness()
    h.db.add_admin(5, owner=True)
    return h, h.user(5, "Owner")


def texts(h):
    return "\n".join(h.session.texts())


def test_wizard_photo_without_caption_is_kept_then_text_asked():
    async def go():
        h, o = mk()
        await h.tap(o, "ad:add")
        await h.photo(o, "PIC1")                       # صورة بلا تعليق
        assert "أرسل نص السؤال" in h.session.texts()[-1]
        await h.say(o, "من هذه الشخصية؟")
        await h.say(o, "أ\nب\nج\nد")
        await h.tap(o, "ad:aa:2"); await h.tap(o, "ad:ad:4"); await h.tap(o, "ad:ac:images")
        await h.say(o, "Who is this?\nA\nB\nC\nD")           # إنجليزي
        q = [x for x in h.db.all_questions() if x.id >= 100000][0]
        assert q.image == "tg:PIC1" and q.answer == 2 and q.q_en == "Who is this?" and q.options_en == ["A", "B", "C", "D"]
    run(go())


def test_wizard_validation_errors_do_not_lose_progress():
    async def go():
        h, o = mk()
        await h.tap(o, "ad:add")
        await h.say(o, "سؤال")
        await h.say(o, "أ\nأ\nب\nج")                       # خيارات مكررة
        assert "4 خيارات مختلفة" in h.session.texts()[-1]
        await h.say(o, "أ\nب\nج")                           # 3 فقط
        assert "4 خيارات" in h.session.texts()[-1]
        await h.say(o, "أ\nب\nج\nد")                        # الآن صحيح -> ينتقل لاختيار الجواب
        assert "الجواب الصحيح" in h.session.texts()[-1]
        await h.tap(o, "ad:aa:0"); await h.tap(o, "ad:ad:1"); await h.tap(o, "ad:ac:anime")
        await h.say(o, "only two\nlines")                    # إنجليزي ناقص
        assert "5 أسطر" in h.session.texts()[-1]
        await h.tap(o, "ad:ae:skip")
        assert len([x for x in h.db.all_questions() if x.id >= 100000]) == 1
    run(go())


def test_pressing_other_buttons_clears_pending_input():
    async def go():
        h, o = mk()
        await h.tap(o, "ad:find")                      # ننتظر نصًا
        await h.tap(o, "ad:stats")                     # ضغط زر آخر: يلغي الانتظار
        before = len(h.session.calls)
        await h.say(o, "كلام عادي")                    # لا يجب أن يُعدَّ بحثًا
        assert len(h.session.calls) == before
        await h.tap(o, "ad:ch")
        await h.say(o, "/cancel")
        await h.say(o, "@Zzz")
        assert h.ctx.channel() != "@Zzz"
    run(go())


def test_find_edit_toggle_delete_roundtrip_and_buttons_all_work():
    async def go():
        h, o = mk()
        await h.tap(o, "ad:find")
        await h.say(o, "ناروتو")
        assert "النتائج" in h.session.texts()[-1]
        await h.tap(o, "ad:find")
        await h.say(o, "999999")                       # رقم غير موجود
        assert "غير موجود" in h.session.texts()[-1]
        await h.tap(o, "ad:q:1")
        assert "#1" in texts(h)
        for fld in ("q", "o", "i", "en"):
            await h.tap(o, f"ad:e:1:{fld}")
        await h.tap(o, "ad:e:1:a"); await h.tap(o, "ad:sa:1:2")
        await h.tap(o, "ad:e:1:d"); await h.tap(o, "ad:sd:1:9")
        await h.tap(o, "ad:e:1:c"); await h.tap(o, "ad:sc:1:music")
        q = h.db.get_question(1)
        assert q.answer == 2 and q.base_difficulty == 9 and q.category == "music"
        await h.tap(o, "ad:e:1:o")
        await h.say(o, "w\nx\ny\nz")
        assert h.db.get_question(1).options == ["w", "x", "y", "z"]
        await h.tap(o, "ad:e:1:en")
        await h.say(o, "حذف")
        assert h.db.get_question(1).q_en is None
        await h.tap(o, "ad:e:1:i")
        await h.say(o, "https://example.com/x.png")
        assert h.db.get_question(1).image == "https://example.com/x.png"
        await h.tap(o, "ad:e:1:i")
        await h.say(o, "حذف")
        assert h.db.get_question(1).image is None
    run(go())


def test_reports_review_dismiss_and_disable_close_reports():
    async def go():
        h, o = mk()
        db = h.db
        for uid in (11, 12, 13):
            db.upsert_user(uid, f"p{uid}")
            db.add_report(5, uid, "السؤال غامض أو فيه أكثر من جواب", 3)
        await h.tap(o, "ad:rep")
        assert "#5" in "\n".join(str(c.reply_markup) for c in h.session.calls if getattr(c, "reply_markup", None))
        await h.tap(o, "ad:rv:5")
        assert "أسباب البلاغات" in texts(h)
        await h.tap(o, "ad:dm:5")
        assert db.open_report_count(5) == 0
        db.add_report(6, 11, "x", 9); db.add_report(6, 12, "x", 9)
        await h.tap(o, "ad:t:6")                       # تعطيل السؤال يغلق بلاغاته
        assert db.open_report_count(6) == 0 and not db.get_question(6).active
        await h.tap(o, "ad:rep")
        assert "لا توجد بلاغات" in h.session.texts()[-1]
    run(go())


def test_settings_all_buttons_and_stats_with_data():
    async def go():
        h, o = mk()
        for cb, getter, val in [("ad:st:0", h.ctx.timer, 0), ("ad:st:60", h.ctx.timer, 60), ("ad:cd:0", h.ctx.cooldown, 0),
                                ("ad:cd:120", h.ctx.cooldown, 120), ("ad:rt:5", h.ctx.report_threshold, 5),
                                ("ad:rd:10", h.ctx.reports_per_day, 10)]:
            await h.tap(o, cb)
            assert getter() == val, cb
        await h.tap(o, "ad:set")
        # إحصائيات بعد نشاط حقيقي
        u = h.user(1, "P")
        await h.tap(u, "qk"); await h.play(u)
        await h.tap(o, "ad:stats")
        assert "إحصائيات البوت" in h.session.texts()[-1]
        await h.tap(o, "ad:sx:users")
        assert "الإجمالي: 1" in h.session.texts()[-1].replace("<b>", "").replace("</b>", "")
        await h.tap(o, "ad:img")
        await h.tap(o, "ad:adm")
        await h.tap(o, "ad:home")
    run(go())


def test_non_admin_cannot_use_any_admin_button():
    async def go():
        h, o = mk()
        h.db.set_setting("timer_seconds", "45")
        x = h.user(77, "X")
        for cb in ("ad:stats", "ad:add", "ad:set", "ad:adm", "ad:bak", "ad:img:go", "ad:t:1", "ad:x:100000", "ad:st:0", "ad:rm:5"):
            await h.tap(x, cb)
        assert not h.session.sent_to(77)
        assert h.db.is_owner(5) and h.ctx.timer() == 45
    run(go())
