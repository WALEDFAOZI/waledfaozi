"""النمو: الوضع المضمن، ومشاركة كل نتيجة، ومكافأة من دخل بدعوة."""
import asyncio
import datetime as dt

from aiogram.types import InlineQuery, Update, User

from harness import Harness


def _inline(uid, name="Ali", query=""):
    u = User(id=uid, is_bot=False, first_name=name)
    return InlineQuery(id=f"iq{uid}", from_user=u, query=query, offset="", chat_type="sender")


def test_inline_mode_offers_a_challenge_for_anyone_and_a_result_when_played():
    async def go():
        h = Harness()
        h.db.upsert_user(31, "Ali")
        await h.dp.feed_update(h.bot, Update(update_id=901, inline_query=_inline(31)))
        answers = [c for c in h.session.calls if type(c).__name__ == "AnswerInlineQuery"]
        assert answers, "لم يُرد البوت على الاستعلام المضمّن"
        res = answers[-1].results
        ids = [r.id for r in res]                               # مقالات الألعاب أولًا، والتحدي في الآخر
        assert ids[-1] == "c" and "r" not in ids                # لم يلعب بعد: التحدي فقط
        assert res[-1].reply_markup.inline_keyboard[0][0].url.endswith("?start=inv_31")
    asyncio.run(go())


def test_inline_result_hides_name_for_hidden_players():
    async def go():
        h = Harness()
        h.db.upsert_user(32, "Secret")
        h.db.conn.execute("UPDATE users SET lb_hidden=1, best_score=8 WHERE tg_id=32")
        h.db.conn.commit()
        await h.dp.feed_update(h.bot, Update(update_id=902, inline_query=_inline(32, "Secret")))
        res = [c for c in h.session.calls if type(c).__name__ == "AnswerInlineQuery"][-1].results
        assert [r.id for r in res][-2:] == ["c", "r"]           # مقالات الألعاب تسبقهما
        c_res, r_res = res[-2], res[-1]
        assert "Secret" not in r_res.input_message_content.message_text
        assert "مجهول" in r_res.input_message_content.message_text and "8.0/10" in r_res.input_message_content.message_text
    asyncio.run(go())


def test_quick_test_result_also_has_a_share_button_with_invite_link():
    async def go():
        h = Harness()
        u = h.user(33, "Quick")
        await h.say(u, "/start")
        await h.tap(u, "qk")
        await h.play(u)
        photos = [c for c in h.session.calls if type(c).__name__ == "SendPhoto" and c.chat_id == 33]
        assert photos, "لم تُرسل بطاقة النتيجة"
        urls = [b.url for row in photos[-1].reply_markup.inline_keyboard for b in row if b.url]
        assert any("inv_33" in (x or "") for x in urls), urls          # الرابط مُرمَّز داخل رابط المشاركة
    asyncio.run(go())


def test_invitee_gets_bonus_once_after_first_full_test():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0            # إجابات بشرية السرعة (الاختبار يجيب فورًا)
        h.db.upsert_user(41, "Host")
        newbie = h.user(42, "Newbie")
        await h.say(newbie, "/start inv_41")                   # دخل عبر رابط دعوة 41
        await h.tap(newbie, "go")
        await h.play(newbie)
        photos = [c for c in h.session.calls if type(c).__name__ == "SendPhoto" and c.chat_id == 42]
        assert photos and "مكافأة الانضمام" in (photos[-1].caption or ""), (photos[-1].caption if photos else None)
        assert h.db.invite_count(41) == 1
        # اختبار ثانٍ لا يعيد المكافأة
        await h.tap(newbie, "go")
        await h.play(newbie)
        photos = [c for c in h.session.calls if type(c).__name__ == "SendPhoto" and c.chat_id == 42]
        assert "مكافأة الانضمام" not in (photos[-1].caption or "")
    asyncio.run(go())


def test_inline_games_use_banner_photos_when_a_file_id_is_known():
    from aiogram.types import InlineQueryResultCachedPhoto
    async def go():
        h = Harness()
        h.db.set_setting("inl_photo:mafia:ar", "FILE_MAFIA")
        await h.dp.feed_update(h.bot, Update(update_id=911, inline_query=_inline(33)))
        res = [c for c in h.session.calls if type(c).__name__ == "AnswerInlineQuery"][-1].results
        photos = {r.id: r for r in res if isinstance(r, InlineQueryResultCachedPhoto)}
        assert "g_mafia" in photos and photos["g_mafia"].photo_file_id == "FILE_MAFIA"
        assert "g_mo" in photos                                       # المافيا أونلاين بنفس اللافتة
        assert any(getattr(r, "id", "") == "g_tf" and not isinstance(r, InlineQueryResultCachedPhoto) for r in res)   # بلا معرّف = نتيجة نصية
    asyncio.run(go())
