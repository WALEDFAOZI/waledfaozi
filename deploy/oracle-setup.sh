#!/usr/bin/env bash
# يثبّت Docker ويشغّل البوت على سيرفر Ubuntu (Oracle Always Free أو أي VPS).
# الاستخدام على السيرفر:   bash oracle-setup.sh
set -euo pipefail

REPO="${REPO:-https://github.com/WALEDFAOZI/waledfaozi.git}"
BRANCH="${BRANCH:-ccr-64677850-l7tk6n}"
DIR="$HOME/otaku-bot"

if ! command -v docker >/dev/null; then
  echo ">> تثبيت Docker..."
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

if [ -d "$DIR/.git" ]; then
  echo ">> تحديث الكود..."
  git -C "$DIR" fetch origin "$BRANCH" && git -C "$DIR" checkout "$BRANCH" && git -C "$DIR" pull --ff-only origin "$BRANCH"
else
  echo ">> سحب الكود..."   # مستودع خاص؟ استخدم REPO=https://<USER>:<TOKEN>@github.com/WALEDFAOZI/waledfaozi.git
  git clone --branch "$BRANCH" "$REPO" "$DIR"
fi
cd "$DIR"

if [ ! -f .env ]; then
  read -rsp "الصق BOT_TOKEN (لن يظهر وأنت تكتب): " TOKEN; echo
  printf 'BOT_TOKEN=%s\n' "$TOKEN" > .env
  chmod 600 .env
fi

sudo docker compose up -d --build
echo "✅ تم. السجلات:  cd $DIR && sudo docker compose logs -f bot"
