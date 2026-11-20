import asyncio

from otaku_bot import links


def test_message_url_for_public_and_private_chats():
    assert links.msg_url(-1001234567890, "Anime1Galaxy", 9) == "https://t.me/Anime1Galaxy/9"
    assert links.msg_url(-1001234567890, None, 55) == "https://t.me/c/1234567890/55"


def test_back_row_is_empty_without_a_live_message_and_labels_by_chat_type():
    class Chat:
        def __init__(self, username, type_):
            self.username, self.type = username, type_

    class Bot:
        def __init__(self, chat):
            self.chat = chat

        async def get_chat(self, chat_id):
            return self.chat

    async def go():
        links._INFO.clear()
        assert await links.back_rows(Bot(Chat(None, "supergroup")), -100111, None, "ar") == []
        rows = await links.back_rows(Bot(Chat("Anime1Galaxy", "channel")), -100222, 7, "ar")
        assert rows[0][0].text == "↩️ العودة للقناة" and rows[0][0].url == "https://t.me/Anime1Galaxy/7"
        links._INFO.clear()
        rows = await links.back_rows(Bot(Chat(None, "supergroup")), -100333, 8, "ar")
        assert rows[0][0].text == "↩️ العودة للمجموعة" and rows[0][0].url == "https://t.me/c/333/8"
    asyncio.run(go())
