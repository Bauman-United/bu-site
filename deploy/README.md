# Деплой «Бауман Юнайтед» на VPS

Стек: `postgres` → `migrate` (одноразово) → `api`, `worker`, `web` → `nginx` (+ `certbot`). Наружу открыты только 80/443.
Все команды ниже выполняются на сервере в `/opt/bu-site/deploy`, если не сказано иное.

## 1. Сервер (Timeweb Cloud)

- Ubuntu 24.04, 2 vCPU, 2–4 ГБ RAM, 30+ ГБ диска, вход по SSH-ключу.
- Установить Docker и rsync:
  ```bash
  sudo apt update && sudo apt install -y docker.io docker-compose-v2 rsync
  sudo adduser --disabled-password deploy && sudo usermod -aG docker deploy
  sudo mkdir -p /opt/bu-site/deploy && sudo chown -R deploy /opt/bu-site
  ```
- Firewall в панели Timeweb: открыть 22, 80, 443; всё остальное закрыть.

## 2. Первый запуск (до покупки домена)

Сначала выполните шаг 3 (секреты и `DEPLOY_ENABLED`) и один раз запустите Actions → Deploy → Run workflow: так в GHCR появятся образы. Без них `deploy.sh` не сможет их скачать. Workflow сам синхронизирует `deploy/` и вызовет `deploy.sh`, поэтому ниже остаётся только подготовить `.env` до первого запуска.

С локальной машины скопировать конфиги:
```bash
rsync -az --exclude .env deploy/ deploy@<IP>:/opt/bu-site/deploy/
```
На сервере:
```bash
cd /opt/bu-site/deploy
cp .env.example .env
openssl rand -hex 24   # → POSTGRES_PASSWORD
openssl rand -hex 24   # → BU_REVALIDATE_SECRET
nano .env              # BU_SITE_URL=http://<IP>, BU_NOINDEX=1, NGINX_MODE=http
docker login ghcr.io   # логин GitHub + PAT с правом read:packages (если пакеты приватные)
./deploy.sh latest
```
`deploy.sh` тянет образы, поднимает стек и прогоняет `smoke.sh`. Пока `BU_NOINDEX=1`, сайт закрыт от индексации (иначе поисковики проиндексируют голый IP).

## 3. Автодеплой из GitHub

Settings → Secrets and variables → Actions:
- Secrets: `VPS_HOST` (IP), `VPS_USER` (`deploy`), `VPS_SSH_KEY` (приватный ключ, публичный — в `~deploy/.ssh/authorized_keys`).
- Variables: `DEPLOY_ENABLED` = `true`.

После этого каждый зелёный CI на `main` собирает образы в GHCR и выкатывает их (`.github/workflows/deploy.yml`). Ручной запуск — Actions → Deploy → Run workflow.

## 4. Проверка lfl.ru с сервера

```bash
curl -sI -A "Mozilla/5.0" https://lfl.ru/club14270 | head -1
```
`200` — источник доступен. Воркер собирает состав, статистику игроков, календарь,
результаты, таблицу и протоколы турниров из `BU_LFL_TOURNAMENT_IDS`. Для ручной проверки:

```bash
docker compose --env-file .env exec worker python -m bu_worker run lfl
```

У LFL минуты голов часто не указаны: такие события сохраняются с минутой `0`. Кубковые
турниры могут не иметь турнирной таблицы — для них это штатная ситуация.

## 5. Алерты в Telegram

1. Создать бота у @BotFather, получить токен.
2. Написать боту `/start`, узнать свой chat_id (например, через @userinfobot).
3. В `.env`: `BU_TELEGRAM_BOT_TOKEN`, `BU_TELEGRAM_CHAT_ID`; затем `docker compose --env-file .env up -d worker`.

Воркер пишет, если парсер упал, источник вернул подозрительно мало данных (данные не перезаписываются) или найден тёзка, которого нельзя склеить автоматически.

### Заявки «Хочу в команду»

Форма на `/join` отправляет заявку владельцу команды личным сообщением от бота клуба.

1. Создать бота у @BotFather (можно того же, что для алертов), получить токен.
2. С аккаунта владельца написать боту `/start` — иначе бот не сможет писать ему первым.
3. Узнать chat id владельца (например, через @userinfobot).
4. В `.env`: `BU_TELEGRAM_BOT_TOKEN`, `BU_JOIN_CHAT_ID`; затем `docker compose --env-file .env up -d api`.

Без `BU_JOIN_CHAT_ID` заявки уходят в `BU_TELEGRAM_CHAT_ID`; если не задан ни токен, ни chat id, форма отвечает «не получилось отправить» и предлагает написать капитану. Лимит — 3 заявки с одного IP в час.

## 6. Бэкапы

1. Создать бакет в Timeweb S3, задать правило жизненного цикла «удалять через 14 дней».
2. Ключи и имя бакета — в `.env` (`S3_*`).
3. Бэкапы складываются в `/opt/bu-site/backups` (каталог создаётся сам). Cron пользователя `deploy` (`crontab -e`):
   ```
   15 4 * * * /opt/bu-site/deploy/backup.sh >> /home/deploy/bu-backup.log 2>&1
   ```
4. Раз в месяц проверять восстановление в отдельную базу:
   ```bash
   ./restore.sh /opt/bu-site/backups/bu-<дата>.sql.gz bu_restore_check
   docker compose --env-file .env exec postgres psql -U bu -d postgres -c "DROP DATABASE bu_restore_check"
   ```
   Без второго аргумента `restore.sh` перезаписывает рабочую базу (спросит подтверждение).

## 7. Домен и HTTPS

1. Купить домен (reg.ru / nic.ru), A-записи `@` и `www` → IP сервера. Дождаться, пока `dig +short <домен>` вернёт IP.
2. Выпустить сертификат (nginx ещё в режиме `http`):
   ```bash
   ./issue-cert.sh <домен> <email>
   ```
3. В `.env`: `NGINX_MODE=https`, `SITE_DOMAIN=<домен>`, `BU_SITE_URL=https://<домен>`, `BU_NOINDEX=0`.
4. `docker compose --env-file .env up -d nginx web worker`
5. Проверить:
   ```bash
   curl -sI http://<домен>/ | head -3          # 301 → https://<домен>/
   curl -sI https://www.<домен>/ | head -3     # 301 → https://<домен>/
   curl -s https://<домен>/robots.txt          # Allow: / и Sitemap
   ./smoke.sh https://<домен>
   ```
Сертификат продлевается контейнером `certbot` автоматически; nginx перечитывает его при следующем перезапуске (раз в месяц-два достаточно `docker compose --env-file .env restart nginx`).

## 8. SEO после домена

- Яндекс Вебмастер: добавить сайт, подтвердить (meta-тег или DNS), отправить `https://<домен>/sitemap.xml`, регион — Москва, включить IndexNow.
- Google Search Console: добавить ресурс-домен, подтвердить через DNS, отправить sitemap.
- Яндекс Метрика: создать счётчик (код добавим в сайт отдельной задачей).
- Яндекс Бизнес: карточка «Бауман Юнайтед — футбольный клуб» с адресом тренировок и ссылкой на сайт.
- Ссылки на сайт: профиль команды на lfl.ru и join.football, шапка/закреп в VK и Telegram, паблики факультетов, студсовет и спортклуб МГТУ.

## 9. Обновление контента

Правка файлов в `content/` (новости, игроки, история) → коммит в `main` → CI → деплой. Воркер при старте синхронизирует `content/` в базу и сбрасывает кеш страниц.

## 10. Диагностика

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs -f --tail=100 worker   # или web, api, nginx
docker compose --env-file .env exec postgres psql -U bu -d bu
#   select source, status, counts, error, started_at from ingest_run order by id desc limit 10;
docker compose --env-file .env exec worker python -m bu_worker run joinfootball   # ручной парсинг
docker compose --env-file .env exec worker python -m bu_worker run lfl            # ручной парсинг LFL
```
