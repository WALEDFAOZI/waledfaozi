"""الليل ما يُحسم (ولا يُعلن القتيل) إلا بعد أن يختار الطبيب، أو ينتهي الوقت."""
from otaku_bot import mafia_game as MG


def make_game():
    g = MG.Game(gid=1, chat_id=-100, scope="group", host_id=1, host_name="h", lang="ar")
    for uid, role in [(1, "killer"), (2, "doctor"), (3, "detective"), (4, "citizen"), (5, "citizen")]:
        g.players[uid] = MG.Player(uid=uid, name=f"p{uid}", role=role)
    return g


def test_night_waits_for_the_doctor_even_if_killers_already_picked():
    g = make_game()
    g.night_picks = {1: 4}                       # القاتل اختار
    g.acted = {3}                                # المحقق اختار، والطبيب لم يختر بعد
    assert MG.night_complete(g) is False          # لا إعلان الآن
    g.acted.add(2)                               # الطبيب اختار
    assert MG.night_complete(g) is True


def test_dead_doctor_does_not_block_the_night():
    g = make_game()
    g.players[2].alive = False
    g.night_picks = {1: 4}
    g.acted = {3}
    assert MG.night_complete(g) is True


def test_night_waits_for_killers_too():
    g = make_game()
    g.acted = {2, 3}
    assert MG.night_complete(g) is False          # القاتل لم يختر
