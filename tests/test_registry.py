import asyncio

import pytest

from otaku_bot import registry as R
from otaku_bot.registry import Registry, RegistryError

TOKEN = "123456:SECRET-TOKEN-VALUE"


@pytest.fixture
def reg(tmp_path):
    r = Registry(tmp_path / "registry.db", R.generate_key())
    yield r
    r.close()


def test_token_is_stored_encrypted_and_reads_back(reg, tmp_path):
    reg.register_main(111, "MainBot", TOKEN, str(tmp_path / "otaku.db"))
    assert reg.token(R.MAIN_TENANT) == TOKEN
    raw = (tmp_path / "registry.db").read_bytes()
    assert TOKEN.encode() not in raw                      # لا يظهر التوكن بصيغة واضحة في الملف


def test_register_main_is_idempotent_and_updates_token(reg, tmp_path):
    db = str(tmp_path / "otaku.db")
    reg.register_main(111, "MainBot", TOKEN, db)
    reg.register_main(111, "MainBot", TOKEN + "x", db)
    assert reg.token(R.MAIN_TENANT) == TOKEN + "x"
    assert reg.tenant(R.MAIN_TENANT)["owner_user_id"] is None
    assert reg.db_path(R.MAIN_TENANT) == db


def test_wrong_key_refuses_to_decrypt(tmp_path):
    path = tmp_path / "registry.db"
    Registry(path, R.generate_key()).register_main(111, "MainBot", TOKEN, "x.db")
    other = Registry(path, R.generate_key())
    with pytest.raises(RegistryError):
        other.token(R.MAIN_TENANT)
    other.close()


def test_invalid_key_is_rejected(tmp_path):
    with pytest.raises(RegistryError):
        Registry(tmp_path / "r.db", "not-a-key")


def test_one_bot_per_owner_and_unique_bot_token(reg, tmp_path):
    tid = reg.add_tenant(42, 900, "KidBot", "900:AAA", str(tmp_path / "t1.db"))
    assert tid > 0 and reg.token(tid) == "900:AAA"
    with pytest.raises(RegistryError):                    # نفس المالك: مرفوض
        reg.add_tenant(42, 901, "Second", "901:BBB", str(tmp_path / "t2.db"))
    with pytest.raises(RegistryError):                    # نفس التوكن/البوت: مرفوض
        reg.add_tenant(43, 900, "Copy", "900:AAA", str(tmp_path / "t3.db"))


def test_chat_claim_is_first_wins(reg):
    assert reg.claim_chat(-1001, 0) == 0                  # الرئيسي يطالب أولًا
    assert reg.claim_chat(-1001, 5) == 0                  # الفرعي يتلقى المالك الحالي ولا يغيّره
    assert reg.chat_owner(-1001) == 0
    assert reg.claim_chat(-1002, 5) == 5
    assert reg.chat_owner(-1002) == 5


class _Me:
    id = 111
    username = "MainBot"


class _Bot:
    def __init__(self, fail=False):
        self.fail = fail

    async def get_me(self):
        if self.fail:
            raise RuntimeError("network down")
        return _Me()


class _Settings:
    def __init__(self, path, key, token=TOKEN, db="x.db"):
        self.registry_path, self.registry_key, self.token, self.db_path = path, key, token, db


def test_startup_registration_never_stops_the_bot(tmp_path, caplog):
    key = R.generate_key()
    s = _Settings(tmp_path / "r.db", key)
    asyncio.run(R.register_main(_Bot(), s))
    r = Registry(tmp_path / "r.db", key)
    assert r.token(R.MAIN_TENANT) == TOKEN
    r.close()
    asyncio.run(R.register_main(_Bot(fail=True), s))      # فشل الشبكة: لا استثناء يخرج
    asyncio.run(R.register_main(_Bot(), _Settings(tmp_path / "r.db", "")))   # بلا مفتاح: لا شيء
