"""تشغيل البوتات الفرعية داخل العملية نفسها + التسجيل + ملكية المجموعات (المرحلتان 3 و4).

- كل بوت فرعي له: توكن مشفّر في السجل، وقاعدة بيانات خاصة، وحالة ألعاب خاصة، وموزّع خاص.
- المالك هو الأدمن الوحيد لبوته. لا صلاحيات عامة لأي أحد آخر.
- ملكية المجموعات: أول بوت يُضاف إلى مجموعة يملكها، والبوت الثاني يغادرها تلقائيًا.
- التحقق من الاشتراك يكون بطلب داخلي إلى البوت الرئيسي (انظر docs/MULTI_BOT_PLAN.md).
"""
from __future__ import annotations

import asyncio
import dataclasses
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from .config import Settings
from .ctx import Ctx
from .db import DB
from .registry import MAIN_TENANT, Registry, RegistryError
from .state import GameState

log = logging.getLogger(__name__)


@dataclass
class Handle:
    tenant_id: int
    bot: Bot
    db: DB
    ctx: Ctx
    dp: Dispatcher
    task: asyncio.Task | None = None


class RelayUnavailable(Exception):
    """البوت الرئيسي غير متاح للتحقق من الاشتراك الآن."""


@dataclass
class Runtime:
    handles: dict[int, Handle] = field(default_factory=dict)
    registry: Registry | None = None
    base: Settings | None = None
    main_bot: Bot | None = None

    def children(self) -> list[Handle]:
        return [h for tid, h in sorted(self.handles.items()) if tid != MAIN_TENANT]


RUNTIME = Runtime()


def child_settings(base: Settings, token: str, db_path: str, owner_user_id: int) -> Settings:
    """إعدادات البوت الفرعي: قاعدته ومالكه وتوكنه، ويرث الباقي من الرئيسي (القناة الإلزامية وغيرها)."""
    return dataclasses.replace(base, token=token, db_path=db_path, admin_ids=(owner_user_id,), backup_chat="")


def build_child(base: Settings, registry: Registry, tenant_id: int) -> Handle:
    """يبني البوت الفرعي (بلا تشغيل الاستقبال): بوت وقاعدة وحالة وموزّع منفصلة."""
    from .app import build_dispatcher   # استيراد متأخر لتفادي دورة الاستيراد

    info = registry.tenant(tenant_id)
    if info is None or info["status"] != "active":
        raise RegistryError("المستأجر غير موجود أو موقوف")
    token = registry.token(tenant_id)
    s = child_settings(base, token, info["db_path"], info["owner_user_id"] or 0)
    Path(info["db_path"]).parent.mkdir(parents=True, exist_ok=True)
    db = DB(info["db_path"])
    db.load_questions(base.questions_path)
    ctx = Ctx(s, db, state=GameState(), tenant_id=tenant_id)
    dp = build_dispatcher(ctx)
    attach_ownership(dp, registry, tenant_id)
    handle = Handle(tenant_id=tenant_id, bot=Bot(token), db=db, ctx=ctx, dp=dp)
    RUNTIME.handles[tenant_id] = handle
    return handle


async def relay_member(channel: str, uid: int):
    """التحقق من عضوية uid في القناة عبر البوت الرئيسي (طلب داخلي، لا رسالة تليجرام بين البوتات)."""
    main = RUNTIME.main_bot
    if main is None:
        raise RelayUnavailable("البوت الرئيسي غير جاهز")
    return await main.get_chat_member(channel, uid)


def start_polling(handle: Handle) -> None:
    """يشغّل استقبال التحديثات في مهمة خلفية، ويحفظها في المقبض."""
    async def _run():
        await handle.dp.start_polling(handle.bot, allowed_updates=handle.dp.resolve_used_update_types(),
                                      handle_signals=False)
    handle.task = asyncio.create_task(_run())


async def start_all_children(base: Settings, registry: Registry) -> int:
    """يشغّل كل البوتات الفرعية النشطة عند بدء التشغيل. فشل بوت لا يوقف الباقي."""
    RUNTIME.registry, RUNTIME.base = registry, base
    started = 0
    for row in registry.active_children():
        try:
            handle = build_child(base, registry, row["id"])
            start_polling(handle)
            started += 1
        except Exception as e:  # noqa: BLE001
            log.warning("child tenant %s not started: %s", row["id"], type(e).__name__)
    return started


# ── ملكية المجموعات ───────────────────────────────────────

class OwnershipGuard(BaseMiddleware):
    """يعمل قبل أي معالج لتغيّر عضوية البوت: إن أُضيف إلى مجموعة يملكها بوت آخر يغادرها.

    وسيط خارجي وليس معالجًا، لأن تليجرام/aiogram يشغّل أول معالج مطابق فقط، ومعالج المجموعات
    الحالي يلتقط كل تغيّرات العضوية.
    """

    def __init__(self, registry: Registry, tenant_id: int):
        self.registry, self.tenant_id = registry, tenant_id

    async def __call__(self, handler, event, data):
        old = getattr(getattr(event, "old_chat_member", None), "status", None)
        new = getattr(getattr(event, "new_chat_member", None), "status", None)
        chat = event.chat
        if chat.type in ("group", "supergroup") and old in ("left", "kicked") and new in ("member", "administrator"):
            owner = self.registry.claim_chat(chat.id, self.tenant_id)
            if owner != self.tenant_id:
                try:
                    await data["bot"].leave_chat(chat.id)
                except TelegramAPIError as e:
                    log.warning("leave %s failed: %s", chat.id, type(e).__name__)
                return None
        return await handler(event, data)


def attach_ownership(dp: Dispatcher, registry: Registry, tenant_id: int) -> None:
    dp.my_chat_member.outer_middleware(OwnershipGuard(registry, tenant_id))


# ── التسجيل: البوت الفرعي يُضاف بتوكنه ─────────────────

class NewBot(StatesGroup):
    token = State()


def build_registration_router(registration: "Registration") -> Router:
    """أمر /newbot في الخاص مع البوت الرئيسي فقط."""
    r = Router(name="tenants")
    r.message.filter(F.chat.type == "private")

    @r.message(Command("newbot"))
    async def cmd_newbot(m: Message, state: FSMContext):
        await state.set_state(NewBot.token)
        await m.answer("🤖 أرسل توكن بوتك الجديد من BotFather.\n"
                       "⚠️ لا تشاركه مع أحد. بعد الإرسال احذف رسالة التوكن من المحادثة.\n"
                       "للإلغاء: /cancel")

    @r.message(Command("cancel"), NewBot.token)
    async def cancel(m: Message, state: FSMContext):
        await state.clear()
        await m.answer("تم الإلغاء.")

    @r.message(NewBot.token, F.text)
    async def got_token(m: Message, state: FSMContext):
        token = (m.text or "").strip()
        await state.clear()                                  # التوكن لا يبقى في الحالة
        try:
            tid = await registration.register(m.from_user.id, token)
        except RegistryError as e:
            await m.answer(f"❌ {e}")
            return
        try:
            handle = build_child(registration.base, registration.registry, tid)
        except RegistryError as e:
            await m.answer(f"❌ {e}")
            return
        start_polling(handle)
        await m.answer("✅ تم تسجيل بوتك وتشغيله. افتحه وأرسل /start، وأنت أدمنه.")

    return r


class Registration:
    """يتحقق من توكن البوت الجديد ويسجّله. اختبارات التوكن تُحقن هنا."""

    def __init__(self, registry: Registry, base: Settings,
                 validate: Callable[[str], "asyncio.Future"] | None = None):
        self.registry, self.base = registry, base
        self.validate = validate or _validate_token

    async def register(self, owner_user_id: int, token: str) -> int:
        """يرجع معرّف المستأجر الجديد، أو يرفع RegistryError برسالة مقروءة بلا توكن."""
        if not token or ":" not in token:
            raise RegistryError("التوكن غير صحيح")
        try:
            bot_id, username = await self.validate(token)
        except Exception as e:  # noqa: BLE001
            raise RegistryError("تعذّر التحقق من التوكن. تأكد أنه صحيح") from e
        main = self.registry.tenant(MAIN_TENANT)
        if main and bot_id == main["bot_id"]:
            raise RegistryError("هذا هو البوت الرئيسي نفسه")
        folder = self.registry.path.parent / "tenants"          # قواعد البوتات الفرعية في مجلد خاص
        folder.mkdir(exist_ok=True)
        db_path = str(folder / f"{bot_id}.db")
        tid = self.registry.add_tenant(owner_user_id, bot_id, username, token, db_path)
        return tid


async def _validate_token(token: str) -> tuple[int, str | None]:
    bot = Bot(token)
    try:
        me = await bot.get_me()
        return me.id, me.username
    finally:
        await bot.session.close()
