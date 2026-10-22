#!/usr/bin/env bash
# Ежедневный бэкап: cron хоста → `15 4 * * * /opt/bu-site/deploy/backup.sh >> /var/log/bu-backup.log 2>&1`
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
KEEP_DAYS="${KEEP_DAYS:-14}"
DIR="${BACKUP_DIR:-/opt/bu-site/backups}"
mkdir -p "$DIR"
FILE="$DIR/bu-$(date +%Y%m%d-%H%M).sql.gz"
docker compose --env-file .env exec -T postgres pg_dump -U bu -d bu --no-owner | gzip > "$FILE"
[ -s "$FILE" ] || { echo "empty dump" >&2; exit 1; }
# Обложки новостей из Telegram: исходные ссылки CDN временные, второй раз их не скачать.
MEDIA="$DIR/bu-media-$(date +%Y%m%d-%H%M).tar.gz"
docker compose --env-file .env exec -T worker tar -C /data/media -czf - . > "$MEDIA"
find "$DIR" -name 'bu-*.sql.gz' -mtime +"$KEEP_DAYS" -delete
find "$DIR" -name 'bu-media-*.tar.gz' -mtime +"$KEEP_DAYS" -delete
if [ -n "${S3_BUCKET:-}" ]; then
  docker run --rm -v "$DIR:/backups:ro" \
    -e AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" -e AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
    amazon/aws-cli:2.17.0 --endpoint-url "$S3_ENDPOINT" s3 cp "/backups/$(basename "$FILE")" "s3://$S3_BUCKET/db/"
  docker run --rm -v "$DIR:/backups:ro" \
    -e AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" -e AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
    amazon/aws-cli:2.17.0 --endpoint-url "$S3_ENDPOINT" s3 cp "/backups/$(basename "$MEDIA")" "s3://$S3_BUCKET/media/"
fi
echo "backup ok: $FILE"
