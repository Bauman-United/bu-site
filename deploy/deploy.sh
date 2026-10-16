#!/usr/bin/env bash
# Обновление стека на сервере до тега: ./deploy/deploy.sh <tag>
set -euo pipefail
cd "$(dirname "$0")"
TAG="${1:-latest}"
sed -i "s/^TAG=.*/TAG=$TAG/" .env
docker compose --env-file .env pull
docker compose --env-file .env up -d --remove-orphans
docker image prune -f >/dev/null
set -a; . ./.env; set +a
if [ "${NGINX_MODE:-http}" = "https" ]; then BASE="https://$SITE_DOMAIN"; else BASE="http://localhost"; fi
./smoke.sh "$BASE" || { echo "smoke failed after deploy $TAG" >&2; exit 1; }
