"""دور الطبيب: الحماية تلغي الضربة على الهدف المحمي فقط، والحالات الحدّية."""
from otaku_bot import mafia as M

ROLES = {1: "killer", 2: "killer", 3: "doctor", 4: "citizen", 5: "citizen", 6: "detective", 7: "citizen", 8: "citizen"}


def test_protected_target_survives_and_others_die():
    alive = set(ROLES)
    r = M.resolve_night(ROLES, alive, M.Night(kills=[4, 5], protect={"doctor": 4}))
    assert r.victims == [5] and r.saved


def test_protecting_a_non_target_saves_nobody():
    alive = set(ROLES)
    r = M.resolve_night(ROLES, alive, M.Night(kills=[4], protect={"doctor": 5}))
    assert r.victims == [4] and not r.saved


def test_doctor_can_protect_himself():
    alive = set(ROLES)
    r = M.resolve_night(ROLES, alive, M.Night(kills=[3], protect={"doctor": 3}))
    assert r.victims == [] and r.saved


def test_two_strikes_on_the_protected_target_still_save_it():
    alive = set(ROLES)
    r = M.resolve_night(ROLES, alive, M.Night(kills=[4, 4], protect={"doctor": 4}))
    assert r.victims == [] and r.saved


def test_protection_on_a_dead_target_does_nothing_and_does_not_crash():
    alive = set(ROLES) - {4}
    r = M.resolve_night(ROLES, alive, M.Night(kills=[5], protect={"doctor": 4}))
    assert r.victims == [5] and not r.saved


def test_no_protection_means_kill_goes_through():
    alive = set(ROLES)
    r = M.resolve_night(ROLES, alive, M.Night(kills=[4]))
    assert r.victims == [4] and not r.saved


def test_auto_config_always_has_a_doctor_from_seven_players():
    for n in range(7, 16):
        _, specials = M.auto_config(n)
        assert "doctor" in specials
