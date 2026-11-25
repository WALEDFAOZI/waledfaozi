"""محرك الشطرنج: القواعد (python-chess) وحالة اللعبة في القاعدة.

الحالة: wait (بانتظار الخصم) ← play (جارية) ← done (انتهت: كش مات، تعادل، استسلام).
كل حركة تُتحقق من الدور ومن شرعيتها على الخادم، فما يقدر أحد يغش من الواجهة.
"""
from __future__ import annotations

import json
import time

import chess

START_FEN = chess.STARTING_FEN


def _row(conn, gid: int):
    return conn.execute("SELECT * FROM chess_games WHERE id=?", (gid,)).fetchone()


def create(conn, creator: int, name: str, origin_chat: int | None = None, origin_msg: int | None = None) -> int:
    now = time.time()
    with conn:
        cur = conn.execute(
            "INSERT INTO chess_games(white,black,fen,moves,state,origin_chat,origin_msg,names,created,updated)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (creator, None, START_FEN, "", "wait", origin_chat, origin_msg, json.dumps({str(creator): name}), now, now))
    return cur.lastrowid


def join(conn, gid: int, uid: int, name: str) -> str:
    """يرجع: ok | full | own | gone"""
    g = _row(conn, gid)
    if not g or g["state"] != "wait":
        return "full" if g else "gone"
    if uid == g["white"]:
        return "own"
    names = json.loads(g["names"])
    names[str(uid)] = name
    with conn:
        conn.execute("UPDATE chess_games SET black=?, state='play', names=?, updated=? WHERE id=?",
                     (uid, json.dumps(names), time.time(), gid))
    return "ok"


def color_of(g, uid: int | None) -> str | None:
    if uid is None:
        return None
    if uid == g["white"]:
        return "white"
    if uid == g["black"]:
        return "black"
    return None


def result_of(board: chess.Board) -> str | None:
    if not board.is_game_over(claim_draw=True):
        return None
    out = board.outcome(claim_draw=True)
    if out is None or out.winner is None:
        return "draw"
    return "white" if out.winner == chess.WHITE else "black"


def move(conn, gid: int, uid: int, uci: str) -> tuple[str, str | None]:
    """يرجع (الحالة، سبب الخطأ). الحالة: ok | illegal | notturn | notplaying | gone"""
    g = _row(conn, gid)
    if not g:
        return "gone", None
    if g["state"] != "play":
        return "notplaying", None
    side = color_of(g, uid)
    board = chess.Board(g["fen"])
    if side is None or ("white" if board.turn == chess.WHITE else "black") != side:
        return "notturn", None
    try:
        mv = chess.Move.from_uci(uci)
    except ValueError:
        return "illegal", None
    if mv not in board.legal_moves:
        # ترقية تلقائية للوزير إذا الحركة بدون ترقية
        q = chess.Move(mv.from_square, mv.to_square, promotion=chess.QUEEN)
        if q in board.legal_moves:
            mv = q
        else:
            return "illegal", None
    san = board.san(mv)
    board.push(mv)
    moves = (g["moves"] + " " + san).strip()
    res = result_of(board)
    state, draw_by = ("done", None) if res else ("play", None)
    with conn:
        conn.execute("UPDATE chess_games SET fen=?, moves=?, state=?, result=?, draw_by=?, updated=? WHERE id=?",
                     (board.fen(), moves, state, res, draw_by, time.time(), gid))
    return "ok", None


def resign(conn, gid: int, uid: int) -> str:
    g = _row(conn, gid)
    if not g or g["state"] != "play":
        return "notplaying"
    side = color_of(g, uid)
    if side is None:
        return "notplayer"
    winner = "black" if side == "white" else "white"
    with conn:
        conn.execute("UPDATE chess_games SET state='done', result=?, draw_by=NULL, updated=? WHERE id=?",
                     (winner, time.time(), gid))
    return "ok"


def offer_draw(conn, gid: int, uid: int) -> str:
    """يرجع: offered | accepted | notplaying | notplayer"""
    g = _row(conn, gid)
    if not g or g["state"] != "play":
        return "notplaying"
    if color_of(g, uid) is None:
        return "notplayer"
    if g["draw_by"] and g["draw_by"] != uid:              # الخصم عرض قبل: قبول
        with conn:
            conn.execute("UPDATE chess_games SET state='done', result='draw', draw_by=NULL, updated=? WHERE id=?",
                         (time.time(), gid))
        return "accepted"
    with conn:
        conn.execute("UPDATE chess_games SET draw_by=?, updated=? WHERE id=?", (uid, time.time(), gid))
    return "offered"


def view(conn, gid: int, uid: int | None) -> dict | None:
    g = _row(conn, gid)
    if not g:
        return None
    board = chess.Board(g["fen"])
    names = json.loads(g["names"])
    return {
        "id": gid, "state": g["state"], "result": g["result"], "fen": g["fen"],
        "turn": "white" if board.turn == chess.WHITE else "black",
        "my_color": color_of(g, uid), "moves": g["moves"].split() if g["moves"] else [],
        "white_name": names.get(str(g["white"]), "?"),
        "black_name": names.get(str(g["black"]), "—") if g["black"] else "—",
        "draw_offered": bool(g["draw_by"]), "draw_by_me": g["draw_by"] == uid if uid else False,
        "in_check": board.is_check(),
    }


def players(conn, gid: int) -> tuple[int | None, int | None]:
    g = _row(conn, gid)
    return (g["white"], g["black"]) if g else (None, None)


def finished_once(conn, gid: int) -> bool:
    """هل انتهت اللعبة؟ (للتأكد من إرسال النتيجة مرة واحدة)"""
    g = _row(conn, gid)
    return bool(g and g["state"] == "done")
