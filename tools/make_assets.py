"""يولّد بانرات الترحيب assets/banner.jpg (عربي) و assets/banner_en.jpg (إنجليزي) بأسلوب المانغا.
شغّله بعد أي تعديل على الرسم:  python tools/make_assets.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from otaku_bot import card  # noqa: E402

for lang, name in (("ar", "banner.jpg"), ("en", "banner_en.jpg")):
    png = card.make_banner(lang)
    (ROOT / "assets" / name).write_bytes(png)
    print(name, len(png) // 1024, "KB")
