# 03. Модель данных

Все данные — JSON-файлы в `data/`. Сайт собирается из них статически; обновление = правка JSON и пересборка. Примеры — в `data/` (имена, счета и цифры там — **заглушки**).

Принцип: **хранить факты, считать производное.** Голы, ассисты, карточки и MVP хранятся только в событиях матчей; статистика игроков, лидеры, форма и рекорды вычисляются при сборке.

## Файлы

| Файл | Содержимое |
|---|---|
| `club.json` | Клуб: название, год основания, соцсети, контакты, тренировки, «ищем», игрок месяца |
| `tournaments.json` | Справочник турниров |
| `seasons.json` | Сезоны и итоговые места |
| `players.json` | Игроки (действующие и бывшие) |
| `staff.json` | Штаб и руководство |
| `matches.json` | Матчи с составами и событиями |
| `standings.json` | Таблица ЛФЛ текущего сезона (вручную) |
| `news.json` | Новости и посты из соцсетей (тело — Markdown) |
| `media.json` | Альбомы и видео |
| `history.json` | Таймлайн, трофеи, легенды |
| `fantasy.json` | Данные для страницы Бауманской лиги (правила, ссылки) |

## Сущности

### Club
```ts
{
  name: "Бауман Юнайтед",
  founded: number | null,
  city: "Москва",
  university: "МГТУ им. Н. Э. Баумана",
  format: "8x8",
  defaultFormation: "3-3-1",
  socials: { telegram?: url, vk?: url, youtube?: url, lfl?: url, fantasy?: url },
  contacts: { captainName, captainTelegram, email },
  training: { days: string, time: string, place: string, mapUrl?: url },
  homeVenue: Venue,
  lookingFor: string[],            // ["Вратаря", "Защитника ×2"]
  playerOfMonth?: { playerId, month: "2026-10", stat: string }
}
```

### Venue
```ts
{ name: string, address: string, mapUrl?: url }
```

### Tournament
```ts
{ id: "lfl" | "bauman-league" | "mgtu-cup" | string, name: string, short: string, kind: "league" | "cup" | "friendly" }
```

### Season
```ts
{ id: "2026-27", label: "2026/27", start: date, end: date, finalPlace?: string }
```

### Player
```ts
{
  id: "artem-kovalev",            // slug, он же URL
  number: 10,
  firstName, lastName, nickname?: "Мотор",
  position: "GK" | "DF" | "MF" | "FW",
  role?: "Опорный / центральный",
  foot?: "Правая" | "Левая" | "Обе",
  faculty?: "ИУ7",
  joined: 2022,
  active: boolean,
  isCaptain?: boolean,
  photo?: path, photos?: path[],
  fact?: string,
  achievements?: { title, subtitle, icon: "cup" | "medal" | "star" }[]
}
```

### Match
```ts
{
  id: "2026-10-11-energiya",       // slug, он же URL
  season: "2026-27",
  tournament: "lfl",
  round?: "7 тур",
  kickoff: "2026-10-11T14:00:00+03:00",   // всегда с таймзоной Москвы
  home: boolean,                   // мы дома?
  venue: Venue,
  opponent: { name: string, logo?: path },
  status: "scheduled" | "live" | "finished" | "cancelled",
  score?: { us: number, them: number },
  lineup?: {
    formation: "3-3-1",
    starters: { playerId, slot: Slot }[],   // 8 игроков
    bench: { playerId }[]
  },
  events?: MatchEvent[],
  mvp?: { playerId: string, votes?: Record<playerId, number> },
  reportNewsId?: string,
  streamUrl?: url,                 // трансляция (VK Видео / YouTube)
  videoUrl?: url,                  // запись
  albumId?: string
}
```

### MatchEvent
```ts
{ minute: number, type: "goal" | "own_goal" | "penalty" | "yellow" | "red" | "sub",
  team: "us" | "them",
  playerId?: string,               // для team = "us"
  playerName?: string,             // для соперника — просто текст
  assistId?: string,
  inId?: string, outId?: string,   // для замен
  note?: string }                  // «штрафной», «фол в центре поля»
```

### Слоты схемы 3-3-1 (8×8)
Координаты центра игрока в % от ширины/высоты поля (ворота наши — внизу):

| Slot | Роль | left | top |
|---|---|---|---|
| `GK` | вратарь | 50 | 89 |
| `LB` | левый защитник | 20 | 70 |
| `CB` | центральный защитник | 50 | 73 |
| `RB` | правый защитник | 80 | 70 |
| `LM` | левый полузащитник | 20 | 46 |
| `CM` | центральный полузащитник | 50 | 50 |
| `RM` | правый полузащитник | 80 | 46 |
| `ST` | нападающий | 50 | 22 |

Другие схемы (3-2-2, 2-3-2, 3-1-3) — добавить словарь `formations` с теми же полями; рендер не меняется.

### Standing (строка таблицы ЛФЛ)
```ts
{ updatedAt: date, source: url, rows: { pos, team, played, won, drawn, lost, gf, ga, pts, isUs?: boolean }[] }
```

### News
```ts
{ id: slug, date, tag: "match" | "club" | "transfer" | "fantasy" | "social",
  title, lead?, body?: markdown, cover?: path,
  source?: { platform: "telegram" | "vk" | "youtube", url },
  matchId?: string, featured?: boolean }
```

### Media
```ts
albums: { id, title, cover, date?, matchId?, photos: { src, w, h, alt? }[] }[]
videos: { id, title, meta, url, embedUrl, duration, thumb?, matchId?, kind: "full" | "highlights" | "interview" | "moment" }[]
```

### History
```ts
timeline: { year: string, tag, title, text, photo?, highlight: boolean }[]
trophies: { place: 1 | 2 | 3, title, season, photo? }[]
legends:  { name, years, stat, note, photo? }[]
```

## Вычисления при сборке

- **Матч сыгран игроком** = в `starters` или вышел на замену (`sub.inId`).
- **Голы / ассисты / ЖК / КК** — подсчёт событий с `team = "us"` по `playerId` / `assistId`. `own_goal` соперника засчитывается команде, но не игроку.
- **MVP** — `match.mvp.playerId`.
- **Форма** — последние 5 `finished` матчей по `kickoff`, исход по `score`.
- **Сухой матч** — `score.them === 0`.
- **Рекорды:**
  - крупнейшая победа — max(`us − them`), при равенстве — больше `us`;
  - серия без поражений — самая длинная последовательность `us ≥ them` по дате;
  - самый быстрый гол — min `minute` среди `goal` с `team = "us"`;
  - больше всех матчей — max по «сыгран игроком» за всё время.
- **Лидеры сезона** — топ по голам / ассистам / MVP за текущий сезон; при равенстве — меньше матчей выше.
- **Сезоны (график)** — сумма `us` и `them` по сезону + `seasons[].finalPlace`.
- **Цифры клуба** — `club.founded`, количество `finished` матчей, сумма `us`, количество `trophies` с `place = 1`.
