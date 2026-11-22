"""منطق المافيا: التحقق من الإعدادات، توزيع الأدوار، الليل، التصويت، والفوز."""
import random

import pytest

from otaku_bot import mafia as M


def test_config_rules():
    M.Config(killers=1, specials=["detective", "doctor"]).validate(7)           # 7 = قاتل + محقق + طبيب + 4 مواطنين
    with pytest.raises(M.ConfigError):
        M.Config(killers=0).validate(6)                                         # لازم قاتل
    with pytest.raises(M.ConfigError):
        M.Config(killers=1, specials=["doctor", "doctor"]).validate(8)          # دور خاص مكرر
    with pytest.raises(M.ConfigError):
        M.Config(killers=2, specials=["detective", "doctor"]).validate(6)   # مواطنون < 3
    with pytest.raises(M.ConfigError):
        M.Config(killers=3).validate(6)                                         # القتلة ≥ غيرهم
    with pytest.raises(M.ConfigError):
        M.Config(killers=1).validate(4)                                         # أقل من الحد الأدنى للاعبين
    with pytest.raises(M.ConfigError):
        M.Config(killers=1).validate(16)                                        # أكثر من الحد الأقصى
    with pytest.raises(M.ConfigError):
        M.Config(killers=1, specials=["witch"]).validate(6)                     # دور غير معروف


def test_assignment_matches_config_and_only_killers_repeat():
    rng = random.Random(3)
    ids = list(range(1, 11))
    cfg = M.Config(killers=2, specials=["detective", "doctor", "joker"])
    roles = M.assign(ids, cfg, rng)
    counts = {}
    for r in roles.values():
        counts[r] = counts.get(r, 0) + 1
    assert counts == {"killer": 2, "detective": 1, "doctor": 1, "joker": 1, "citizen": 5}
    assert len(roles) == 10


def test_night_kill_and_protection():
    roles = {1: "killer", 2: "doctor", 3: "citizen", 4: "citizen", 5: "detective", 6: "citizen"}
    alive = set(roles)
    # القتلة يختارون 3، والطبيب يحمي 3 → لا قتيل
    r = M.resolve_night(roles, alive, M.Night(kill=3, protect={"doctor": 3}))
    assert r.victim is None and r.saved
    # الطبيب يحمي غير الضحية → يموت الهدف
    r = M.resolve_night(roles, alive, M.Night(kill=4, protect={"doctor": 2}))
    assert r.victim == 4 and not r.saved
    # المحقق يكشف فريق القاتل
    r = M.resolve_night(roles, alive, M.Night(check=1))
    assert r.detective == (1, M.MAFIA)
    r = M.resolve_night(roles, alive, M.Night(check=3))
    assert r.detective == (3, M.TOWN)


def test_vote_eliminates_the_most_voted_and_ties_mean_nobody():
    alive = {1, 2, 3, 4, 5}
    assert M.vote(alive, {1: 2, 3: 2}) == 2                     # صوتان مقابل لا شيء: يُطرد الأكثر
    assert M.vote(alive, {1: 2, 3: 2, 4: 2, 5: 3}) == 2        # 3 مقابل 1: يُطرد
    assert M.vote(alive, {1: 2, 3: 4, 5: 3, 2: 5}) is None     # كل واحد صوت لشخص: تعادل = لا طرد
    assert M.vote(alive, {1: 2, 3: 2, 2: 4, 5: 4}) is None     # 2 و4 بصوتين لكل منهما: تعادل = لا طرد
    assert M.vote({1, 2, 3}, {4: 1, 2: 1}) == 1                # صوت الميت لا يُحسب، وصوتان لـ 1 يكفيان
    assert M.vote({1, 2, 3}, {4: 1}) is None                   # لا أصوات حيّة = لا طرد


def test_win_conditions():
    roles = {1: "killer", 2: "citizen", 3: "citizen", 4: "citizen", 5: "joker"}
    assert M.winner(roles, {2, 3, 4, 5}) == M.TOWN                 # القاتل مات
    assert M.winner(roles, {1, 2}) == M.MAFIA                      # قاتل مقابل مواطن واحد
    assert M.winner(roles, {1, 2, 3, 4, 5}) is None                 # اللعبة مستمرة
    assert M.winner(roles, {1, 2, 3, 4, 5}, last_voted="joker") is None    # المجنون من المواطنين: طرده لا ينهي اللعبة


def test_mayor_double_vote_changes_the_outcome_only_with_weight():
    alive = {1, 2, 3, 4, 5}
    ballots = {1: 2, 3: 4}                       # صوت لكل مرشح: تعادل
    assert M.vote(alive, ballots) is None
    assert M.vote(alive, ballots, {1: 2}) == 2   # صوت العمدة مرتان يرجّح الكفة
    assert "mayor" in M.ROLES and "mayor" in M.SPECIAL
