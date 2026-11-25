"""خادم الشطرنج (Mini App): الصفحة + واجهة الـ API. كل طلب يُتحقق من هوية المستخدم عبر initData.

التحقق (من توثيق تيليجرام): مفتاح = HMAC_SHA256("WebAppData", التوكن)، والتوقيع = HMAC_SHA256(المفتاح، سلسلة البيانات).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import web

from . import chess_engine as CE

log = logging.getLogger(__name__)
PAGE = Path(__file__).parent / "web" / "chess.html"


def verify_init_data(init_data: str, token: str, max_age: int = 86400) -> dict | None:
    """يرجع بيانات المستخدم إن كان التوقيع صحيحاً، وإلا None."""
    if not init_data or not token:
        return None
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received = pairs.pop("hash", None)
    if not received:
        return None
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        return None
    try:
        if time.time() - int(pairs.get("auth_date", "0")) > max_age:
            return None
        return json.loads(pairs.get("user", "{}")) or None
    except (ValueError, TypeError):
        return None


def build_app(token: str, conn, on_finish=None) -> web.Application:
    """on_finish(gid) تُستدعى مرة واحدة عند انتهاء اللعبة (لإرسال النتيجة للشات)."""
    app = web.Application()

    async def page(request: web.Request):
        gid = request.match_info["gid"]
        if not gid.isdigit():
            raise web.HTTPNotFound()
        return web.FileResponse(PAGE, headers={"Cache-Control": "no-cache"})

    def user_of(request: web.Request) -> dict | None:
        return verify_init_data(request.headers.get("X-Init-Data", ""), token)

    def gid_of(request: web.Request) -> int | None:
        g = request.match_info.get("gid", "")
        return int(g) if g.isdigit() else None

    async def state(request: web.Request):
        gid, u = gid_of(request), user_of(request)
        if gid is None or u is None:
            return web.json_response({"error": "auth"}, status=401)
        v = CE.view(conn, gid, int(u["id"]))
        if not v:
            return web.json_response({"error": "gone"}, status=404)
        return web.json_response(v)

    async def run_action(request: web.Request, fn, *args):
        gid, u = gid_of(request), user_of(request)
        if gid is None or u is None:
            return web.json_response({"error": "auth"}, status=401)
        uid = int(u["id"])
        before = CE.view(conn, gid, uid)
        was_done = bool(before and before["state"] == "done")
        result = fn(conn, gid, uid, *args) if args else fn(conn, gid, uid)
        if isinstance(result, tuple):
            status, reason = result
        else:
            status, reason = result, None
        v = CE.view(conn, gid, uid)
        if v and v["state"] == "done" and not was_done and on_finish:
            try:
                await on_finish(gid)
            except Exception:  # noqa: BLE001
                log.exception("chess: cannot announce result for %s", gid)
        return web.json_response({"status": status, "reason": reason, "state": v})

    async def join(request: web.Request):
        gid, u = gid_of(request), user_of(request)
        if gid is None or u is None:
            return web.json_response({"error": "auth"}, status=401)
        name = (u.get("first_name") or "?")[:32]
        status = CE.join(conn, gid, int(u["id"]), name)
        v = CE.view(conn, gid, int(u["id"]))
        return web.json_response({"status": status, "state": v})

    async def move(request: web.Request):
        body = await request.json() if request.can_read_body else {}
        uci = str(body.get("uci", ""))[:6]
        return await run_action(request, lambda c, g, uid: CE.move(c, g, uid, uci))

    async def resign(request: web.Request):
        return await run_action(request, CE.resign)

    async def draw(request: web.Request):
        return await run_action(request, CE.offer_draw)

    app.router.add_get("/chess/{gid}", page)
    app.router.add_get("/api/chess/{gid}", state)
    app.router.add_post("/api/chess/{gid}/join", join)
    app.router.add_post("/api/chess/{gid}/move", move)
    app.router.add_post("/api/chess/{gid}/resign", resign)
    app.router.add_post("/api/chess/{gid}/draw", draw)
    return app
