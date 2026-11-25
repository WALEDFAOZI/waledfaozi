"""التطبيق المصغّر: الملف الشخصي، الإعدادات، الترتيب، الألعاب، والشطرنج، مع التحقق من هوية المستخدم."""
import asyncio

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from otaku_bot import chess_engine as CE
from otaku_bot.app_hub import add_hub_routes
from otaku_bot.chess_web import build_app
from otaku_bot.db import DB
from test_chess_web import TOKEN, init_data


def make(db):
    app = build_app(TOKEN, db.conn)
    add_hub_routes(app, TOKEN, db, lambda: "otaku_test_bot")
    return app


def test_profile_settings_top_and_games_for_the_signed_user():
    async def go():
        db = DB(":memory:")
        db.upsert_user(1, "أحمد")
        db.record_outcome(1, "mafia", "win")
        db.record_outcome(1, "mafia", "lose")
        gid = CE.create(db.conn, 1, "أحمد")
        CE.join(db.conn, gid, 2, "سارة")
        async with TestClient(TestServer(make(db))) as cl:
            h = {"X-Init-Data": init_data(1, "أحمد")}
            r = await cl.get("/api/app/me", headers={})
            assert r.status == 401                                       # بدون توقيع ممنوع
            me = await (await cl.get("/api/app/me", headers=h)).json()
            assert me["name"] == "أحمد"
            assert me["games"]["mafia"]["win"] == 1 and me["games"]["mafia"]["lose"] == 1
            assert me["chess"] and me["chess"][0]["opponent"] == "سارة"
            r = await cl.post("/api/app/settings", headers=h, json={"lb_hidden": True, "lang": "en", "notify": True})
            assert (await r.json())["ok"] is True
            me2 = await (await cl.get("/api/app/me", headers=h)).json()
            assert me2["lb_hidden"] is True and me2["lang"] == "en" and me2["notify"] is True
            top = await (await cl.get("/api/app/top", headers=h)).json()
            assert "rows" in top
            g = await (await cl.get("/api/app/games", headers=h)).json()
            assert any(x["key"] == "chess" for x in g["games"])
            assert g["games"][0]["link"].startswith("https://t.me/otaku_test_bot?")
            page = await cl.get("/app")
            assert page.status == 200 and "t-profile" in await page.text()
    asyncio.run(go())
