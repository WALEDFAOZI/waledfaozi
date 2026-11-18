"""يولّد data/names_ar.json من tools/names_data.py.   python tools/build_names.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from names_data import NAMES, OPTION_ONLY  # noqa: E402

out = Path(__file__).resolve().parent.parent / "data" / "names_ar.json"
out.write_text(json.dumps({"names": NAMES, "option_only": OPTION_ONLY}, ensure_ascii=False, indent=0), encoding="utf-8")
print(len(NAMES), "names ->", out)
