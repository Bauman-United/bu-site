#!/usr/bin/env bash
# Восстановление: ./deploy/restore.sh /opt/bu-site/backups/bu-YYYYMMDD-HHMM.sql.gz [db]
# По умолчанию восстанавливает в базу bu (ОСТОРОЖНО: перезаписывает данные). Для проверки — укажите другую базу.
set -euo pipefail
cd "$(dirname "$0")"
FILE="$1"; DB="${2:-bu}"
[ -f "$FILE" ] || { echo "no file $FILE" >&2; exit 1; }
if [ "$DB" = "bu" ]; then
  read -r -p "Перезаписать рабочую базу bu? Напишите yes: " ok; [ "$ok" = "yes" ] || exit 1
  docker compose --env-file .env stop api worker bu-web
fi
docker compose --env-file .env exec -T postgres psql -U bu -d postgres -c "DROP DATABASE IF EXISTS \"$DB\" WITH (FORCE)" -c "CREATE DATABASE \"$DB\" OWNER bu"
gunzip -c "$FILE" | docker compose --env-file .env exec -T postgres psql -q -U bu -d "$DB"
[ "$DB" = "bu" ] && docker compose --env-file .env up -d api worker bu-web
echo "restored $FILE into $DB"
