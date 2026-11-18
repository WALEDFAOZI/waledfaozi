"""سياق مشترك: الإعدادات (من .env أو معدَّلة من لوحة الأدمن) + قاعدة البيانات."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .config import Settings
from .db import DB


@dataclass
class Ctx:
    settings: Settings
    db: DB
    rng: random.Random = field(default_factory=random.Random)
    claim_code: str | None = None   # كود يظهر في سجل التشغيل لتفعيل المالك عبر /claim
    tasks: list = field(default_factory=list)   # مهام الخلفية (رسائل جماعية، نسخ احتياطي)

    def timer(self) -> int:
        return int(self.db.get_setting("timer_seconds", str(self.settings.timer_seconds)))

    def cooldown(self) -> int:
        return int(self.db.get_setting("cooldown_minutes", str(self.settings.cooldown_minutes)))

    def channel(self) -> str:
        return self.db.get_setting("required_channel", self.settings.required_channel) or ""

    def report_threshold(self) -> int:
        return int(self.db.get_setting("report_threshold", "3"))

    def reports_per_day(self) -> int:
        return int(self.db.get_setting("reports_per_day", "10"))

    def is_admin(self, tg_id: int) -> bool:
        return tg_id in self.settings.admin_ids or self.db.is_admin(tg_id)

    def admin_ids(self) -> list[int]:
        return sorted(set(self.settings.admin_ids) | set(self.db.admin_ids()))

    def is_owner(self, tg_id: int) -> bool:
        return tg_id in self.settings.admin_ids or self.db.is_owner(tg_id)

    def owner_ids(self) -> list[int]:
        return sorted(set(self.settings.admin_ids) | {i for i in self.db.admin_ids() if self.db.is_owner(i)})
