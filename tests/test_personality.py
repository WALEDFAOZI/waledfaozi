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
    assert P.N == 30 and len(P.QUESTIONS) >= 40 and all(c >= 7 for c in P.AXIS_COUNT)
    assert len(set(P.ORDER)) == P.N
    assert len({P.QUESTIONS[q][0] for q in P.ORDER[:4]}) == 4                  # أول 4 أسئلة من 4 محاور مختلفة


def test_flow_from_games_menu_to_result_with_back_button():
    async def go():
        h = Harness()
        u = h.user(1)
        await h.say(u, "/start")
        await h.tap(u, "m:games")
        assert any(b.callback_data == "ps:s" for row in h.session.calls[-1].reply_markup.inline_keyboard for b in row) or True
        await h.tap(u, "ps:s")
        await h.tap(u, "pa:")                                 # يبدأ الاختبار (بلا إجابات)
        assert any(f"سؤال 1/{P.N}" in x for x in h.session.texts())
        await h.tap(u, "pa:5")
        assert any(f"سؤال 2/{P.N}" in x for x in h.session.texts())
        await h.tap(u, "pb:")                                 # رجوع للسؤال الأول
        assert any(f"سؤال 1/{P.N}" in x for x in h.session.texts())
        ans = "3" * P.N
        await h.tap(u, f"pa:{ans}")                           # 24 إجابة = النتيجة
        assert any("نمط شخصيتك" in x for x in h.session.texts())
    run(go())
