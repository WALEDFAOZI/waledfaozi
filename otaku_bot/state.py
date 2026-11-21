"""الحالة المشتركة للألعاب والذاكرة المؤقتة، مجمّعة في كائن واحد.

المرحلة 0 من خطة تعدد البوتات: كل القواميس التي كانت معرّفة على مستوى الوحدات صارت
تُقرأ من هذا الكائن. المستأجر الرئيسي يستخدم STATE الافتراضي، والبوتات الفرعية
ستحصل على نسخها الخاصة في المراحل اللاحقة.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GameState:
    mafia_games: dict[int, Any] = field(default_factory=dict)
    mafia_cooldown: dict[int, float] = field(default_factory=dict)
    spy_games: dict[int, Any] = field(default_factory=dict)
    spy_cooldown: dict[int, float] = field(default_factory=dict)
    swaps: dict[int, dict] = field(default_factory=dict)
    online_queue: dict[str, list] = field(default_factory=dict)
    online_matches: dict[int, Any] = field(default_factory=dict)
    online_user_match: dict[int, int] = field(default_factory=dict)
    chat_info: dict[int, tuple] = field(default_factory=dict)
    me_name: dict[str, str] = field(default_factory=dict)
    channel: dict[str, Any] = field(default_factory=lambda: {"get": lambda: ""})


STATE = GameState()   # المستأجر الرئيسي
