import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LEVELS = 10
PER_LEVEL = 5            # 10 مستويات × 5 = 50 سؤال
CALIBRATION_WEIGHT = 20  # وزن رأيك (الصعوبة الأساسية) مقابل الإجابات الحقيقية

CATEGORY_LABELS_EN = {
    "anime": "General anime", "characters": "Characters", "studios": "Studios",
    "creators": "Creators & authors", "music": "Music", "culture": "Otaku culture",
    "history": "Anime history", "manga": "Manga", "images": "Character pics",
}

TITLES_EN = [
    (0.0, "Noob 🍼"), (2.0, "Casual viewer 📺"), (4.0, "Otaku 🎌"),
    (6.0, "Seasoned Otaku ⚔️"), (8.0, "Sensei 🥋"), (9.5, "King of Otaku 👑"),
]

CATEGORY_LABELS = {
    "images": "شخصيات بالصور",
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
    backup_chat: str = ""        # قناة/مجموعة خاصة تُحفظ فيها النسخ ويُستعاد منها التقدم تلقائيًا (BACKUP_CHAT_ID)
    backup_hours: int = 6        # كل كم ساعة تُرسل نسخة إلى backup_chat

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
            backup_chat=os.getenv("BACKUP_CHAT_ID", "").strip(),
            backup_hours=max(1, int(os.getenv("BACKUP_HOURS", "6") or 6)),
        )
