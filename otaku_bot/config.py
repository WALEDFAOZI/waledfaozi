import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LEVELS = 10
PER_LEVEL = 5            # 10 مستويات × 5 = 50 سؤال
CALIBRATION_WEIGHT = 20  # وزن رأيك (الصعوبة الأساسية) مقابل الإجابات الحقيقية

CATEGORY_LABELS = {
    "anime": "أنمي عام",
    "characters": "شخصيات",
    "studios": "استوديوهات",
    "creators": "صنّاع ومؤلفون",
    "music": "موسيقى",
    "culture": "ثقافة أوتاكو",
    "history": "تاريخ الأنمي",
    "manga": "مانغا",
}

# (الحد الأدنى للتقييم, اللقب) — مرتبة تصاعديًا
TITLES = [
    (0.0, "نوب / ما شفت أنمي 🍼"),
    (2.0, "مشاهد عادي 📺"),
    (4.0, "أوتاكو 🎌"),
    (6.0, "أوتاكو متمرس ⚔️"),
    (8.0, "سينسي 🥋"),
    (9.5, "ملك الأوتاكو 👑"),
]


@dataclass(frozen=True)
class Settings:
    token: str
    db_path: str
    questions_path: str
    timer_seconds: int       # 0 = بدون مؤقت
    cooldown_minutes: int    # الانتظار بين اختبارين مكتملين، 0 = بدون
    admin_ids: tuple[int, ...]
    required_channel: str = ""   # مثل @Anime1Galaxy ، فارغ = بدون اشتراك إجباري

    @staticmethod
    def from_env() -> "Settings":
        admins = tuple(
            int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x
        )
        return Settings(
            token=os.getenv("BOT_TOKEN", "").strip(),
            db_path=os.getenv("DB_PATH", str(ROOT / "otaku.db")),
            questions_path=os.getenv("QUESTIONS_PATH", str(ROOT / "data" / "questions.json")),
            timer_seconds=int(os.getenv("TIMER_SECONDS", "30")),
            cooldown_minutes=int(os.getenv("COOLDOWN_MINUTES", "30")),
            admin_ids=admins,
            required_channel=os.getenv("REQUIRED_CHANNEL", "@Anime1Galaxy").strip(),
        )
