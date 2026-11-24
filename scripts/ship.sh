#!/usr/bin/env bash
# يشغّل الاختبارات بالتوازي، يرفع رقم الإصدار، يعمل commit و push، ثم يبني الملف المضغوط.
# الاستخدام: scripts/ship.sh "وصف التعديل"        (يرفع الإصدار تلقائياً)
#            scripts/ship.sh "وصف التعديل" 2026-11-25-aa   (إصدار محدد)
#            scripts/ship.sh --quick "وصف"        (بدون اختبارات كاملة: للتجربة فقط)
set -euo pipefail
cd "$(dirname "$0")/.."

QUICK=0
if [[ "${1:-}" == "--quick" ]]; then QUICK=1; shift; fi
MSG="${1:?اكتب وصف التعديل}"
NEW="${2:-}"

CUR=$(python -c "import re;print(re.search(r'VERSION = \"([^\"]+)\"', open('otaku_bot/__init__.py').read()).group(1))")
if [[ -z "$NEW" ]]; then
  NEW=$(python - "$CUR" <<'PY'
import sys
base, suffix = sys.argv[1].rsplit("-", 1)
def nxt(s):
    n = 0
    for ch in s: n = n * 26 + (ord(ch) - 96)
    n += 1
    out = ""
    while n: n, r = divmod(n - 1, 26); out = chr(97 + r) + out
    return out
print(f"{base}-{nxt(suffix)}")
PY
)
fi
echo "الإصدار: $CUR -> $NEW"
sed -i "s/VERSION = \"$CUR\"/VERSION = \"$NEW\"/" otaku_bot/__init__.py

if [[ $QUICK -eq 0 ]]; then
  python -m pytest -q -n 4
fi

git add -A otaku_bot tests data scripts
git commit -q -m "$MSG

Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KGDmqpKPFT3eHbpsqXLyf4"
git push -u origin ccr-64677850-l7tk6n 2>&1 | tail -1

P=/tmp/claude-0/-home-user-waledfaozi/3126f8ae-0848-5c0c-910f-3af76479c888/scratchpad/pkg
rm -rf "$P" && mkdir -p "$P"
cp -r otaku_bot data assets main.py requirements.txt .env "$P/"
find "$P" -name __pycache__ -prune -exec rm -rf {} +
rm -f otaku-bot-with-token.zip
(cd "$P" && zip -qr "$OLDPWD/otaku-bot-with-token.zip" .)
echo "جاهز: $(pwd)/otaku-bot-with-token.zip ($(unzip -p otaku-bot-with-token.zip otaku_bot/__init__.py | grep VERSION))"
