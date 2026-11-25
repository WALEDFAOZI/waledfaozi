"""أمر /chess: ينشئ لعبة وزر «العب الآن» برابط startapp، ويحترم إيقاف اللعبة من الأدمن."""
import asyncio

from harness import Harness, run
from otaku_bot import chess_bot as CB
from otaku_bot import chess_engine as CE


def test_chess_command_creates_a_game_with_a_startapp_button():
    async def go():
        CB.set_username("otaku_test_bot")
        h = Harness()
        u = h.user(5, "Ali")
        h.db.upsert_user(5, "Ali")
        await h.say(u, "/chess")
        sent = [c for c in h.session.calls if type(c).__name__ == "SendMessage"][-1]
        urls = [b.url for row in sent.reply_markup.inline_keyboard for b in row if b.url]
        assert urls and urls[0].startswith("https://t.me/otaku_test_bot?startapp=chess_")
        gid = int(urls[0].split("chess_")[1])
        v = CE.view(h.db.conn, gid, 5)
        assert v["state"] == "wait" and v["my_color"] == "white"
    run(go())


def test_chess_can_be_switched_off_from_admin():
    async def go():
        CB.set_username("otaku_test_bot")
        h = Harness()
        h.db.set_game_on("chess", False)
        u = h.user(6, "Sara")
        h.db.upsert_user(6, "Sara")
        await h.say(u, "/chess")
        texts = [c.text for c in h.session.calls if type(c).__name__ == "SendMessage"]
        assert any("متوقفة" in (x or "") for x in texts)
        assert CE.view(h.db.conn, 1, None) is None
    run(go())
