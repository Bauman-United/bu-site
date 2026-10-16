# План 3: деплой на Timeweb VPS, CI/CD, бэкапы

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Всё, что нужно в репозитории, чтобы поднять сайт на одном VPS одной командой, обновлять его по пушу в `main`, получать HTTPS после покупки домена и не терять данные.

**Architecture:** Два образа — `bu-python` (core + worker + api + content + миграции) и `bu-web` (Next.js standalone). `deploy/docker-compose.yml`: `postgres`, одноразовый `migrate`, `api`, `worker` (синк content → планировщик), `web`, `nginx` (режим `http` до домена, `https` после), `certbot`. GitHub Actions: CI (Python, web, e2e), ежедневный canary живого парсинга, деплой (GHCR → ssh → `docker compose pull && up -d`), включаемый переменной репозитория. Бэкап — `pg_dump` по cron хоста в Timeweb S3.

**Tech Stack:** Docker, docker compose v2, nginx 1.27, certbot, GitHub Actions, GHCR, PostgreSQL 16, Timeweb S3 (S3-совместимое API).

**Spec:** `docs/superpowers/specs/2026-10-15-bauman-united-site-design.md` (раздел 12, 13, 7.3)

## Global Constraints

- Переменные окружения сайта — с префиксом `BU_` (правило плана 1); секреты только в `deploy/.env` на сервере и GitHub Secrets, в репозитории — только `deploy/.env.example`.
- До покупки домена: `NGINX_MODE=http`, `BU_NOINDEX=1`, `BU_SITE_URL=http://<IP>`. После: `NGINX_MODE=https`, `SITE_DOMAIN=<домен>`, `BU_SITE_URL=https://<домен>`, `BU_NOINDEX=0`.
- Node в образах и CI — 22 LTS (`>=22.18`, правило плана 2); Python 3.12; uv.
- Деплой-воркфлоу ничего не делает, пока в репозитории не задана переменная `DEPLOY_ENABLED=true` (сервер и секреты настраивает человек).
- Наружу торчат только порты 80/443 (nginx); Postgres, API, web — только во внутренней сети compose.
- Никаких пушей/деплоев из этой работы — только файлы в репозитории и локальная проверка в Docker.

## Review Focus

1. Холодный старт на пустом сервере: `docker compose up -d` поднимает всё в правильном порядке (миграции до api/worker), без ручных шагов кроме `.env` — проверка в Task 2.
2. Перезапуск/повторный деплой не теряет данные БД (volume) и не плодит дубли (идемпотентный синк content) — проверка в Task 2.
3. API/worker не доступны снаружи; `/api/revalidate` доступен только с секретом — проверка в Task 2.
4. Бэкап восстанавливается в чистую БД — проверка в Task 4.
5. Переключение на HTTPS не ломает ACME-челлендж и даёт 301 http→https и www→apex — проверка в Task 3.

---

### Task 1: Docker-образы

**Files:**
- Create: `deploy/python.Dockerfile`, `deploy/web.Dockerfile`, `.dockerignore`, `web/.dockerignore`

- [ ] **Step 1: `.dockerignore` (корень)**

```
.git
.venv
**/__pycache__
**/.pytest_cache
.ruff_cache
.mypy_cache
.superpowers
snapshots
web
docs
design
deploy/.env
**/node_modules
```

`web/.dockerignore`:
```
node_modules
.next
test-results
playwright-report
tsconfig.tsbuildinfo
e2e
```

- [ ] **Step 2: `deploy/python.Dockerfile`**

```dockerfile
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY core/pyproject.toml core/pyproject.toml
COPY worker/pyproject.toml worker/pyproject.toml
COPY api/pyproject.toml api/pyproject.toml
COPY core/bu_core core/bu_core
COPY worker/bu_worker worker/bu_worker
COPY api/bu_api api/bu_api
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim
RUN useradd --create-home --uid 1000 bu
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY core/alembic.ini core/alembic.ini
COPY core/migrations core/migrations
COPY content content
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 BU_CONTENT_DIR=/app/content BU_SNAPSHOT_DIR=/data/snapshots
RUN mkdir -p /data/snapshots && chown -R bu /data
USER bu
EXPOSE 8000
CMD ["uvicorn", "bu_api.app:build", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

(Если тег `uv:0.8.22` недоступен — ближайший существующий 0.8.x, Ruling.)

- [ ] **Step 3: `deploy/web.Dockerfile`**

```dockerfile
FROM node:22-alpine AS build
RUN corepack enable
WORKDIR /web
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build && pnpm check:robots

FROM node:22-alpine
WORKDIR /web
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
RUN addgroup -S bu && adduser -S bu -G bu
COPY --from=build --chown=bu:bu /web/.next/standalone ./
COPY --from=build --chown=bu:bu /web/.next/static ./.next/static
COPY --from=build --chown=bu:bu /web/public ./public
USER bu
EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 4: Сборка и проверка**

Run (из корня):
```bash
docker build -f deploy/python.Dockerfile -t bu-python:local .
docker build -f deploy/web.Dockerfile -t bu-web:local .
docker run --rm bu-python:local python -c "import bu_api.app, bu_worker.runner; print('ok')"
docker run --rm bu-python:local alembic -c core/alembic.ini history | head -3
docker run --rm -e BU_API_URL=http://127.0.0.1:9 -p 3999:3000 -d --name bu-web-smoke bu-web:local && sleep 3 && curl -s -o /dev/null -w "%{http_code}\n" localhost:3999/robots.txt; docker rm -f bu-web-smoke
```
Expected: обе сборки успешны; `ok`; история миграций показывает `0002`; `robots.txt` → `200` (страницы с данными дадут 500 без API — это ожидаемо).

- [ ] **Step 5: Commit**

```bash
git add .dockerignore web/.dockerignore deploy/*.Dockerfile && git commit -m "build: docker images for python services and web"
```

---

### Task 2: docker-compose, nginx (http), env

**Files:**
- Create: `deploy/docker-compose.yml`, `deploy/.env.example`, `deploy/nginx/http/default.conf.template`, `deploy/nginx/common/proxy.conf`, `deploy/smoke.sh`
- Modify: `.gitignore` (`deploy/.env`)

- [ ] **Step 1: `deploy/.env.example`**

```bash
# Скопировать в deploy/.env и заполнить. Файл .env в git не попадает.
TAG=latest
IMAGE_PREFIX=ghcr.io/bauman-united

# Режим nginx: http (до домена) или https (после выпуска сертификата)
NGINX_MODE=http
SITE_DOMAIN=example.ru

POSTGRES_PASSWORD=change-me-long-random

BU_SITE_URL=http://127.0.0.1
BU_NOINDEX=1
BU_REVALIDATE_SECRET=change-me-long-random
BU_TELEGRAM_BOT_TOKEN=
BU_TELEGRAM_CHAT_ID=

# Бэкапы в Timeweb S3
S3_ENDPOINT=https://s3.twcstorage.ru
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
```

- [ ] **Step 2: `deploy/docker-compose.yml`**

```yaml
name: bu-site

x-python: &python
  image: ${IMAGE_PREFIX:-ghcr.io/bauman-united}/bu-python:${TAG:-latest}
  build:
    context: ..
    dockerfile: deploy/python.Dockerfile
  environment: &python-env
    BU_DATABASE_URL: postgresql+psycopg://bu:${POSTGRES_PASSWORD}@postgres/bu
    BU_SITE_URL: ${BU_SITE_URL}
    BU_REVALIDATE_URL: http://web:3000/api/revalidate
    BU_REVALIDATE_SECRET: ${BU_REVALIDATE_SECRET}
    BU_TELEGRAM_BOT_TOKEN: ${BU_TELEGRAM_BOT_TOKEN:-}
    BU_TELEGRAM_CHAT_ID: ${BU_TELEGRAM_CHAT_ID:-}
  restart: unless-stopped

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: bu
      POSTGRES_USER: bu
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in deploy/.env}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bu -d bu"]
      interval: 5s
      timeout: 3s
      retries: 20
    restart: unless-stopped

  migrate:
    <<: *python
    command: ["alembic", "-c", "core/alembic.ini", "upgrade", "head"]
    depends_on:
      postgres: { condition: service_healthy }
    restart: "no"

  api:
    <<: *python
    depends_on:
      migrate: { condition: service_completed_successfully }
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
      interval: 10s
      timeout: 3s
      retries: 10

  worker:
    <<: *python
    command: ["sh", "-c", "python -m bu_worker run content && exec python -m bu_worker schedule"]
    volumes:
      - snapshots:/data/snapshots
    depends_on:
      migrate: { condition: service_completed_successfully }
      web: { condition: service_started }

  web:
    image: ${IMAGE_PREFIX:-ghcr.io/bauman-united}/bu-web:${TAG:-latest}
    build:
      context: ..
      dockerfile: deploy/web.Dockerfile
    environment:
      BU_API_URL: http://api:8000
      BU_SITE_URL: ${BU_SITE_URL}
      BU_NOINDEX: ${BU_NOINDEX:-1}
      BU_REVALIDATE_SECRET: ${BU_REVALIDATE_SECRET}
    depends_on:
      api: { condition: service_healthy }
    restart: unless-stopped

  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
      - "443:443"
    environment:
      SITE_DOMAIN: ${SITE_DOMAIN:-example.ru}
    volumes:
      - ./nginx/${NGINX_MODE:-http}:/etc/nginx/templates:ro
      - ./nginx/common:/etc/nginx/common:ro
      - certbot-www:/var/www/certbot:ro
      - letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - web
    restart: unless-stopped

  certbot:
    image: certbot/certbot:v3.0.1
    volumes:
      - certbot-www:/var/www/certbot
      - letsencrypt:/etc/letsencrypt
    entrypoint: ["sh", "-c", "trap exit TERM; while :; do certbot renew --webroot -w /var/www/certbot --quiet; sleep 12h & wait $${!}; done"]
    restart: unless-stopped

volumes:
  pgdata:
  snapshots:
  certbot-www:
  letsencrypt:
```

Примечание: `worker` ждёт `web`, чтобы первый revalidate после синка дошёл; если web ещё не готов — `revalidate` логирует ошибку и не роняет воркер (так сделано в плане 1).

- [ ] **Step 3: nginx**

`deploy/nginx/common/proxy.conf`:
```nginx
proxy_http_version 1.1;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_read_timeout 30s;
```

`deploy/nginx/http/default.conf.template`:
```nginx
gzip on;
gzip_types text/css application/javascript application/json image/svg+xml application/xml text/plain;
server_tokens off;

server {
    listen 80 default_server;
    server_name _;
    client_max_body_size 2m;

    location /.well-known/acme-challenge/ { root /var/www/certbot; }

    location /_next/static/ {
        proxy_pass http://web:3000;
        include /etc/nginx/common/proxy.conf;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    location / {
        proxy_pass http://web:3000;
        include /etc/nginx/common/proxy.conf;
    }
}
```

- [ ] **Step 4: Смоук-скрипт**

`deploy/smoke.sh`:
```bash
#!/usr/bin/env bash
# Проверка поднятого стека: ./deploy/smoke.sh [base_url]
set -euo pipefail
BASE="${1:-http://localhost}"
fail() { echo "FAIL: $*" >&2; exit 1; }
code() { curl -s -o /dev/null -w "%{http_code}" "$1"; }

for path in / /matches /standings /team /news /about /join /robots.txt /sitemap.xml; do
  c=$(code "$BASE$path"); [ "$c" = "200" ] || fail "$path → $c"
  echo "ok $path"
done
[ "$(code "$BASE/no-such-page")" = "404" ] || fail "404 page"
[ "$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/revalidate" -H 'content-type: application/json' -d '{"tags":["home"]}')" = "401" ] || fail "revalidate without secret must be 401"
curl -s "$BASE/" | grep -q 'application/ld+json' || fail "JSON-LD on home"
echo "smoke ok"
```
`chmod +x deploy/smoke.sh`; в `.gitignore` добавить `deploy/.env`.

- [ ] **Step 5: Локальный холодный старт и проверки Review Focus 1–3**

Run:
```bash
cp deploy/.env.example deploy/.env
sed -i '' 's/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=local-dev-pass/; s/^BU_REVALIDATE_SECRET=.*/BU_REVALIDATE_SECRET=local-secret/; s/^IMAGE_PREFIX=.*/IMAGE_PREFIX=local/; s#^BU_SITE_URL=.*#BU_SITE_URL=http://localhost#' deploy/.env
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
docker compose -f deploy/docker-compose.yml --env-file deploy/.env ps
./deploy/smoke.sh http://localhost
docker compose -f deploy/docker-compose.yml --env-file deploy/.env logs worker | tail -20
```
Expected: `migrate` — `exited (0)`; остальные `running`/`healthy`; smoke ok; в логах воркера — синк content и первый запуск join.football со статусом ok (живые запросы к join.football — один прогон, паузы 3 с).

Проверка внутренней сети (Review Focus 3):
```bash
curl -s -m 3 -o /dev/null -w "%{http_code}\n" localhost:8000/health || true   # не должно отвечать стеку (порт не опубликован)
docker compose -f deploy/docker-compose.yml --env-file deploy/.env port api 8000 || echo "api not published (ok)"
```
Expected: `api not published (ok)` (на 8000 у разработчика может висеть чужой процесс — проверка через `compose port`).

Перезапуск без потери данных (Review Focus 2):
```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec -T postgres psql -U bu -d bu -Atc "select count(*) from match"
docker compose -f deploy/docker-compose.yml --env-file deploy/.env down && docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d
sleep 20 && docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec -T postgres psql -U bu -d bu -Atc "select count(*) from match; select count(*) from news"
```
Expected: число матчей то же (>0), новостей столько же, сколько файлов в `content/news`.

Оставить стек запущенным для Task 3–4.

- [ ] **Step 6: Commit**

```bash
git add deploy .gitignore && git commit -m "deploy: docker compose stack with nginx http mode and smoke check"
```

---

### Task 3: HTTPS-режим и переход на домен

**Files:**
- Create: `deploy/nginx/https/default.conf.template`, `deploy/issue-cert.sh`

- [ ] **Step 1: Шаблон https**

`deploy/nginx/https/default.conf.template`:
```nginx
gzip on;
gzip_types text/css application/javascript application/json image/svg+xml application/xml text/plain;
server_tokens off;

server {
    listen 80 default_server;
    server_name _;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://${SITE_DOMAIN}$request_uri; }
}

server {
    listen 443 ssl;
    http2 on;
    server_name www.${SITE_DOMAIN};
    ssl_certificate /etc/letsencrypt/live/${SITE_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${SITE_DOMAIN}/privkey.pem;
    return 301 https://${SITE_DOMAIN}$request_uri;
}

server {
    listen 443 ssl default_server;
    http2 on;
    server_name ${SITE_DOMAIN};
    ssl_certificate /etc/letsencrypt/live/${SITE_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${SITE_DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:SSL:10m;
    add_header Strict-Transport-Security "max-age=31536000" always;
    client_max_body_size 2m;

    location /_next/static/ {
        proxy_pass http://web:3000;
        include /etc/nginx/common/proxy.conf;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    location / {
        proxy_pass http://web:3000;
        include /etc/nginx/common/proxy.conf;
    }
}
```

- [ ] **Step 2: Скрипт выпуска сертификата**

`deploy/issue-cert.sh`:
```bash
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
echo "и выполните: docker compose --env-file .env up -d nginx web worker"
```
`chmod +x deploy/issue-cert.sh`.

- [ ] **Step 3: Проверка https-конфига с самоподписанным сертификатом (Review Focus 5)**

```bash
docker run --rm -v bu-site_letsencrypt:/etc/letsencrypt alpine sh -c "apk add -q openssl && mkdir -p /etc/letsencrypt/live/bu.test && openssl req -x509 -nodes -newkey rsa:2048 -days 1 -subj /CN=bu.test -keyout /etc/letsencrypt/live/bu.test/privkey.pem -out /etc/letsencrypt/live/bu.test/fullchain.pem"
NGINX_MODE=https SITE_DOMAIN=bu.test docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d nginx
curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" -H "Host: bu.test" http://localhost/matches
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: bu.test" http://localhost/.well-known/acme-challenge/none
curl -sk -o /dev/null -w "%{http_code} %{redirect_url}\n" --resolve www.bu.test:443:127.0.0.1 https://www.bu.test/team
curl -sk -o /dev/null -w "%{http_code}\n" --resolve bu.test:443:127.0.0.1 https://bu.test/
```
Expected: `301 https://bu.test/matches`; `404` (ACME-путь обслуживается nginx, не редиректится); `301 https://bu.test/team`; `200`.

Вернуть http-режим и убрать тестовый сертификат:
```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d nginx
docker run --rm -v bu-site_letsencrypt:/etc/letsencrypt alpine rm -rf /etc/letsencrypt/live/bu.test
```

- [ ] **Step 4: Commit**

```bash
git add deploy && git commit -m "deploy: https nginx mode and certificate issuing script"
```

---

### Task 4: Бэкап и восстановление

**Files:**
- Create: `deploy/backup.sh`, `deploy/restore.sh`

- [ ] **Step 1: `deploy/backup.sh`**

```bash
#!/usr/bin/env bash
# Ежедневный бэкап: cron хоста → `15 4 * * * /opt/bu-site/deploy/backup.sh >> /var/log/bu-backup.log 2>&1`
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
KEEP_DAYS="${KEEP_DAYS:-14}"
DIR="${BACKUP_DIR:-/var/backups/bu-site}"
mkdir -p "$DIR"
FILE="$DIR/bu-$(date +%Y%m%d-%H%M).sql.gz"
docker compose --env-file .env exec -T postgres pg_dump -U bu -d bu --no-owner | gzip > "$FILE"
[ -s "$FILE" ] || { echo "empty dump" >&2; exit 1; }
find "$DIR" -name 'bu-*.sql.gz' -mtime +"$KEEP_DAYS" -delete
if [ -n "${S3_BUCKET:-}" ]; then
  docker run --rm -v "$DIR:/backups:ro" \
    -e AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" -e AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
    amazon/aws-cli:2.17.0 --endpoint-url "$S3_ENDPOINT" s3 cp "/backups/$(basename "$FILE")" "s3://$S3_BUCKET/db/"
fi
echo "backup ok: $FILE"
```

Хранение в S3 14 дней — правилом жизненного цикла бакета в панели Timeweb (в README).

- [ ] **Step 2: `deploy/restore.sh`**

```bash
#!/usr/bin/env bash
# Восстановление: ./deploy/restore.sh /var/backups/bu-site/bu-YYYYMMDD-HHMM.sql.gz [db]
# По умолчанию восстанавливает в базу bu (ОСТОРОЖНО: перезаписывает данные). Для проверки — укажите другую базу.
set -euo pipefail
cd "$(dirname "$0")"
FILE="$1"; DB="${2:-bu}"
[ -f "$FILE" ] || { echo "no file $FILE" >&2; exit 1; }
if [ "$DB" = "bu" ]; then
  read -r -p "Перезаписать рабочую базу bu? Напишите yes: " ok; [ "$ok" = "yes" ] || exit 1
  docker compose --env-file .env stop api worker web
fi
docker compose --env-file .env exec -T postgres psql -U bu -d postgres -c "DROP DATABASE IF EXISTS \"$DB\" WITH (FORCE)" -c "CREATE DATABASE \"$DB\" OWNER bu"
gunzip -c "$FILE" | docker compose --env-file .env exec -T postgres psql -q -U bu -d "$DB"
[ "$DB" = "bu" ] && docker compose --env-file .env up -d api worker web
echo "restored $FILE into $DB"
```

- [ ] **Step 3: Проверка (Review Focus 4)**

```bash
chmod +x deploy/backup.sh deploy/restore.sh
BACKUP_DIR=/tmp/bu-backups ./deploy/backup.sh
./deploy/restore.sh "$(ls -t /tmp/bu-backups/bu-*.sql.gz | head -1)" bu_restore_check
docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec -T postgres psql -U bu -d bu_restore_check -Atc "select count(*) from match; select count(*) from player"
docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec -T postgres psql -U bu -d postgres -c "DROP DATABASE bu_restore_check"
```
Expected: `backup ok`; восстановленная база содержит те же числа матчей и игроков, что рабочая.

- [ ] **Step 4: Commit**

```bash
git add deploy && git commit -m "deploy: database backup to S3 and restore scripts"
```

---

### Task 5: CI и canary

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/canary.yml`, `worker/tests/test_canary.py`
- Modify: `pyproject.toml` (pytest marker `canary`, по умолчанию исключён)

- [ ] **Step 1: Canary-тест**

`worker/tests/test_canary.py`:
```python
"""Живая проверка, что вёрстка join.football всё ещё парсится. Запуск: CANARY=1 uv run pytest -m canary"""

import os

import pytest

from bu_core.settings import Settings
from bu_worker.http import PoliteClient
from bu_worker.sources.joinfootball.fetch import fetch_bundle

pytestmark = [
    pytest.mark.canary,
    pytest.mark.skipif(os.environ.get("CANARY") != "1", reason="live network check"),
]


def test_live_joinfootball_still_parses():
    s = Settings(_env_file=None)
    client = PoliteClient(s.joinfootball_base, "BaumanUnitedBot/1.0 (+canary)", s.request_delay_s)
    bundle = fetch_bundle(client, s.joinfootball_tournament_ids[0], s.joinfootball_team_id,
                          s.joinfootball_base, lambda name, html: None)
    assert len(bundle.players) >= 8
    assert bundle.calendar
    assert any(row.team_name in s.our_team_names for row in bundle.standings)
```

В `pyproject.toml` → `[tool.pytest.ini_options]` добавить:
```toml
markers = ["canary: live network checks against sources"]
```

Run: `uv run pytest worker/tests/test_canary.py` → `1 skipped`; `CANARY=1 uv run pytest -m canary` → `1 passed`.

- [ ] **Step 2: `.github/workflows/ci.yml`**

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request:

jobs:
  python:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_PASSWORD: postgres }
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres" --health-interval 5s --health-retries 20
    env:
      PGHOST: localhost
      PGUSER: postgres
      PGPASSWORD: postgres
      TEST_DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost/bu_test
      BU_DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost/bu_dev
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --frozen
      - run: createdb bu_test && createdb bu_dev
      - run: uv run ruff check . && uv run ruff format --check .
      - run: uv run alembic -c core/alembic.ini upgrade head && uv run alembic -c core/alembic.ini check
      - run: uv run pytest

  web:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: web } }
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: pnpm, cache-dependency-path: web/pnpm-lock.yaml }
      - run: pnpm install --frozen-lockfile
      - run: pnpm test
      - run: pnpm typecheck
      - run: pnpm lint

  e2e:
    runs-on: ubuntu-latest
    needs: [python, web]
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_PASSWORD: postgres }
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres" --health-interval 5s --health-retries 20
    env:
      PGHOST: localhost
      PGUSER: postgres
      PGPASSWORD: postgres
      CI: "1"
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --frozen
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: pnpm, cache-dependency-path: web/pnpm-lock.yaml }
      - run: pnpm install --frozen-lockfile
        working-directory: web
      - run: pnpm exec playwright install --with-deps chromium
        working-directory: web
      - run: pnpm e2e
        working-directory: web
      - run: pnpm e2e:empty
        working-directory: web
      - if: failure()
        uses: actions/upload-artifact@v4
        with: { name: playwright, path: web/test-results }
```

(`pnpm/action-setup@v4` берёт версию pnpm из поля `packageManager` в `web/package.json`; если поля нет — добавить `"packageManager": "pnpm@<текущая версия pnpm -v>"`. Подключение e2e к Postgres CI идёт через `PGHOST/PGUSER/PGPASSWORD` — libpq подхватывает их и в `createdb`, и в psycopg-URL без логина.)

- [ ] **Step 3: `.github/workflows/canary.yml`**

```yaml
name: Canary (join.football markup)
on:
  schedule: [{ cron: "0 5 * * *" }]
  workflow_dispatch:
jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --frozen
      - run: CANARY=1 uv run pytest -m canary -v
```

- [ ] **Step 4: Проверка синтаксиса workflow**

Run: `uv run --with pyyaml python -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]; print('yaml ok')" .github/workflows/*.yml`
и, если доступно, `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.7 -color`
Expected: `yaml ok`; actionlint без ошибок.

Локально прогнать то, что CI запускает: `uv run ruff check . && uv run pytest && (cd web && pnpm test && pnpm typecheck && pnpm lint)` → PASS.

- [ ] **Step 5: Commit**

```bash
git add .github pyproject.toml worker/tests/test_canary.py web/package.json && git commit -m "ci: python, web and e2e workflows; daily join.football canary"
```

---

### Task 6: Деплой-воркфлоу и runbook

**Files:**
- Create: `.github/workflows/deploy.yml`, `deploy/README.md`, `deploy/deploy.sh`

- [ ] **Step 1: `deploy/deploy.sh`** (выполняется на сервере)

```bash
#!/usr/bin/env bash
# Обновление стека на сервере до тега: ./deploy/deploy.sh <tag>
set -euo pipefail
cd "$(dirname "$0")"
TAG="${1:-latest}"
sed -i.bak "s/^TAG=.*/TAG=$TAG/" .env
docker compose --env-file .env pull
docker compose --env-file .env up -d --remove-orphans
docker image prune -f >/dev/null
./smoke.sh http://localhost || { echo "smoke failed after deploy $TAG" >&2; exit 1; }
```

- [ ] **Step 2: `.github/workflows/deploy.yml`**

```yaml
name: Deploy
on:
  workflow_run:
    workflows: [CI]
    types: [completed]
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  packages: write

jobs:
  deploy:
    if: vars.DEPLOY_ENABLED == 'true' && (github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success')
    runs-on: ubuntu-latest
    env:
      PREFIX: ghcr.io/${{ github.repository_owner }}
      TAG: ${{ github.event.workflow_run.head_sha || github.sha }}
    steps:
      - uses: actions/checkout@v4
        with: { ref: "${{ env.TAG }}" }
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: "${{ github.actor }}", password: "${{ secrets.GITHUB_TOKEN }}" }
      - name: Normalize image prefix
        run: echo "PREFIX=$(echo "$PREFIX" | tr '[:upper:]' '[:lower:]')" >> "$GITHUB_ENV"
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: deploy/python.Dockerfile
          push: true
          tags: ${{ env.PREFIX }}/bu-python:${{ env.TAG }},${{ env.PREFIX }}/bu-python:latest
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: deploy/web.Dockerfile
          push: true
          tags: ${{ env.PREFIX }}/bu-web:${{ env.TAG }},${{ env.PREFIX }}/bu-web:latest
      - name: Sync deploy files and roll out
        env:
          SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
          HOST: ${{ secrets.VPS_HOST }}
          USER: ${{ secrets.VPS_USER }}
        run: |
          install -m 600 /dev/null ~/.ssh_key && printf '%s\n' "$SSH_KEY" > ~/.ssh_key
          SSH="ssh -i ~/.ssh_key -o StrictHostKeyChecking=accept-new"
          rsync -az -e "$SSH" --exclude .env deploy/ "$USER@$HOST:/opt/bu-site/deploy/"
          $SSH "$USER@$HOST" "/opt/bu-site/deploy/deploy.sh $TAG"
```

- [ ] **Step 3: `deploy/README.md` — runbook** (по-русски, пошагово):
  1. **Сервер Timeweb Cloud:** Ubuntu 24.04, 2 vCPU / 2–4 ГБ RAM / 30+ ГБ; SSH-ключ; `apt install docker.io docker-compose-v2 rsync`; пользователь `deploy` в группе `docker`; `mkdir -p /opt/bu-site/deploy && chown deploy /opt/bu-site -R`; firewall: открыть 22, 80, 443.
  2. **Первый запуск:** скопировать `deploy/` на сервер (`rsync`), `cp .env.example .env`, сгенерировать пароли (`openssl rand -hex 24`), заполнить `BU_SITE_URL=http://<IP>`, `BU_NOINDEX=1`; `docker login ghcr.io` (PAT с `read:packages`, если пакеты приватные); `./deploy.sh latest`.
  3. **GitHub:** Secrets `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`; Variable `DEPLOY_ENABLED=true` — с этого момента каждый зелёный CI на `main` выкатывается.
  4. **Проверка lfl.ru с сервера:** `curl -sI -A "Mozilla/5.0" https://lfl.ru/club14270` — если 200, ЛФЛ можно парсить (отдельная задача), иначе вести ЛФЛ в `content/matches/*.yaml`.
  5. **Алерты:** создать бота в @BotFather, узнать свой chat_id (@userinfobot), заполнить `BU_TELEGRAM_BOT_TOKEN`/`BU_TELEGRAM_CHAT_ID`, `docker compose --env-file .env up -d worker`.
  6. **Бэкапы:** бакет в Timeweb S3 + правило хранения 14 дней; ключи в `.env`; cron из шапки `backup.sh`; раз в месяц — проверка `restore.sh … bu_restore_check`.
  7. **Домен:** купить (reg.ru / nic.ru), A-записи `@` и `www` → IP; `./issue-cert.sh <домен> <email>`; в `.env`: `NGINX_MODE=https`, `SITE_DOMAIN`, `BU_SITE_URL=https://<домен>`, `BU_NOINDEX=0`; `docker compose --env-file .env up -d nginx web worker`; проверить `curl -I http://<домен>` → 301, `https://<домен>/robots.txt` → `Allow`.
  8. **После домена (SEO-чеклист спеки 9.3):** Яндекс Вебмастер (подтверждение, sitemap, регион «Москва», IndexNow), Google Search Console, Яндекс Метрика, карточка в Яндекс Бизнесе, ссылки на сайт с lfl.ru/join.football/VK/Telegram.
  9. **Обновление контента:** правка `content/` → push в `main` → CI → деплой (синк content выполняется воркером при старте).
  10. **Диагностика:** `docker compose --env-file .env ps|logs -f worker|web|api`, `psql`: `docker compose exec postgres psql -U bu -d bu`, журнал парсинга: `select * from ingest_run order by id desc limit 10;`.

- [ ] **Step 4: Проверка**

Run: `bash -n deploy/*.sh && uv run --with pyyaml python -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml')); print('ok')"` и actionlint (как в Task 5).
Локально прогнать `deploy.sh` против локального стека нельзя без registry — вместо этого: `IMAGE_PREFIX=local TAG=latest docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --remove-orphans && ./deploy/smoke.sh` → smoke ok.

- [ ] **Step 5: Commit и остановка локального стека**

```bash
git add .github deploy && git commit -m "deploy: GitHub Actions rollout to VPS and runbook"
docker compose -f deploy/docker-compose.yml --env-file deploy/.env down
```
