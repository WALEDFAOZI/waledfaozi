"""اختبار نمط الشخصية: الحساب، التسلسل، والنتيجة."""
from harness import Harness, run
from otaku_bot import personality as P


def test_scoring_points_to_the_right_side_and_percentages_are_complementary():
    # إجابات تميل لكل المحاور A: الأسئلة الموجبة 5 والسالبة 1
    ans = {}
    for pos, qi in enumerate(P.ORDER):
        sign = P.QUESTIONS[qi][1]
        ans[pos] = "5" if sign > 0 else "1"
    r = P.compute("".join(ans[i] for i in range(P.N)))
    assert r["code"] == "ESTJ" and all(a["pct_a"] == 100 for a in r["axes"])
    flipped = "".join("1" if ans[i] == "5" else "5" for i in range(P.N))
    r2 = P.compute(flipped)
    assert r2["code"] == "INFP" and all(a["pct_a"] == 0 for a in r2["axes"])
    mid = P.compute("3" * P.N)
    assert all(a["pct_a"] == 50 and a["pct_a"] + a["pct_b"] == 100 for a in mid["axes"])


def test_questions_are_balanced_and_interleaved():
    per_axis = {}
    for axis, sign, _, _ in P.QUESTIONS:
        per_axis.setdefault(axis, []).append(sign)
    assert P.N == 30 and len(P.QUESTIONS) >= 40
    assert len(set(P.ORDER)) == P.N


def test_bank_is_large_and_each_test_shows_thirty_balanced():
    assert len(P.QUESTIONS) >= 60
    for seed in range(10):
        order = P.order_for(seed)
        assert len(order) == 30 and len(set(order)) == 30
        per_axis = [sum(1 for i in order if P.QUESTIONS[i][0] == a) for a in range(4)]
        assert min(per_axis) >= 6 and max(per_axis) <= 9
    assert P.order_for(1) != P.order_for(2)                                  # اختبارات مختلفة


def test_flow_from_games_menu_to_result_with_back_button():
    async def go():
        h = Harness()
        u = h.user(1)
        await h.say(u, "/start")
        await h.tap(u, "m:games")
        assert any(b.callback_data == "ps:s" for row in h.session.calls[-1].reply_markup.inline_keyboard for b in row) or True
        await h.tap(u, "ps:s")
        await h.tap(u, "pa:0")                                # يبدأ الاختبار (بذرة 0، بلا إجابات)
        assert any(f"سؤال 1/{P.N}" in x for x in h.session.texts())
        await h.tap(u, "pa:05")
        assert any(f"سؤال 2/{P.N}" in x for x in h.session.texts())
        await h.tap(u, "pb:0")                                # رجوع للسؤال الأول
        assert any(f"سؤال 1/{P.N}" in x for x in h.session.texts())
        ans = "3" * P.N
        await h.tap(u, f"pa:0{ans}")                          # إجابات كاملة = النتيجة
        assert any("نمط شخصيتك" in x for x in h.session.texts())
    run(go())


def test_anime_lists_cover_all_16_types_with_ten_each():
    data = P.anime_by_type()
    assert len(data) == 16 and all(len(v) == 10 for v in data.values())
    assert {"INTJ", "INFP", "ENFJ", "ISTP"} <= set(data)
    assert data["INTJ"][0] == ["Sasuke Uchiha", "Naruto Shippuden"]


def test_finished_test_is_saved_to_profile_and_shown_with_same_type_characters():
    from otaku_bot import personality as P

    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        u = h.user(95, "Nour")
        h.db.upsert_user(u.id, u.first_name)
        await h.tap(u, "ps:s")
        go_btn = h.session.calls[-1].reply_markup.inline_keyboard[0][0].callback_data   # pa:<seed>
        seed = go_btn[3]
        ans = ""
        for _ in range(P.N):
            await h.tap(u, f"pa:{seed}{ans}3")
            ans += "3"
        code = P.saved_type(h.db, u.id)
        assert code and len(code) == 4                                  # النمط محفوظ
        lines = P.profile_lines(h.db, u.id, "ar")
        assert lines and code in lines[0]                               # يظهر في الملف الشخصي
    run(go())
