"""بطاقات بأسلوب المانغا، بانر الترحيب، والنصوص البشرية المتنوعة."""
import io
import random
from pathlib import Path

from PIL import Image, features

from harness import Harness, last_menu_call, run
from otaku_bot import art, card
from otaku_bot.mascot import mood_for
from otaku_bot.texts import T, t

ROOT = Path(__file__).resolve().parent.parent
BRK = {"characters": (9, 10), "studios": (7, 8), "anime": (5, 8)}


def img(b):
    return Image.open(io.BytesIO(b))


def test_all_tiers_render_valid_jpeg_with_expected_size_and_differ():
    outs = {}
    for score in (0.5, 3, 5, 7, 9, 9.8):
        b = card.make_card("Tester", score, "title", 50, BRK, "ar")
        im = img(b)
        assert b[:2] == b"\xff\xd8" and im.size == (900, 560) and len(b) > 20_000
        outs[score] = b
    assert len(set(outs.values())) == 6                      # كل مستوى بصورة مختلفة (لون/ملامح)
    assert [card.tier_of(s)[1] for s in (0, 2, 4, 6, 8, 9.5)] == ["D", "C", "B", "A", "S", "S+"]
    assert [mood_for(s) for s in (1, 3, 5, 7, 9, 9.9)] == ["dizzy", "sweat", "smile", "happy", "star", "crown"]


def test_human_touch_character_look_is_personal_and_stable():
    """لكل لاعب «أوتاكو-تشان» بلون شعر وأعين خاص به (ثابت له، ومختلف عن غيره)؛ والحبيبات الورقية عشوائية قليلًا."""
    import random as _r
    from otaku_bot.mascot import HAIRS, IRISES
    look = lambda name, score: (_r.Random(card._seed(name, score)).choice(HAIRS), _r.Random(card._seed(name, score)).choice(IRISES))  # noqa: E731
    assert look("سارة", 7.2) == look("سارة", 7.2)
    looks = {look(f"player{i}", 7.0)[0] for i in range(40)}
    assert len(looks) >= 4                                    # تنوّع حقيقي بين اللاعبين
    a = card.make_card("سارة", 7.2, "أوتاكو متمرس", 60, BRK, "ar")
    assert img(a).size == (900, 560)


def test_profile_sudden_and_banner_cards():
    p = {"name": "W", "best": 8.7, "tests": 12, "sudden": 9, "rank": 3, "weekly_rank": 1, "answers": 600, "correct": 420,
         "cats": [("characters", 0.91, 40), ("studios", 0.8, 30), ("anime", 0.66, 25)], "games": {}}
    for lang in ("ar", "en"):
        assert img(card.make_profile_card(p, "Sensei", lang)).size == (900, 600)
        assert img(card.make_sudden_card("W", 14, 15, 21, lang)).size == (900, 560)
        assert img(card.make_banner(lang)).size == (1280, 640)
    # ملف بدون ترتيب/تصنيفات يشتغل أيضًا
    assert card.make_profile_card({"name": "N", "best": 1.0, "tests": 1, "answers": 0, "correct": 0, "cats": []}, "Noob", "ar")


def test_cards_render_without_raqm_and_without_japanese_font(monkeypatch):
    orig = features.check
    monkeypatch.setattr(art.features, "check", lambda n: False if n == "raqm" else orig(n))
    monkeypatch.setattr(art, "_JP", [])                       # استضافة بلا خط ياباني: نتخطى الكتابة اليابانية فقط
    assert not art.has_jp()
    assert img(card.make_card("والد فيصل", 8.7, "سينسي", 93, BRK, "ar")).size == (900, 560)


def test_bundled_banners_exist_and_licenses_are_shipped():
    for name in ("banner.jpg", "banner_en.jpg"):
        p = ROOT / "assets" / name
        im = Image.open(p)
        assert im.size == (1280, 640) and p.stat().st_size > 50_000
    assert (ROOT / "assets" / "fonts" / "Inter-Black.otf").is_file() and (ROOT / "assets" / "fonts" / "ipagp.ttf").is_file()
    lic = (ROOT / "assets" / "FONT-LICENSES.txt").read_text(encoding="utf-8")
    assert "Open Font License" in lic and "IPA Font License" in lic


def test_start_sends_banner_with_menu_caches_file_id_and_falls_back():
    async def go():
        h = Harness()
        await h.say(h.user(1, "Waled"), "/start")
        m = last_menu_call(h)
        assert type(m).__name__ == "SendPhoto" and "يا هلا والله Waled!" in m.caption
        data = {b.callback_data for row in m.reply_markup.inline_keyboard for b in row}
        assert {"go", "m:games", "pf"} <= data and "qk" not in data   # زر «اختبار سريع» أُلغي بطلب المستخدم
        # معرّف صورة مخزَّن: لا نرفع الملف ثانية
        from otaku_bot.config import ROOT as _R
        bkey = f"banner_fid_ar_{(_R / 'assets' / 'banner.jpg').stat().st_size}"
        h.db.set_setting(bkey, "CACHED_FID")
        await h.say(h.user(2), "/start")
        assert last_menu_call(h).photo == "CACHED_FID"
        # فشل الصورة (معرّف قديم): يرجع للنص ويمسح المعرّف التالف
        h.session.bad_photos = {"CACHED_FID"}
        await h.say(h.user(3), "/start")
        assert type(last_menu_call(h)).__name__ == "SendMessage" and h.db.get_setting(bkey) == ""
        # الإنجليزية: بانر ونص إنجليزي
        en = h.user(4, "Sam", lang="en")
        await h.say(en, "/start")
        m = last_menu_call(h)
        assert type(m).__name__ == "SendPhoto" and "Hey Sam, welcome aboard" in m.caption
    run(go())


def test_result_message_has_human_line_and_card_is_jpeg():
    async def go():
        h = Harness()
        u = h.user(1, "Sara")
        await h.tap(u, "go")
        await h.play(u, correct=True)
        photo = [c for c in h.session.calls if type(c).__name__ == "SendPhoto"][-1]
        assert photo.photo.filename == "result.jpg"
        assert "<i>" in photo.caption and "خلصت يا Sara" in photo.caption
        pools = [x for x in T["ar"]["res_line_king"]]
        assert any(line in photo.caption for line in pools)            # 10/10 → جملة من مجموعة «الملك»
        # الموت المفاجئ: بطاقة + جملة
        await h.tap(u, "sd")
        await h.play(u, correct=False, limit=1)
        sp = [c for c in h.session.calls if type(c).__name__ == "SendPhoto"][-1]
        assert sp.photo.filename == "sudden.jpg" and "<i>" in sp.caption
    run(go())


def test_text_pools_are_varied_complete_and_formatted():
    random.seed(0)
    for L in ("ar", "en"):
        assert len({t(L, "toast_ok") for _ in range(80)}) >= 3          # الرد يتبدّل ولا يتكرر نفسه
        assert len({t(L, "toast_bad", ans="X") for _ in range(80)}) >= 3
        for tier in ("king", "sensei", "seasoned", "otaku", "casual", "noob"):
            pool = T[L][f"res_line_{tier}"]
            assert isinstance(pool, list) and len(pool) >= 3 and len(set(pool)) == len(pool)
        for key in ("sd_line_low", "sd_line_mid", "sd_line_high"):
            assert len(T[L][key]) >= 2
        assert "X" in t(L, "toast_bad", ans="X")
    # كل مجموعة جمل عربية لها مقابل إنجليزي بنفس العدد
    for k, v in T["ar"].items():
        if isinstance(v, list):
            assert isinstance(T["en"][k], list) and len(T["en"][k]) == len(v), k
    # لا بقايا نبرة آلية متكررة في الرسائل الأساسية
    for L in ("ar", "en"):
        assert "—" not in T[L]["welcome"]


def test_welcome_uses_first_name_escaped_in_every_entry_point():
    async def go():
        h = Harness()
        u = h.user(1, "<b>Hack</b> & Co")                          # اسم فيه وسوم: لازم يُهرَّب
        await h.say(u, "/start")
        cap = last_menu_call(h).caption
        assert "يا هلا والله &lt;b&gt;Hack&lt;/b&gt; &amp; Co!" in cap and "<b>Hack</b>" not in cap
        await h.tap(u, "menu")
        assert "يا هلا والله &lt;b&gt;Hack" in h.session.texts()[-1]
        await h.tap(u, "lg:en")
        assert "Hey &lt;b&gt;Hack" in h.session.texts()[-1]
        from otaku_bot.texts import t
        assert "{name}" not in t("ar", "welcome", name="X") and "X" in t("en", "welcome", name="X")
    run(go())


def test_add_bot_buttons_sit_side_by_side_in_the_menu_with_rights():
    from otaku_bot import bot as B
    B.set_bot_username("otaku_test_bot")
    try:
        rows = B.add_bot_row("ar")
        assert len(rows) == 1 and len(rows[0]) == 2                       # زرّان في صف واحد
        assert all(b.style == "success" for b in rows[0])                  # أخضران
        urls = [b.url for b in rows[0]]
        assert "startgroup=play&admin=delete_messages+pin_messages+invite_users" in urls[0]
        assert "startchannel=play&admin=post_messages+edit_messages+delete_messages" in urls[1]
        B.set_bot_username("")
        assert B.add_bot_row("ar") == []                                    # بلا اسم بوت: لا أزرار
    finally:
        B.set_bot_username("otaku_test_bot")
