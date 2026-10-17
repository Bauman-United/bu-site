#!/usr/bin/env bash
# Обновление стека на сервере до тега: ./deploy/deploy.sh <tag>
set -euo pipefail
cd "$(dirname "$0")"
TAG="${1:-latest}"
sed -i "s/^TAG=.*/TAG=$TAG/" .env
# .env грузим в shell только после compose: bash снимает кавычки в JSON-значениях
# (BU_LFL_TOURNAMENT_IDS), а переменные окружения у compose приоритетнее .env.
if grep -qx 'NGINX_MODE=edge' .env; then
  # Сеть общего Caddy; создаётся один раз, повторный вызов — no-op.
  docker network inspect edge >/dev/null 2>&1 || docker network create edge >/dev/null
fi
docker compose --env-file .env pull
docker compose --env-file .env up -d --remove-orphans
docker image prune -f >/dev/null
set -a; . ./.env; set +a
if [ "${NGINX_MODE:-http}" = "edge" ]; then
  : "${CADDY_SITES_DIR:?set CADDY_SITES_DIR in deploy/.env}" "${CADDY_CONTAINER:?set CADDY_CONTAINER in deploy/.env}"
  site="$(sed "s/\${SITE_DOMAIN}/$SITE_DOMAIN/" caddy/site.caddy.template)"
  case "$SITE_DOMAIN" in
    *.sslip.io) ;;
    *) site="$site"$'\n\n'"www.$SITE_DOMAIN {"$'\n\t'"redir https://$SITE_DOMAIN{uri} permanent"$'\n'"}" ;;
  esac
  if [ "$site" != "$(cat "$CADDY_SITES_DIR/bu-site.caddy" 2>/dev/null)" ]; then
    printf '%s\n' "$site" > "$CADDY_SITES_DIR/bu-site.caddy"
    docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
  fi
fi
case "${NGINX_MODE:-http}" in
  https|edge) BASE="https://$SITE_DOMAIN" ;;
  *) BASE="http://localhost" ;;
esac
./smoke.sh "$BASE" || { echo "smoke failed after deploy $TAG" >&2; exit 1; }
