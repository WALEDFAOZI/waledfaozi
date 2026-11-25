"""خادم الشطرنج: توقيع تيليجرام (initData) والـ API من الانضمام إلى الحركة والاستسلام."""
import asyncio
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from aiohttp.test_utils import TestClient, TestServer

from otaku_bot import chess_engine as CE
from otaku_bot.chess_web import build_app, verify_init_data
from otaku_bot.db import DB

TOKEN = "123456:TEST-TOKEN"


def init_data(uid: int, name: str, token: str = TOKEN, age: int | None = None) -> str:
    fields = {"auth_date": str(int(time.time()) if age is None else age),
              "user": json.dumps({"id": uid, "first_name": name}, ensure_ascii=False)}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def test_valid_signature_returns_the_user_and_tampering_is_rejected():
    data = init_data(7, "علي")
    assert verify_init_data(data, TOKEN)["id"] == 7
    assert verify_init_data(data.replace("%D8%B9", "%D8%B3"), TOKEN) is None   # تعديل البيانات
    assert verify_init_data(init_data(7, "علي", token="other"), TOKEN) is None  # توكن غلط
    assert verify_init_data(init_data(7, "علي", age=1), TOKEN) is None          # بيانات قديمة جداً
    assert verify_init_data("", TOKEN) is None


def test_api_full_flow_join_move_and_resign():
    async def go():
        db = DB(":memory:")
        gid = CE.create(db.conn, 1, "أحمد")
        app = build_app(TOKEN, db.conn)
        async with TestClient(TestServer(app)) as cl:
            a, b = {"X-Init-Data": init_data(1, "أحمد")}, {"X-Init-Data": init_data(2, "سارة")}
            r = await cl.get(f"/api/chess/{gid}", headers={})
            assert r.status == 401                                         # بدون توقيع: ممنوع
            r = await cl.post(f"/api/chess/{gid}/join", headers=b, json={})
            assert (await r.json())["status"] == "ok"
            r = await cl.post(f"/api/chess/{gid}/move", headers=b, json={"uci": "e7e5"})
            assert (await r.json())["status"] == "notturn"                 # ليس دورك
            r = await cl.post(f"/api/chess/{gid}/move", headers=a, json={"uci": "e2e4"})
            assert (await r.json())["status"] == "ok"
            r = await cl.get(f"/api/chess/{gid}", headers=b)
            st = await r.json()
            assert st["state"] == "play" and st["my_color"] == "black" and st["moves"] == ["e4"]
            r = await cl.post(f"/api/chess/{gid}/resign", headers=b, json={})
            assert (await r.json())["state"]["result"] == "white"
    asyncio.run(go())


def test_finish_callback_runs_once():
    async def go():
        db = DB(":memory:")
        gid = CE.create(db.conn, 1, "أحمد")
        CE.join(db.conn, gid, 2, "سارة")
        calls = []

        async def done(g):
            calls.append(g)
        app = build_app(TOKEN, db.conn, on_finish=done)
        async with TestClient(TestServer(app)) as cl:
            a, b = {"X-Init-Data": init_data(1, "أحمد")}, {"X-Init-Data": init_data(2, "سارة")}
            await cl.post(f"/api/chess/{gid}/resign", headers=a, json={})
            await cl.post(f"/api/chess/{gid}/resign", headers=b, json={})  # بعد النهاية: لا إعلان مرة ثانية
        assert calls == [gid]
    asyncio.run(go())
