import asyncio
import logging
import os
import sys
import time

from .config import ROOT, Settings


def load_dotenv(path=ROOT / ".env") -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def check(settings: Settings) -> int:
    """فحص بدون توكن: يحمّل الأسئلة ويطبع إحصائيات البنك."""
    from collections import Counter

    from .db import DB
    db = DB(":memory:")
    n = db.load_questions(settings.questions_path)
    qs = db.all_questions()
    lv = Counter(q.level for q in qs)
    cat = Counter(q.category for q in qs)
    print(f"✅ {n} سؤالًا")
    print("المستويات:", dict(sorted(lv.items())))
    print("التصنيفات:", dict(cat))
    print(f"🇬🇧 بالإنجليزية: {sum(1 for q in qs if q.q_en)} · 🖼 بصور: {sum(1 for q in qs if q.image)}")
    bad = [lvl for lvl in range(1, 11) if lv[lvl] < 5]
    if bad:
        print("❌ مستويات أقل من 5 أسئلة:", bad)
        return 1
    thin = [lvl for lvl in range(1, 11) if lv[lvl] < 40]
    print(f"ℹ️ مستويات أقل من 40 سؤالًا (ستتكرر الأسئلة سريعًا): {thin}")
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    settings = Settings.from_env()
    if "--check" in sys.argv:
        sys.exit(check(settings))
    if not settings.token:
        sys.exit("BOT_TOKEN غير موجود. ضعه في ملف .env أو كمتغير بيئة (انظر .env.example).")
    from .app import run
    log = logging.getLogger("supervisor")
    delay = 5
    while True:                    # أي انهيار غير متوقع (شبكة/تليجرام) = إعادة تشغيل ذاتية بدل التوقف
        try:
            asyncio.run(run(settings))
            return
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:  # noqa: BLE001
            log.exception("bot crashed, restarting in %ds", delay)
            time.sleep(delay)
            delay = min(60, delay * 2)


if __name__ == "__main__":
    main()
