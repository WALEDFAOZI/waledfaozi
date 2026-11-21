"""السجل المركزي للبوتات (المرحلة 1 من خطة تعدد البوتات).

- المستأجر 0 هو البوت الرئيسي، وقاعدته هي قاعدة البيانات الحالية (لا نقل للبيانات).
- التوكنات مشفّرة بمفتاح Fernet من REGISTRY_KEY، ولا تُخزَّن أو تُعرض بصيغة واضحة.
- بوت واحد لكل شخص: قيد فريد على owner_user_id.
- ملكية الدردشات: أول بوت يطالب بالدردشة يملكها، والطلب ذري بمفتاح أساسي على chat_id.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from pathlib import Path

try:  # المكتبة اختيارية: البوت يعمل بدونها ما دام السجل غير مفعّل
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:  # pragma: no cover
    Fernet = None
    InvalidToken = Exception

log = logging.getLogger(__name__)

MAIN_TENANT = 0

SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (
    id            INTEGER PRIMARY KEY,
    owner_user_id INTEGER UNIQUE,              -- بوت واحد لكل شخص؛ NULL للبوت الرئيسي
    bot_id        INTEGER NOT NULL UNIQUE,
    bot_username  TEXT,
    token_enc     BLOB    NOT NULL,
    db_path       TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'active',
    created_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_owner (
    chat_id    INTEGER PRIMARY KEY,
    tenant_id  INTEGER NOT NULL REFERENCES tenants(id),
    claimed_at INTEGER NOT NULL
);
"""


class RegistryError(Exception):
    """خطأ مقروء للمستخدم لا يحتوي على أي توكن."""


def generate_key() -> str:
    if Fernet is None:
        raise RegistryError("مكتبة cryptography غير مثبتة (pip install cryptography)")
    return Fernet.generate_key().decode()


class Registry:
    def __init__(self, path: str | Path, key: str):
        if Fernet is None:
            raise RegistryError("مكتبة cryptography غير مثبتة (pip install cryptography)")
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except (ValueError, TypeError) as e:
            raise RegistryError("REGISTRY_KEY غير صالح (أنشئه بـ generate_key)") from e
        self.path = Path(path)
        self._lock = threading.Lock()
        self._con = sqlite3.connect(str(path), check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._con.close()

    # ── التشفير ───────────────────────────────────────────
    def _enc(self, token: str) -> bytes:
        return self._fernet.encrypt(token.encode())

    def _dec(self, blob: bytes) -> str:
        try:
            return self._fernet.decrypt(bytes(blob)).decode()
        except InvalidToken as e:
            raise RegistryError("تعذّر فك تشفير توكن: REGISTRY_KEY لا يطابق السجل") from e

    # ── المستأجرون ────────────────────────────────────────
    def register_main(self, bot_id: int, username: str | None, token: str, db_path: str) -> None:
        """يسجّل البوت الرئيسي كمستأجر 0، ويحدّث توكنه إن تغيّر (idempotent)."""
        with self._lock, self._con:
            self._con.execute(
                """INSERT INTO tenants (id, owner_user_id, bot_id, bot_username, token_enc, db_path, status, created_at)
                   VALUES (?, NULL, ?, ?, ?, ?, 'active', ?)
                   ON CONFLICT(id) DO UPDATE SET bot_id=excluded.bot_id, bot_username=excluded.bot_username,
                                                 token_enc=excluded.token_enc, db_path=excluded.db_path""",
                (MAIN_TENANT, bot_id, username, self._enc(token), str(db_path), int(time.time())))

    def add_tenant(self, owner_user_id: int, bot_id: int, username: str | None, token: str, db_path: str) -> int:
        """يضيف بوتًا فرعيًا. يرفع RegistryError إن كان للمالك بوت، أو التوكن مسجّل سابقًا."""
        with self._lock, self._con:
            try:
                cur = self._con.execute(
                    """INSERT INTO tenants (owner_user_id, bot_id, bot_username, token_enc, db_path, status, created_at)
                       VALUES (?, ?, ?, ?, ?, 'active', ?)""",
                    (owner_user_id, bot_id, username, self._enc(token), str(db_path), int(time.time())))
            except sqlite3.IntegrityError as e:
                raise RegistryError("لهذا الحساب بوت مسجّل بالفعل، أو التوكن مستخدم سابقًا") from e
            return int(cur.lastrowid)

    def tenant(self, tenant_id: int) -> dict | None:
        row = self._con.execute(
            "SELECT id, owner_user_id, bot_id, bot_username, db_path, status, created_at FROM tenants WHERE id=?",
            (tenant_id,)).fetchone()
        return dict(row) if row else None

    def token(self, tenant_id: int) -> str:
        row = self._con.execute("SELECT token_enc FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if row is None:
            raise RegistryError("مستأجر غير موجود")
        return self._dec(row["token_enc"])

    def active_children(self) -> list[dict]:
        """البوتات الفرعية النشطة (كل المستأجرين ما عدا الرئيسي)."""
        rows = self._con.execute(
            "SELECT id, owner_user_id, bot_id, bot_username, db_path FROM tenants WHERE id<>? AND status='active' ORDER BY id",
            (MAIN_TENANT,)).fetchall()
        return [dict(r) for r in rows]

    def db_path(self, tenant_id: int) -> str | None:
        row = self._con.execute("SELECT db_path FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        return row["db_path"] if row else None

    # ── ملكية الدردشات ───────────────────────────────────
    def claim_chat(self, chat_id: int, tenant_id: int) -> int:
        """يطالب بالدردشة لصالح المستأجر. يرجع المستأجر المالك بعد الطلب (قد يكون غيره)."""
        with self._lock, self._con:
            self._con.execute(
                "INSERT OR IGNORE INTO chat_owner (chat_id, tenant_id, claimed_at) VALUES (?, ?, ?)",
                (chat_id, tenant_id, int(time.time())))
            row = self._con.execute("SELECT tenant_id FROM chat_owner WHERE chat_id=?", (chat_id,)).fetchone()
            return int(row["tenant_id"])

    def chat_owner(self, chat_id: int) -> int | None:
        row = self._con.execute("SELECT tenant_id FROM chat_owner WHERE chat_id=?", (chat_id,)).fetchone()
        return int(row["tenant_id"]) if row else None


def open_configured(settings) -> "Registry | None":
    """يفتح السجل إن كان REGISTRY_KEY مضبوطًا، وإلا يرجع None. لا يوقف البوت عند الخطأ."""
    key = getattr(settings, "registry_key", "")
    if not key:
        return None
    try:
        return Registry(settings.registry_path, key)
    except RegistryError as e:
        log.warning("registry disabled: %s", e)
        return None


async def register_main(bot, settings) -> None:
    """يسجّل البوت الرئيسي عند التشغيل إن وُجد REGISTRY_KEY. لا يوقف البوت إن فشل التسجيل."""
    key = getattr(settings, "registry_key", "")
    if not key:
        return
    try:
        me = await bot.get_me()
        reg = Registry(settings.registry_path, key)
        try:
            reg.register_main(me.id, me.username, settings.token, settings.db_path)
        finally:
            reg.close()
        log.info("registry: main bot registered as tenant %d", MAIN_TENANT)
    except Exception as e:  # noqa: BLE001 - التسجيل لا يجب أن يوقف البوت أبدًا؛ الرسالة لا تحتوي التوكن
        log.warning("registry: main bot not registered: %s", type(e).__name__)
