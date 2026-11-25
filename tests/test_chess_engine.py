"""قواعد الشطرنج: الحركات الشرعية، الدور، الكش مات، الاستسلام، والتعادل."""
from otaku_bot import chess_engine as CE
from otaku_bot.db import DB


def fresh():
    db = DB(":memory:")
    return db.conn


def started(conn):
    gid = CE.create(conn, 1, "أحمد")
    assert CE.join(conn, gid, 2, "سارة") == "ok"
    return gid


def test_join_rules_and_states():
    conn = fresh()
    gid = CE.create(conn, 1, "أحمد")
    assert CE.join(conn, gid, 1, "أحمد") == "own"        # ما تلعب ضد نفسك
    assert CE.join(conn, gid, 2, "سارة") == "ok"
    assert CE.join(conn, gid, 3, "خالد") == "full"       # اللعبة امتلأت
    assert CE.view(conn, gid, 1)["state"] == "play"


def test_turns_and_legal_moves():
    conn = fresh()
    gid = started(conn)
    assert CE.move(conn, gid, 2, "e7e5")[0] == "notturn"  # الأبيض يبدأ
    assert CE.move(conn, gid, 1, "e2e5")[0] == "illegal"  # حركة مستحيلة
    assert CE.move(conn, gid, 1, "zz")[0] == "illegal"
    assert CE.move(conn, gid, 1, "e2e4")[0] == "ok"
    assert CE.move(conn, gid, 1, "d2d4")[0] == "notturn"  # الدور للأسود الآن
    assert CE.move(conn, gid, 2, "e7e5")[0] == "ok"
    v = CE.view(conn, gid, 2)
    assert v["turn"] == "white" and v["moves"] == ["e4", "e5"] and v["my_color"] == "black"


def test_checkmate_ends_the_game_with_winner():
    conn = fresh()
    gid = started(conn)
    # طريق قصير إلى كش مات (حماقة الفتح)
    seq = [(1, "f2f3"), (2, "e7e5"), (1, "g2g4"), (2, "d8h4")]
    for uid, mv in seq:
        assert CE.move(conn, gid, uid, mv)[0] == "ok"
    v = CE.view(conn, gid, 1)
    assert v["state"] == "done" and v["result"] == "black"
    assert CE.move(conn, gid, 1, "a2a3")[0] == "notplaying"   # بعد النهاية ما تنفع حركة


def test_resign_gives_the_win_to_the_other_side():
    conn = fresh()
    gid = started(conn)
    assert CE.resign(conn, gid, 1) == "ok"
    v = CE.view(conn, gid, 2)
    assert v["state"] == "done" and v["result"] == "black"


def test_draw_offer_is_accepted_by_the_other_player():
    conn = fresh()
    gid = started(conn)
    assert CE.offer_draw(conn, gid, 1) == "offered"
    assert CE.view(conn, gid, 2)["draw_offered"] is True
    assert CE.offer_draw(conn, gid, 2) == "accepted"
    v = CE.view(conn, gid, 1)
    assert v["state"] == "done" and v["result"] == "draw"


def test_outsider_cannot_move_or_resign():
    conn = fresh()
    gid = started(conn)
    assert CE.resign(conn, gid, 9) == "notplayer"
    assert CE.move(conn, gid, 9, "e2e4")[0] == "notturn"
