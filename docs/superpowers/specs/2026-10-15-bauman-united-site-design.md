# Сайт «Бауман Юнайтед» — дизайн реализации

Дата: 2026-10-15
Статус: на ревью

## 1. Контекст и цель

Сайт любительской футбольной команды «Бауман Юнайтед» (МГТУ им. Н. Э. Баумана, Москва, формат 8×8).
Макеты, дизайн-система, ТЗ по страницам и черновая модель данных уже готовы — пакет `bauman-united-site.zip`
(далее «пакет»): `docs/01-spec.md`, `docs/02-design-system.md`, `design/tokens.*`, `design/artboards/*.dc.html`.
Этот документ описывает **как** реализуем сайт; **что** на страницах — по-прежнему пакет, с отличиями из раздела 2.

**Цель:** сайт по макетам, быстрый с телефона (трафик из Telegram/VK), данные о матчах и игроках
обновляются автоматически, ручной контент правится файлами в репозитории. Сайт в топе Яндекса по
брендовым запросам и связкам «футбол + МГТУ Баумана / бауманка».

**Критерии успеха:**
- Все MVP-страницы (раздел 6) соответствуют макетам на телефоне и десктопе.
- Матчи, счета, таблицы и статистика игроков обновляются без участия человека.
- Сломанный парсер не приводит к пустым или неверным блокам на сайте.
- LCP < 2.5 с на 4G; Lighthouse SEO ≥ 95.
- Сайт проиндексирован Яндексом и Google, sitemap принят, JSON-LD валиден.

## 2. Отличия от пакета

| Пакет | Решение |
|---|---|
| Astro, статическая сборка из JSON | Next.js (App Router) + Python (FastAPI, воркер) + Postgres |
| Данные вручную в `data/*.json` | Матчи/игроки/таблицы — парсеры; ручной контент — Markdown/YAML в `content/` |
| «Бауманская лига» = фэнтази (iframe) | Bauman League (`bauman_league.join.football`) — реальная университетская лига МГТУ, один из двух турниров команды. Фэнтази — вне скоупа, в бэклоге отдельная вкладка `/fantasy` с iframe |
| Хостинг — статика | Один VPS Timeweb, docker-compose |
| Админка (Decap/Keystatic) «позже» | Админки нет. Возможна позже поверх `content/` или FastAPI |

## 3. Источники данных

| Источник | Что берём | Ограничения |
|---|---|---|
| join.football, `bauman_league.join.football/tournament/<id>/...` | Заявка команды (номер, амплуа, ФИО, И/Г/П/ЖК/КК), календарь и результаты, турнирная таблица, бомбардиры/ассистенты | robots.txt закрывает `/matches`, `/player`, `/participants` — их не запрашиваем. HTML серверный, JS не нужен |
| lfl.ru, `lfl.ru/club14270` | Матчи, таблица, статистика ЛФЛ | Из среды разработки соединение обрывается (HTTP/2 PROTOCOL_ERROR). Доступность с VPS проверяется первой задачей; fallback — ручные `content/matches/*.yaml` |
| Яндекс Диск (публичная папка) | Фото альбомов | Оригиналы остаются на Диске |
| `content/` в репозитории | Новости, фото/прозвища/факты игроков, история, трофеи, клуб, ручные события матчей | — |

Персональные данные: даты рождения игроков со страниц источников **не сохраняются и не публикуются**.

## 4. Архитектура

```
[join.football] [lfl.ru] [Я.Диск] [content/ в репо]
        \          |        |        /
   worker (Python, cron): fetch → snapshot → parse → upsert → recompute → revalidate
                              ↓
                          Postgres  (единый источник правды, архив сезонов)
                              ↓
                    api (FastAPI, read-only)
                              ↓
          web (Next.js App Router, ISR + on-demand revalidation)
                              ↓
                    nginx (+ certbot) → пользователь
```

### 4.1 Структура репозитория

```
bu-site/
├── web/          Next.js 15, TypeScript, CSS Modules — отображение и SEO
├── api/          FastAPI — GET-эндпоинты для web
├── worker/       парсеры, синк контента и фото, пайплайн, планировщик
├── core/         общий Python-пакет: модели SQLAlchemy 2, Alembic, доменная логика (статистика)
├── content/      news/*.md, players/*.yaml, matches/*.yaml, history.yaml, club.yaml
├── design/       токены и макеты из пакета (справочник)
├── deploy/       docker-compose.yml, nginx, certbot, скрипт бэкапа
└── .github/workflows/  CI и деплой
```

Python: 3.12, менеджер `uv`, workspace из `core`, `api`, `worker`. Линт — ruff, типы — mypy.
Node: 20 LTS, pnpm.

### 4.2 Юниты и границы

| Юнит | Ответственность | Зависит от |
|---|---|---|
| `core.models` | ORM-модели и миграции | Postgres |
| `core.stats` | Чистые функции: статистика игрока, форма, лидеры, рекорды, цифры клуба | только модели/DTO |
| `core.matching` | Склейка игрока из источника с записью в БД и YAML | — |
| `worker.sources.<name>` | `fetch() -> RawSnapshot`, `parse(RawSnapshot) -> ParsedBundle` | httpx, selectolax |
| `worker.sources.content` | Чтение `content/` → DTO | pyyaml, python-frontmatter |
| `worker.sources.yadisk` | Публичная папка → WebP 400/800/1600 + метаданные | API Я.Диска, Pillow |
| `worker.pipeline` | Нормализация, транзакционный upsert, защита от пустоты, пересчёт, revalidate, алерты | core |
| `api` | Read-only JSON для web | core |
| `web` | Страницы, metadata, sitemap, JSON-LD, OG-картинки | только `api` |

`web` не ходит в Postgres и источники напрямую. `api` ничего не пишет (кроме `POST /join` в v2).

## 5. Данные

### 5.1 Модель

Основа — сущности из `docs/03-data-model.md` пакета, перенесённые в Postgres, со следующими изменениями:

- `tournament`: добавлены `source` (`lfl` | `joinfootball` | `manual`), `external_id`, `url`. Турниры Bauman League
  (Лига Инженеров и др.) — отдельные записи на каждый сезон.
- `player`: без даты рождения; добавлены `aliases text[]`. `slug` генерируется транслитом ФИО и не меняется.
- `player_source_link(player_id, source, external_name, external_id)` — привязка игрока к источнику.
- `player_tournament_stats(player_id, tournament_id, played, goals, assists, yellow, red, mvp)` — агрегаты из
  источника. База для таблиц и профилей.
- `match_event` — события по минутам, если удалось получить из источника или из `content/matches/<slug>.yaml`.
- `standing_row` — строки таблицы с `updated_at` и `source_url`.
- Агрегаты для чтения: `player_season_stats`, `club_records`, `team_form` — пересчитываются воркером, API только читает.
- `ingest_run(source, started_at, status, counts, error)` — журнал запусков воркера.

### 5.2 Приоритеты слияния

1. Поле из `content/` (YAML/frontmatter) перекрывает спарсенное (номер, позиция, имя для отображения).
2. Если `match_event` для матча есть — статистика по нему считается из событий; иначе берутся агрегаты `player_tournament_stats`.
3. Если игрок есть в нескольких источниках, агрегаты суммируются по турнирам, а не дублируются.

### 5.3 Склейка игроков

Ключ — нормализованное ФИО (нижний регистр, ё→е, без лишних пробелов) + `aliases` из YAML.
Однозначное совпадение — привязка. Нет совпадения — создаётся новый игрок. Неоднозначное совпадение
(несколько кандидатов) — игрок не создаётся, в `ingest_run` пишется предупреждение и уходит алерт;
человек добавляет алиас в `content/players/<slug>.yaml`.

### 5.4 Формат `content/`

```
content/
├── club.yaml              название, основание, соцсети, контакты, тренировки, «ищем», игрок месяца
├── players/<slug>.yaml    photo, nickname, fact, foot, faculty, role, joined, achievements, aliases, overrides
├── matches/<slug>.yaml    ручные матчи (если источника нет), events, lineup, mvp, report_news, stream/video
├── news/<slug>.md         frontmatter: date, tag, title, lead, cover, source, match; тело — Markdown
└── history.yaml           timeline, trophies, legends
```

Синк при каждом деплое. Ошибка валидации YAML (pydantic) роняет деплой с понятным сообщением
(файл, поле, причина) — битый контент не попадает на сайт.

## 6. Фронтенд

### 6.1 Страницы и этапы

| Страница | URL | Этап |
|---|---|---|
| Главная | `/` | MVP |
| Матчи (фильтры в query-string) | `/matches?season=&t=&where=` | MVP |
| Матч | `/matches/[slug]` | MVP: табло + отчёт; v2: события, схема поля 3-3-1, фото |
| Таблицы обоих турниров | `/standings` | MVP |
| Состав | `/team` | MVP |
| Игрок | `/team/[slug]` | MVP |
| Новости | `/news`, `/news/[slug]` | MVP |
| О клубе | `/about` | MVP |
| Хочу в команду | `/join` | MVP: ссылка на Telegram капитана; v2: форма → бот |
| Статистика | `/stats` | v2 |
| История и зал славы | `/history` | v2 |
| Фото | `/media`, `/media/[album]` | v2 |
| Видео и трансляции | `/media/video` | v3 |
| Голосование MVP матча | на `/matches/[slug]` | v3 |
| Фэнтази (iframe) | `/fantasy` | бэклог |

На главной блок «Таблица ЛФЛ» показывает таблицу основного турнира текущего сезона (выбор — `club.yaml: primary_tournament`).

### 6.2 Реализация

- Токены из `design/tokens.css` → глобальные CSS-переменные; компоненты на CSS Modules, перенос стилей из макетов 1:1.
- Шрифты Oswald и Manrope через `next/font` (self-host, кириллица).
- Server Components по умолчанию. Клиентские компоненты: обратный отсчёт, фильтры, сортировка таблиц,
  переключатель «сезон / всё время», бургер-меню, лайтбокс.
- Порядок: библиотека компонентов по `Kit.dc.html` → общие шапка/подвал → страницы.
- Данные: `fetch` к `api` с `next: { tags: [...] }`; `POST /api/revalidate` (с секретом) вызывает `revalidateTag`.
- Адаптив и доступность — по разделам «Адаптив» и «Доступность» `docs/01-spec.md` пакета.

## 7. Воркер

### 7.1 Цикл

1. **Fetch.** Перед запуском — проверка robots.txt (`urllib.robotparser`); запрещённые пути не запрашиваются.
   Пауза ≥ 3 с между запросами, User-Agent `BaumanUnitedBot/1.0 (+<SITE_URL>)`, таймауты и 3 ретрая с backoff.
2. **Snapshot.** Сырой HTML → `snapshots/<source>/<YYYY-MM-DD-HHMM>/`, хранение 30 дней.
3. **Parse.** HTML → pydantic DTO.
4. **Sanity check.** Сравнение с предыдущим успешным запуском: падение числа игроков заявки, матчей или строк таблицы
   более чем на 50 % либо ноль — запуск помечается `rejected`, БД не меняется, уходит алерт.
5. **Upsert** — одна транзакция на источник.
6. **Recompute** агрегатов.
7. **Revalidate** — POST в web с тегами изменённых сущностей; IndexNow для новых/изменённых URL.

### 7.2 Расписание

| Задача | Частота |
|---|---|
| join.football, lfl.ru | каждые 6 ч; в день матча — каждые 30 мин от начала матча до +3 ч |
| `content/` | при деплое |
| Яндекс Диск | ежедневно ночью |
| Очистка snapshots | ежедневно |

Планировщик — APScheduler внутри контейнера `worker`. Ручной запуск: `python -m worker run <source>`.

### 7.3 Алерты

Telegram-бот пишет владельцу в личку: ошибка парсера, `rejected` sanity check, неоднозначная склейка,
ошибка Я.Диска. Не чаще одного одинакового алерта в 6 ч.

## 8. API

Read-only, JSON, без авторизации (кроме `/internal/*` — по токену из сети docker).

`GET /club`, `/seasons`, `/tournaments`, `/matches?season&tournament&where&status`, `/matches/{slug}`,
`/players?active`, `/players/{slug}`, `/stats?season&tournament`, `/standings?tournament`,
`/news?tag&page`, `/news/{slug}`, `/albums`, `/albums/{id}`, `/history`, `/home` (агрегат для главной одним запросом),
`/sitemap` (все URL с `lastmod`).

Схемы ответов — pydantic; OpenAPI генерирует TS-типы для web (`openapi-typescript`) — одна модель на оба языка.

## 9. SEO

### 9.1 Целевые запросы

Голые «МГТУ им. Баумана» / «бауманка» занимают bmstu.ru, Википедия и СМИ — их не таргетируем.
Цели:
- бренд: «Бауман Юнайтед», «Bauman United», «бауман юнайтед футбол»;
- университет + футбол: «футбол МГТУ Баумана», «футбольная команда бауманки», «сборная бауманки по футболу»,
  «Лига Инженеров бауманка», «Bauman League футбол»;
- лиги: «Бауман Юнайтед ЛФЛ», «команда ЛФЛ 8x8 Москва»;
- длинный хвост: «Бауман Юнайтед — <соперник>», ФИО игроков.

### 9.2 Техническое (в коде, MVP)

- Полный HTML с сервера на всех страницах (SSR/ISR).
- `generateMetadata` везде. Title: `{Страница} — Бауман Юнайтед | футбольная команда МГТУ им. Баумана`
  (главная: `Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана`). Description генерируется из данных.
- Canonical на каждой странице; у `/matches` с фильтрами canonical — без query, `noindex` для комбинаций фильтров.
- `sitemap.xml` из `GET /sitemap` с `lastmod`; `robots.txt` со ссылкой на sitemap.
- nginx: 301 http→https и www→без www; `lang="ru"`.
- JSON-LD: `SportsTeam` (главная/«О клубе»: `sport`, `memberOf` → `CollegeOrUniversity` «МГТУ им. Н. Э. Баумана»,
  `location`, `sameAs` → VK/TG/lfl.ru/join.football, `logo`), `SportsEvent` (матч: `homeTeam`, `awayTeam`,
  `startDate`, `location`, `eventStatus`, `superEvent` → турнир), `Person` + `memberOf` (игрок),
  `NewsArticle` (новость), `BreadcrumbList` (везде, кроме главной).
- OG/Twitter-картинки через `next/og`: табло матча, карточка игрока, обложка новости, дефолтная для остальных.
- `next/image` (AVIF/WebP, `sizes`), lazy-load ниже первого экрана, без блокирующих сторонних скриптов.
- Фавикон и `manifest` из герба.

### 9.3 Поисковики и сервисы (после домена)

- Яндекс Вебмастер: подтверждение, sitemap, регион «Москва», IndexNow (ключ в `.env`, пинг из воркера).
- Google Search Console: подтверждение, sitemap.
- Яндекс Метрика (без вебвизора на старте) — счётчик через `next/script` `afterInteractive`.
- Яндекс Бизнес: карточка «Бауман Юнайтед — футбольный клуб» с адресом тренировок и ссылкой на сайт.

### 9.4 Контент и ссылки (не код — чеклист для команды)

- `/about`: 300–600 слов о команде, естественно включающие «футбольная команда МГТУ им. Н. Э. Баумана», «бауманка»,
  «ЛФЛ», «Лига Инженеров / Bauman League».
- Отчёт о каждом матче (от 150 слов) с названием соперника и авторами голов.
- Ссылки на сайт: профиль команды на lfl.ru и join.football, VK и Telegram (шапка, закреп), паблики факультетов,
  студсовет/профком МГТУ, спортклуб МГТУ.

## 10. Обработка ошибок

- Парсер: sanity check + откат транзакции (7.1); сайт показывает последние корректные данные.
- API недоступен: web отдаёт закэшированные ISR-страницы; для некэшированных — страница ошибки в стиле сайта.
- Нет данных (межсезонье, нет ближайшего матча): блок скрывается.
- Свои страницы 404 и 500 по стилистике макетов.
- Битый `content/`: деплой падает с указанием файла и поля.

## 11. Тестирование

- **Парсеры:** pytest на сохранённых HTML-фикстурах (в т.ч. текущая страница заявки join.football).
  Ежедневный canary-job в CI запрашивает живые страницы и проверяет, что парсинг не сломался.
- **core.stats / core.matching:** юнит-тесты, включая крайние случаи (автогол, равенство в лидерах, серия без поражений через сезоны, неоднозначная склейка).
- **pipeline:** интеграционные тесты на Postgres (testcontainers): upsert, откат при sanity-fail, приоритет `content/`.
- **api:** pytest + httpx на тестовой БД; контракт сверяется с сгенерированными TS-типами.
- **web:** Vitest (склонения отсчёта, форматирование дат по Москве); Playwright smoke по MVP-страницам
  с проверкой title, description, canonical и JSON-LD; Lighthouse CI (SEO ≥ 95, Performance ≥ 85 mobile).

## 12. Деплой и эксплуатация

- VPS Timeweb, Ubuntu LTS, docker-compose: `web`, `api`, `worker`, `postgres`, `nginx`, `certbot`.
- До покупки домена — доступ по IP, `noindex` на всём сайте (чтобы не проиндексировался IP-адрес).
  После: `SITE_URL` + DNS → выпуск сертификата → снятие `noindex` → подключение сервисов из 9.3.
- CI (GitHub Actions): ruff, mypy, pytest, tsc, eslint, vitest, playwright → сборка образов → GHCR →
  ssh на VPS → `docker compose pull && up -d` → `alembic upgrade head` → синк `content/`.
- Бэкап: ежедневный `pg_dump` в Timeweb S3, хранение 14 дней; скрипт восстановления в `deploy/`.
- Секреты — `.env` на сервере и GitHub Secrets: пароль БД, токен бота и chat_id, `REVALIDATE_SECRET`,
  `INTERNAL_API_TOKEN`, ключ IndexNow, ключи S3.

## 13. Первые проверки (до основной работы)

1. Доступ к lfl.ru с IP VPS и структура страницы клуба. Нет доступа — ЛФЛ через `content/matches/*.yaml`.
2. Какие данные о матчах (счёт, авторы голов) отдают разрешённые страницы `/tournament/...` join.football.
   Недостаточно — авторы голов вносятся вручную в `content/matches/*.yaml`, агрегаты игроков берутся из заявки.

## 14. Вне скоупа

- Админ-панель.
- Фэнтази-лига (бэклог: `/fantasy` с iframe).
- Автоимпорт постов из Telegram/VK (кандидат на v3+; пока посты добавляются как новости с `tag: social`).
- Мультиязычность.
