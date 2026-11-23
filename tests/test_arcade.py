"""ألعاب ثنائية: المنطق (إكس أو، أربعة في صف، حجرة ورقة مقص) والطابور وتحدّي الصديق بالرابط."""
import asyncio

from harness import Harness, run
from otaku_bot import arcade as A


def test_xo_rules():
    assert A.xo_state([ "X", "X", "X", None, "O", "O", None, None, None]) == "X"      # صف
    assert A.xo_state(["O", None, None, None, "O", None, None, None, "O"]) == "O"     # قطر
    assert A.xo_state(["X", "O", "X", "X", "O", "O", "O", "X", "X"]) == "draw"        # امتلاء بلا فائز
    assert A.xo_state([None] * 9) is None


def test_c4_rules_vertical_and_diagonal_and_full_column():
    g = [[None] * 7 for _ in range(6)]
    for r in range(4):
        g[r][2] = "R"                                  # عمود من 4
    assert A.c4_state(g) == "R"
    g = [[None] * 7 for _ in range(6)]
    for i in range(4):
        g[i][i] = "Y"                                  # قطر
    assert A.c4_state(g) == "Y"
    g = [[None] * 7 for _ in range(6)]
    assert A.c4_drop(g, 3, "R") == 0 and A.c4_drop(g, 3, "Y") == 1
    for _ in range(4):                                  # العمود 5 فيه قرصان، نكمله حتى يمتلئ
        A.c4_drop(g, 5, "R")
    for _ in range(6):
        A.c4_drop(g, 5, "Y")
    assert A.c4_drop(g, 5, "Y") is None                # العمود ممتلئ


def test_rps_results():
    assert A.rps_result("r", "s") == 1 and A.rps_result("s", "r") == 2
    assert A.rps_result("p", "r") == 1 and A.rps_result("r", "r") == 0


def test_online_queue_pairs_two_players_and_both_get_a_board():
    async def go():
        A.queue["xo"].clear(); A.matches.clear(); A.user_match.clear()
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        a, b = h.user(11, "Ali"), h.user(12, "Bob")
        for u in (a, b):
            h.db.upsert_user(u.id, u.first_name)
        await h.tap(a, "ar:q:xo")
        await h.tap(b, "ar:q:xo")
        assert len(A.matches) == 1
        m = next(iter(A.matches.values()))
        assert set(m.players) == {11, 12}
        sent = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id in (11, 12)]
        assert {c.chat_id for c in sent} == {11, 12}
        first = m.players[0]
        await h.tap(h.user(first, "x"), "ar:x:%d:4" % m.gid)     # الأول يلعب الوسط
        assert m.board[4] == "X" and m.turn == 1
    run(go())


def test_friend_invite_link_starts_a_match_with_the_friend():
    async def go():
        A.matches.clear(); A.user_match.clear(); A.invites.clear()
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        host, friend = h.user(21, "Host"), h.user(22, "Friend")
        for u in (host, friend):
            h.db.upsert_user(u.id, u.first_name)
        await h.tap(host, "ar:f:rps")
        code = max(A.invites)
        await h.say(friend, f"/start ar_{code}")
        assert len(A.matches) == 1
        m = next(iter(A.matches.values()))
        assert set(m.players) == {21, 22} and m.kind == "rps"
        assert code not in A.invites                             # الرابط يُستهلك
    run(go())


def test_group_xo_two_players_join_and_play_on_one_message():
    from test_mafia_game import GROUP, gcmd

    async def go():
        A.matches.clear(); A.user_match.clear()
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        a, b = h.user(31, "Ali"), h.user(32, "Bob")
        for u in (a, b):
            h.db.upsert_user(u.id, u.first_name)
        await gcmd(h, a, "/xo", 500)
        assert len(A.matches) == 1
        m = next(iter(A.matches.values()))
        assert m.scope == "c" and m.state == "join" and m.players == [31]
        await h.tap(b, f"ar:j:{m.gid}")
        assert m.state == "play" and m.players == [31, 32]
        await h.tap(b, f"ar:x:{m.gid}:0")                        # ليس دور بوب
        assert m.board[0] is None
        await h.tap(a, f"ar:x:{m.gid}:0")                        # دور علي
        assert m.board[0] == "X" and m.turn == 1
        await h.tap(b, f"ar:x:{m.gid}:3")
        await h.tap(a, f"ar:x:{m.gid}:1")
        await h.tap(b, f"ar:x:{m.gid}:4")
        await h.tap(a, f"ar:x:{m.gid}:2")                        # علي يكمل الصف الأول
        assert m.state == "done" or not A.matches
        assert not A.user_match
        edits = [c for c in h.session.calls if type(c).__name__ == "EditMessageText" and c.chat_id == GROUP.id]
        assert any("فاز" in (c.text or "") for c in edits)
    run(go())


def test_inline_invite_ids_are_created_and_capped():
    A.invites.clear()
    ids = [A.make_invite(7, "xo") for _ in range(3)]
    assert all(i in A.invites and A.invites[i] == (7, "xo") for i in ids)
    for _ in range(600):
        A.make_invite(8, "rps")
    assert len(A.invites) <= 500
