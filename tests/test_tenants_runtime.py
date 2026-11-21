"""المراحل 3 و4: تسجيل البوتات الفرعية، التحقق عبر الرئيسي، وملكية المجموعات."""
import asyncio
from types import SimpleNamespace

import pytest

from harness import QPATH
from otaku_bot import tenants as T
from otaku_bot.config import Settings
from otaku_bot.registry import MAIN_TENANT, Registry, RegistryError, generate_key


@pytest.fixture
def base(tmp_path):
    return Settings(token="1:main", db_path=str(tmp_path / "otaku.db"), questions_path=QPATH, timer_seconds=0,
                    cooldown_minutes=0, admin_ids=(), required_channel="@Anime1Galaxy")


@pytest.fixture
def reg(tmp_path):
    r = Registry(tmp_path / "registry.db", generate_key())
    r.register_main(111, "MainBot", "111:main", str(tmp_path / "otaku.db"))
    yield r
    r.close()
    T.RUNTIME.handles.clear()
    T.RUNTIME.main_bot = None


def test_child_bot_gets_own_db_state_owner_and_dispatcher(reg, base, tmp_path):
    tid = reg.add_tenant(42, 900, "KidBot", "900:KIDTOKEN", str(tmp_path / "tenants" / "900.db"))
    h = T.build_child(base, reg, tid)
    assert h.ctx.tenant_id == tid
    assert h.ctx.settings.admin_ids == (42,)                  # المالك وحده أدمن بوته
    assert h.ctx.settings.required_channel == "@Anime1Galaxy"  # القناة الإلزامية من الرئيسي
    assert h.ctx.settings.backup_chat == ""                    # لا نسخ احتياطية للرئيسي تُرسل من بوت فرعي
    assert h.ctx.state is not T.RUNTIME.base and h.ctx.state.mafia_games is not h.ctx.state.spy_games
    assert T.RUNTIME.handles[tid] is h
    assert T.RUNTIME.children() == [h]


def test_main_bot_is_not_listed_as_a_child(reg):
    assert T.RUNTIME.children() == []


def test_registration_rules(reg, base, tmp_path):
    async def fake_ok(token):
        return int(token.split(":")[0]), "Kid"

    async def go():
        r = T.Registration(reg, base, validate=fake_ok)
        tid = await r.register(42, "900:AAA")
        assert tid > 0
        with pytest.raises(RegistryError):                    # مالك له بوت بالفعل
            await r.register(42, "901:BBB")
        with pytest.raises(RegistryError):                    # توكن مسجّل لغيره
            await r.register(43, "900:AAA")
        with pytest.raises(RegistryError):                    # البوت الرئيسي نفسه
            await r.register(44, "111:main")
        with pytest.raises(RegistryError):                    # توكن بصيغة خاطئة
            await r.register(45, "no-colon")
        assert reg.tenant(tid)["db_path"].endswith("900.db")  # قاعدة البوت الفرعي في مجلد خاص
    asyncio.run(go())


def test_registration_failure_does_not_leak_the_token(reg, base):
    async def broken(token):
        raise RuntimeError("network " + token)

    async def go():
        r = T.Registration(reg, base, validate=broken)
        with pytest.raises(RegistryError) as e:
            await r.register(42, "900:SECRET")
        assert "SECRET" not in str(e.value)
    asyncio.run(go())


class _FakeMainBot:
    def __init__(self, status="member"):
        self.status = status
        self.asked = []

    async def get_chat_member(self, chat, uid):
        self.asked.append((chat, uid))
        return SimpleNamespace(status=self.status)


def test_child_membership_check_is_relayed_to_the_main_bot():
    main = _FakeMainBot("member")
    T.RUNTIME.main_bot = main
    member = asyncio.run(T.relay_member("@Anime1Galaxy", 5))
    assert member.status == "member" and main.asked == [("@Anime1Galaxy", 5)]


def test_relay_refuses_when_the_main_bot_is_not_ready():
    T.RUNTIME.main_bot = None
    with pytest.raises(T.RelayUnavailable):
        asyncio.run(T.relay_member("@Anime1Galaxy", 5))


class _Chat:
    def __init__(self, cid, type_="supergroup"):
        self.id, self.type = cid, type_


class _Bot:
    def __init__(self):
        self.left = []

    async def leave_chat(self, chat_id):
        self.left.append(chat_id)


def _event(chat, old, new):
    return SimpleNamespace(chat=chat, old_chat_member=SimpleNamespace(status=old),
                           new_chat_member=SimpleNamespace(status=new))


def test_second_bot_in_a_group_leaves_by_itself(reg):
    guard_main = T.OwnershipGuard(reg, MAIN_TENANT)
    guard_kid = T.OwnershipGuard(reg, 7)
    group = _Chat(-100500)
    seen = []

    async def handler(ev, data):
        seen.append(ev)
        return "handled"

    async def go():
        bot = _Bot()
        assert await guard_main(handler, _event(group, "left", "member"), {"bot": bot}) == "handled"   # الأول يملكها
        assert await guard_kid(handler, _event(group, "left", "member"), {"bot": bot}) is None          # الثاني يغادر
        assert bot.left == [-100500] and len(seen) == 1
        # الأول يعود للمجموعة بعد خروجه: يبقى هو المالك
        assert await guard_main(handler, _event(group, "left", "administrator"), {"bot": bot}) == "handled"
    asyncio.run(go())


def test_leaving_events_and_channels_are_not_intercepted(reg):
    guard = T.OwnershipGuard(reg, 7)
    seen = []

    async def handler(ev, data):
        seen.append(ev)

    async def go():
        bot = _Bot()
        await guard(handler, _event(_Chat(-100600), "member", "left"), {"bot": bot})          # خروج
        await guard(handler, _event(_Chat(-100601, "channel"), "left", "administrator"), {"bot": bot})   # قناة
        assert bot.left == [] and len(seen) == 2
    asyncio.run(go())
