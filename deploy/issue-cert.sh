#!/usr/bin/env bash
# Первый выпуск сертификата Let's Encrypt (nginx в режиме http уже запущен, DNS домена указывает на сервер).
# Использование: ./deploy/issue-cert.sh example.ru admin@example.ru
set -euo pipefail
DOMAIN="$1"; EMAIL="$2"
cd "$(dirname "$0")"
docker compose --env-file .env run --rm --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot -d "$DOMAIN" -d "www.$DOMAIN" \
  --email "$EMAIL" --agree-tos --no-eff-email
echo "Сертификат выпущен. Теперь в deploy/.env: NGINX_MODE=https, SITE_DOMAIN=$DOMAIN, BU_SITE_URL=https://$DOMAIN, BU_NOINDEX=0"
echo "и выполните: docker compose --env-file .env up -d nginx bu-web worker"
