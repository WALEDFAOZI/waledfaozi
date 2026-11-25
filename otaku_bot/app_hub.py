"""التطبيق المصغّر الكامل (Mini App): الرئيسية، الملف الشخصي، الشطرنج، الترتيب، والإعدادات.

كل طلب يُتحقق من هوية المستخدم عبر initData (نفس تحقق الشطرنج)، ونفس البيانات اللي يشوفها في البوت.
"""
from __future__ import annotations

from pathlib import Path

from aiohttp import web

from . import chess_engine as CE
from . import online_notify, progress
from .chess_web import verify_init_data
from .quiz import title_for

PAGE = Path(__file__).parent / "web" / "app.html"

GAMES = [  # (المفتاح، الاسم بالعربي، الاسم بالإنجليزي، المسار في البوت)
    ("quiz", "الاختبار الكامل", "Full quiz", "start=go"),
    ("sudden", "الموت المفاجئ", "Sudden death", "start=on_sudden"),
    ("tf", "صح أو خطأ", "True or false", "start=on_tf"),
    ("images", "أسئلة الصور", "Picture quiz", "start=on_images"),
    ("kt", "كت", "KT game", "start=kt"),
    ("mafia", "المافيا", "Mafia", "start=mo_go"),
    ("chess", "الشطرنج", "Chess", "start=chess"),
]


def _u(request: web.Request, token: str) -> dict | None:
    return verify_init_data(request.headers.get("X-Init-Data", ""), token)


def add_hub_routes(app: web.Application, token: str, db, get_username) -> None:
    """يضيف مسارات التطبيق المصغّر إلى نفس خادم الشطرنج."""

    async def page(request: web.Request):
        return web.FileResponse(PAGE, headers={"Cache-Control": "no-cache"})

    async def me(request: web.Request):
        u = _u(request, token)
        if not u:
            return web.json_response({"error": "auth"}, status=401)
        uid = int(u["id"])
        db.upsert_user(uid, u.get("first_name") or "?")
        p = db.user_profile(uid) or {}
        usr = db.get_user(uid)
        L = db.get_lang(uid)
        best = float(p.get("best") or 0)
        lvl_xp = int(usr["xp"] or 0) if usr else 0
        chess = []
        for r in db.conn.execute(
                "SELECT id, white, black, state, result FROM chess_games WHERE white=? OR black=? "
                "ORDER BY updated DESC LIMIT 15", (uid, uid)):
            other = r["black"] if r["white"] == uid else r["white"]
            names = CE.view(db.conn, r["id"], uid) or {}
            opp = names.get("black_name" if r["white"] == uid else "white_name", "—") if other else "—"
            chess.append({"id": r["id"], "state": r["state"], "result": r["result"],
                          "color": "white" if r["white"] == uid else "black", "opponent": opp})
        return web.json_response({
            "name": p.get("name") or u.get("first_name") or "?",
            "lang": L,
            "best": round(best, 1),
            "title": title_for(best, L) if best else "",
            "tests": int(p.get("tests") or 0),
            "rank": p.get("rank"),
            "weekly_rank": p.get("weekly_rank"),
            "answers": int(p.get("answers") or 0),
            "correct": int(p.get("correct") or 0),
            "level": progress.level_of(lvl_xp),
            "xp": lvl_xp,
            "achievements": len(db.achievements_of(uid)),
            "achievements_total": len(progress.ACH),
            "games": db.personal_game_stats(uid),
            "recent": [round(float(x["score"]), 1) for x in db.last_session_stats(uid)][:10],
            "lb_hidden": bool(usr["lb_hidden"]) if usr else False,
            "notify": online_notify.is_on(db, uid),
            "chess": chess,
        })

    async def settings(request: web.Request):
        u = _u(request, token)
        if not u:
            return web.json_response({"error": "auth"}, status=401)
        uid = int(u["id"])
        body = await request.json() if request.can_read_body else {}
        if "lang" in body and body["lang"] in ("ar", "en"):
            db.set_lang(uid, body["lang"])
        if "lb_hidden" in body:
            db.set_lb_hidden(uid, bool(body["lb_hidden"]))
        if "notify" in body:
            db.set_setting(online_notify.KEY.format(uid=uid), "1" if body["notify"] else "0")
        return web.json_response({"ok": True})

    async def top(request: web.Request):
        if not _u(request, token):
            return web.json_response({"error": "auth"}, status=401)
        rows = db.leaderboard(10)
        return web.json_response({"rows": [{"name": r["name"], "score": round(float(r["best_score"]), 1)} for r in rows]})

    async def games(request: web.Request):
        if not _u(request, token):
            return web.json_response({"error": "auth"}, status=401)
        me_name = get_username() or ""
        out = []
        for key, ar, en, path in GAMES:
            out.append({"key": key, "ar": ar, "en": en,
                        "link": f"https://t.me/{me_name}?{path}" if me_name else ""})
        return web.json_response({"games": out, "enabled": {k: db.game_on(k) for k, *_ in GAMES}})

    app.router.add_get("/app", page)
    app.router.add_get("/api/app/me", me)
    app.router.add_post("/api/app/settings", settings)
    app.router.add_get("/api/app/top", top)
    app.router.add_get("/api/app/games", games)
