# План 2: web MVP (Next.js) и техническое SEO

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MVP-страницы сайта по макетам из `design/artboards/` на Next.js, с полным серверным HTML, метаданными, JSON-LD, sitemap/robots, OG-картинками и on-demand revalidation от воркера.

**Architecture:** `web/` — Next.js 16 App Router (TypeScript, CSS Modules). Все данные — из FastAPI (`BU_API_URL`) через типизированный клиент `src/lib/api.ts`; `fetch` кешируется Data Cache с тегами (`revalidate: 300`), воркер сбрасывает теги через `POST /api/revalidate`. Страницы рендерятся на сервере на каждый запрос (`dynamic = "force-dynamic"`), чтобы сборка не зависела от доступности API; повторные запросы обслуживаются из Data Cache. Серверные компоненты по умолчанию; клиентские — только отсчёт, бургер-меню, фильтры.

**Tech Stack:** Next.js 16.3, React 19, TypeScript 5, CSS Modules, `next/font/google` (Oswald, Manrope, кириллица, self-host при сборке), `react-markdown`, `openapi-typescript`, `schema-dts`, Vitest + Testing Library, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-15-bauman-united-site-design.md` (разделы 6, 9, 10, 11). Макеты и ТЗ по блокам: `design/artboards/*.dc.html`, `design/package/docs/01-spec.md`, `design/package/docs/02-design-system.md`, токены `design/tokens.css`.

## Global Constraints

- Node 20+, pnpm. Все команды фронта — из `web/`: `pnpm <script>`.
- Версии: `next@16.3.8`, `react@19.2.x`/`react-dom@19.2.x` (совместимые с next 16.3), `typescript@5.x`. Если указанная версия не ставится — ближайшая patch-версия той же minor, с записью Ruling.
- Next 16: `params` и `searchParams` страниц — `Promise`; `revalidateTag(tag, "max")`; `middleware` не используем.
- Стиль строго ч/б по `02-design-system.md`; `border-radius: 0` кроме круглых бейджей; перенос стилей из артбордов 1:1 в CSS Modules (inline-стили артбордов → классы).
- Цели касания ≥ 44px; иконочные кнопки с `aria-label`; декоративные SVG `aria-hidden="true"`; исходы матчей подписаны буквой и `aria-label`, не только цветом; `prefers-reduced-motion` отключает анимации.
- Время показывается по Москве (`Europe/Moscow`); API уже отдаёт `+03:00`.
- Даты рождения не выводятся нигде.
- Навигация MVP: Матчи, Таблицы, Команда, Новости, О клубе; кнопка «Хочу в команду». Разделы v2 (Статистика, История, Медиа) и фэнтази в меню не показываем, пока страниц нет.
- `BU_SITE_URL` — канонический origin; `BU_NOINDEX=1` (по умолчанию до покупки домена) → `robots: noindex, nofollow` на всех страницах и `Disallow: /` в robots.txt.
- Title-шаблон: `{Страница} — Бауман Юнайтед | футбольная команда МГТУ им. Баумана`; главная: `Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана`.

## Review Focus

1. Пустая база (нет матчей/игроков/новостей, межсезонье): каждая страница рендерится без падений, пустые блоки скрываются — e2e на пустом API в Task 11.
2. API недоступен или 5xx: пользователь видит страницу ошибки в стиле сайта, а не белый экран; несуществующий slug → 404 по макету — тесты в Task 4 и Task 7.
3. Фильтры `/matches` с мусорными значениями в query (`?where=xxx&t=`) не роняют страницу и получают `noindex` + canonical без query — тест в Task 6.
4. `POST /api/revalidate` без правильного секрета не сбрасывает кеш (401) — тест в Task 2.
5. Длинные кириллические имена соперников/игроков не ломают сетку на 375px (нет горизонтального скролла страницы) — проверка в Playwright mobile в Task 11.

---

### Task 1: Каркас `web/`, токены, шрифты, API-клиент, форматирование

**Files:**
- Create: `web/package.json`, `web/tsconfig.json`, `web/next.config.ts`, `web/vitest.config.ts`, `web/vitest.setup.ts`, `web/eslint.config.mjs`, `web/.gitignore`
- Create: `web/src/app/globals.css`, `web/src/app/fonts.ts`
- Create: `web/src/lib/api-types.ts` (генерируется), `web/src/lib/types.ts`, `web/src/lib/api.ts`, `web/src/lib/format.ts`
- Test: `web/src/lib/format.test.ts`, `web/src/lib/api.test.ts`
- Move: `web/openapi.json` (уже есть) — источник для `api-types.ts`

**Interfaces:**
- Produces:
  - `api.ts`: `class ApiError extends Error { status: number }`; `apiGet<T>(path: string, opts?: { tags?: string[]; query?: Record<string, string | undefined> }): Promise<T>`; `apiGetOrNull<T>(...)` (404 → `null`); типизированные обёртки: `getHome(): Promise<Home>`, `getMatches(q: MatchQuery): Promise<MatchSummary[]>`, `getMatch(slug): Promise<MatchDetail | null>`, `getPlayers(): Promise<PlayerCard[]>`, `getPlayer(slug): Promise<PlayerDetail | null>`, `getNews(q: {tag?: string; page?: number}): Promise<NewsPage>`, `getNewsItem(slug): Promise<NewsDetail | null>`, `getStandings(tournament?: string): Promise<Standings[]>`, `getClub(): Promise<Club>`, `getSeasons(): Promise<Season[]>`, `getTournaments(season?: string): Promise<Tournament[]>`, `getSitemap(): Promise<SitemapItem[]>`.
  - `types.ts`: ре-экспорт сгенерированных схем (`MatchSummary`, `MatchDetail`, `PlayerCard`, `PlayerDetail`, `NewsCard`, `NewsDetail`, `NewsPage`, `TournamentOut as Tournament`, `StandingsOut as Standings`, `SeasonOut as Season`, `EventOut`) + ручные типы для нетипизированных ответов: `Home`, `Club`, `SitemapItem`, `Leader`, `FormItem`, `Totals`.
  - `format.ts`: `plural(n, [one, few, many])`, `formatDate(iso)` → «6 сентября 2026», `formatDateShort(iso)` → «06.09», `formatTime(iso)` → «20:30», `formatWeekday(iso)` → «вс», `outcomeLabel(o)` → «Победа»/«Ничья»/«Поражение», `outcomeLetter(o)` → «В»/«Н»/«П», `countdownParts(targetIso, nowMs)` → `{days, hours, minutes, started: boolean, over: boolean}`, `positionLabel(pos)` → «Вратарь»…, `positionGroup(pos)` → «Вратари»…

- [ ] **Step 1: `web/package.json`**

```json
{
  "name": "bu-web",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start --port 3000",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "e2e": "playwright test",
    "gen:api": "openapi-typescript openapi.json -o src/lib/api-types.ts"
  },
  "dependencies": {
    "next": "16.3.8",
    "react": "19.2.0",
    "react-dom": "19.2.0",
    "react-markdown": "^10.1.0"
  },
  "devDependencies": {
    "@playwright/test": "^1.56.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.3.0",
    "@types/node": "^22",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "@vitejs/plugin-react": "^5.0.0",
    "eslint": "^9",
    "eslint-config-next": "16.3.8",
    "jsdom": "^26.0.0",
    "openapi-typescript": "^7.9.0",
    "schema-dts": "^1.1.5",
    "typescript": "^5.8",
    "vitest": "^3.2.0"
  }
}
```

(Если `pnpm install` не находит точную версию react, взять ту, что требует `next@16.3.8` в peerDependencies, — Ruling.)

`web/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "es2023"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] },
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules", "e2e"]
}
```

`web/next.config.ts`:
```ts
import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [{ protocol: "https", hostname: "st.joinsport.io" }],
  },
};

export default config;
```

`web/vitest.config.ts`:
```ts
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
```

`web/vitest.setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
```

`web/eslint.config.mjs`:
```js
import next from "eslint-config-next";

export default [...next, { ignores: [".next/**", "src/lib/api-types.ts", "e2e/.auth/**"] }];
```

`web/.gitignore`:
```
node_modules/
.next/
test-results/
playwright-report/
next-env.d.ts
```

Run: `cd web && pnpm install && pnpm gen:api`
Expected: установлено; создан `src/lib/api-types.ts`.

- [ ] **Step 2: Падающие тесты `format.ts` и `api.ts`**

`web/src/lib/format.test.ts`:
```ts
import {
  countdownParts,
  formatDate,
  formatDateShort,
  formatTime,
  outcomeLabel,
  outcomeLetter,
  plural,
  positionGroup,
  positionLabel,
} from "./format";

describe("plural", () => {
  it.each([
    [1, "день"], [2, "дня"], [5, "дней"], [11, "дней"], [21, "день"], [22, "дня"], [0, "дней"],
  ])("%i → %s", (n, word) => {
    expect(plural(n, ["день", "дня", "дней"])).toBe(word);
  });
});

describe("dates in Moscow", () => {
  const iso = "2026-09-06T20:30:00+03:00";
  it("formats", () => {
    expect(formatDate(iso)).toBe("6 сентября 2026");
    expect(formatDateShort(iso)).toBe("06.09");
    expect(formatTime(iso)).toBe("20:30");
  });
  it("uses Moscow time regardless of input offset", () => {
    expect(formatTime("2026-09-06T17:30:00Z")).toBe("20:30");
  });
});

describe("outcome", () => {
  it("labels", () => {
    expect(outcomeLabel("W")).toBe("Победа");
    expect(outcomeLetter("D")).toBe("Н");
    expect(outcomeLetter("L")).toBe("П");
  });
});

describe("countdownParts", () => {
  const target = Date.parse("2026-10-24T20:30:00+03:00");
  it("splits remaining time", () => {
    const now = target - (2 * 86400 + 17 * 3600 + 5 * 60) * 1000;
    expect(countdownParts(new Date(target).toISOString(), now)).toEqual({
      days: 2, hours: 17, minutes: 5, started: false, over: false,
    });
  });
  it("started and over", () => {
    expect(countdownParts(new Date(target).toISOString(), target + 60_000).started).toBe(true);
    expect(countdownParts(new Date(target).toISOString(), target + 3 * 3600_000).over).toBe(true);
  });
});

describe("positions", () => {
  it("labels and groups", () => {
    expect(positionLabel("GK")).toBe("Вратарь");
    expect(positionGroup("FW")).toBe("Нападающие");
    expect(positionLabel(null)).toBe("Игрок");
  });
});
```

`web/src/lib/api.test.ts`:
```ts
import { ApiError, apiGet, apiGetOrNull } from "./api";

const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

describe("api client", () => {
  beforeEach(() => {
    process.env.BU_API_URL = "http://api.test";
  });
  afterEach(() => vi.restoreAllMocks());

  it("builds url with query, skips empty params and passes cache tags", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(ok([]));
    await apiGet("/matches", { tags: ["matches"], query: { season: "2026-27", where: undefined, t: "" } });
    const [url, init] = spy.mock.calls[0] as [string, RequestInit & { next: unknown }];
    expect(url).toBe("http://api.test/matches?season=2026-27");
    expect(init.next).toEqual({ revalidate: 300, tags: ["matches"] });
  });

  it("404 → null in apiGetOrNull, other errors throw ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("", { status: 404 }));
    expect(await apiGetOrNull("/matches/x")).toBeNull();
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("", { status: 502 }));
    await expect(apiGet("/home")).rejects.toBeInstanceOf(ApiError);
  });
});
```

Run: `pnpm test`
Expected: FAIL (модулей нет).

- [ ] **Step 3: Реализация `format.ts`, `types.ts`, `api.ts`**

`web/src/lib/format.ts`:
```ts
const TZ = "Europe/Moscow";

export type Outcome = "W" | "D" | "L";
export type Position = "GK" | "DF" | "MF" | "FW";

export function plural(n: number, forms: [string, string, string]): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return forms[0];
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return forms[1];
  return forms[2];
}

function parts(iso: string, opts: Intl.DateTimeFormatOptions): Record<string, string> {
  const out: Record<string, string> = {};
  for (const p of new Intl.DateTimeFormat("ru-RU", { timeZone: TZ, ...opts }).formatToParts(new Date(iso))) {
    out[p.type] = p.value;
  }
  return out;
}

export function formatDate(iso: string): string {
  const p = parts(iso, { day: "numeric", month: "long", year: "numeric" });
  return `${p.day} ${p.month} ${p.year}`;
}

export function formatDateShort(iso: string): string {
  const p = parts(iso, { day: "2-digit", month: "2-digit" });
  return `${p.day}.${p.month}`;
}

export function formatTime(iso: string): string {
  const p = parts(iso, { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  return `${p.hour}:${p.minute}`;
}

export function formatWeekday(iso: string): string {
  return parts(iso, { weekday: "short" }).weekday;
}

export function outcomeLabel(o: Outcome): string {
  return { W: "Победа", D: "Ничья", L: "Поражение" }[o];
}

export function outcomeLetter(o: Outcome): string {
  return { W: "В", D: "Н", L: "П" }[o];
}

export function countdownParts(targetIso: string, nowMs: number) {
  const target = Date.parse(targetIso);
  const diff = target - nowMs;
  const started = diff <= 0;
  const over = nowMs > target + 2 * 3600_000;
  const left = Math.max(0, diff);
  const totalMinutes = Math.floor(left / 60_000);
  return {
    days: Math.floor(totalMinutes / 1440),
    hours: Math.floor((totalMinutes % 1440) / 60),
    minutes: totalMinutes % 60,
    started,
    over,
  };
}

const POSITION: Record<Position, [string, string]> = {
  GK: ["Вратарь", "Вратари"],
  DF: ["Защитник", "Защитники"],
  MF: ["Полузащитник", "Полузащитники"],
  FW: ["Нападающий", "Нападающие"],
};

export function positionLabel(pos: string | null | undefined): string {
  return pos && pos in POSITION ? POSITION[pos as Position][0] : "Игрок";
}

export function positionGroup(pos: string | null | undefined): string {
  return pos && pos in POSITION ? POSITION[pos as Position][1] : "Без позиции";
}
```

`web/src/lib/types.ts`:
```ts
import type { components } from "./api-types";

type S = components["schemas"];
export type MatchSummary = S["MatchSummary"];
export type MatchDetail = S["MatchDetail"];
export type EventOut = S["EventOut"];
export type PlayerCard = S["PlayerCard"];
export type PlayerDetail = S["PlayerDetail"];
export type PlayerStats = S["PlayerStats"];
export type NewsCard = S["NewsCard"];
export type NewsDetail = S["NewsDetail"];
export type NewsPage = S["NewsPage"];
export type Tournament = S["TournamentOut"];
export type Standings = S["StandingsOut"];
export type StandingRow = S["StandingRowOut"];
export type Season = S["SeasonOut"];

export type Outcome = "W" | "D" | "L";

export interface FormItem { slug: string; outcome: Outcome; us: number; them: number }
export interface Totals {
  played?: number; won?: number; drawn?: number; lost?: number;
  gf?: number; ga?: number; clean_sheets?: number;
}
export interface Leader { slug: string; name: string; value: number; played: number }
export interface PlayerOfMonth { player: string; month?: string; stat?: string; slug: string; name: string; photo?: string | null }

export interface Home {
  next_match: MatchSummary | null;
  last_match: MatchDetail | null;
  form: FormItem[];
  totals: Totals;
  standings: Standings | null;
  news: NewsCard[];
  leaders: { goals: Leader | null; assists: Leader | null; player_of_month: PlayerOfMonth | null };
  numbers: { founded?: number | null; matches?: number; goals?: number; trophies?: number };
  live: MatchSummary | null;
}

export interface Club {
  name: string;
  name_en?: string;
  founded?: number | null;
  city?: string;
  university?: string;
  format?: string;
  primary_tournament?: string | null;
  socials?: Partial<Record<"telegram" | "vk" | "youtube" | "lfl" | "joinfootball", string | null>>;
  contacts?: { captain_name?: string | null; captain_telegram?: string | null; email?: string | null };
  training?: { days?: string | null; time?: string | null; place?: string | null; map_url?: string | null };
  looking_for?: string[];
  about?: string;
}

export interface SitemapItem { path: string; lastmod: string | null }
```

`web/src/lib/api.ts`:
```ts
import "server-only";

import type {
  Club, Home, MatchDetail, MatchSummary, NewsDetail, NewsPage, PlayerCard, PlayerDetail,
  Season, SitemapItem, Standings, Tournament,
} from "./types";

export const REVALIDATE_SECONDS = 300;

export class ApiError extends Error {
  constructor(public status: number, path: string) {
    super(`API ${status} for ${path}`);
  }
}

type Query = Record<string, string | undefined>;

function url(path: string, query?: Query): string {
  const base = process.env.BU_API_URL ?? "http://localhost:8000";
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) if (v) params.set(k, v);
  const qs = params.toString();
  return `${base}${path}${qs ? `?${qs}` : ""}`;
}

export async function apiGet<T>(path: string, opts: { tags?: string[]; query?: Query } = {}): Promise<T> {
  const res = await fetch(url(path, opts.query), {
    next: { revalidate: REVALIDATE_SECONDS, tags: opts.tags ?? [] },
  } as RequestInit);
  if (!res.ok) throw new ApiError(res.status, path);
  return (await res.json()) as T;
}

export async function apiGetOrNull<T>(path: string, opts: { tags?: string[]; query?: Query } = {}): Promise<T | null> {
  try {
    return await apiGet<T>(path, opts);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

export interface MatchQuery { season?: string; tournament?: string; where?: "home" | "away"; status?: string }

export const getHome = () => apiGet<Home>("/home", { tags: ["home"] });
export const getMatches = (q: MatchQuery = {}) =>
  apiGet<MatchSummary[]>("/matches", { tags: ["matches"], query: { ...q } });
export const getMatch = (slug: string) =>
  apiGetOrNull<MatchDetail>(`/matches/${encodeURIComponent(slug)}`, { tags: ["matches", `match:${slug}`] });
export const getPlayers = () => apiGet<PlayerCard[]>("/players", { tags: ["players"], query: { active: "true" } });
export const getPlayer = (slug: string) =>
  apiGetOrNull<PlayerDetail>(`/players/${encodeURIComponent(slug)}`, { tags: ["players", `player:${slug}`] });
export const getNews = (q: { tag?: string; page?: number } = {}) =>
  apiGet<NewsPage>("/news", { tags: ["news"], query: { tag: q.tag, page: q.page ? String(q.page) : undefined } });
export const getNewsItem = (slug: string) =>
  apiGetOrNull<NewsDetail>(`/news/${encodeURIComponent(slug)}`, { tags: ["news", `news:${slug}`] });
export const getStandings = (tournament?: string) =>
  apiGet<Standings[]>("/standings", { tags: ["standings"], query: { tournament } });
export const getClub = () => apiGet<Club>("/club", { tags: ["club"] });
export const getSeasons = () => apiGet<Season[]>("/seasons", { tags: ["matches"] });
export const getTournaments = (season?: string) =>
  apiGet<Tournament[]>("/tournaments", { tags: ["matches"], query: { season } });
export const getSitemap = () => apiGet<SitemapItem[]>("/sitemap", { tags: ["matches", "players", "news"] });
```

Для работы `import "server-only"` в Vitest добавить в `vitest.config.ts` → `resolve.alias`: `"server-only": fileURLToPath(new URL("./src/test/server-only.ts", import.meta.url))` и создать пустой `web/src/test/server-only.ts` (`export {};`); добавить `server-only` в dependencies.

- [ ] **Step 4: Глобальные стили и шрифты**

`web/src/app/fonts.ts`:
```ts
import { Manrope, Oswald } from "next/font/google";

export const oswald = Oswald({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-oswald",
  display: "swap",
});

export const manrope = Manrope({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-manrope",
  display: "swap",
});
```

`web/src/app/globals.css` — содержимое `design/tokens.css` целиком, с двумя заменами в `:root`:
```css
  --f-display: var(--font-oswald), 'Arial Narrow', sans-serif;
  --f-body: var(--font-manrope), system-ui, sans-serif;
```
и дополнениями в конце:
```css
*, *::before, *::after { box-sizing: border-box; }
body { background: var(--c-ink); color: var(--c-paper); min-height: 100vh; overflow-x: hidden; }
img { max-width: 100%; display: block; }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.eyebrow { font-family: var(--f-display); font-size: var(--fs-label); letter-spacing: var(--ls-eyebrow); text-transform: uppercase; color: var(--c-muted); }
.section--paper .eyebrow { color: var(--c-muted-on-paper); }
.table-scroll { overflow-x: auto; }
```

- [ ] **Step 5: Тесты зелёные, линт, типы**

Run: `pnpm test && pnpm typecheck && pnpm lint`
Expected: PASS (typecheck может ругаться на отсутствие `src/app` страниц — допустимо до Task 4; если `tsc` требует `next-env.d.ts`, выполнить `pnpm next typegen` или создать файл по шаблону Next).

- [ ] **Step 6: Commit**

```bash
git add web && git commit -m "feat(web): Next.js scaffold, tokens, fonts, typed API client, formatters"
```

---

### Task 2: SEO-ядро: метаданные, JSON-LD, robots, sitemap, revalidate

**Files:**
- Create: `web/src/lib/seo.ts`, `web/src/lib/jsonld.ts`, `web/src/components/JsonLd.tsx`
- Create: `web/src/app/robots.ts`, `web/src/app/sitemap.ts`, `web/src/app/api/revalidate/route.ts`
- Test: `web/src/lib/seo.test.ts`, `web/src/lib/jsonld.test.ts`, `web/src/app/api/revalidate/route.test.ts`

**Interfaces:**
- Consumes: `types.ts`, `format.ts` (Task 1).
- Produces:
  - `seo.ts`: `siteUrl(): string` (из `BU_SITE_URL`, без завершающего `/`), `isNoindex(): boolean` (`BU_NOINDEX !== "0"`), `SITE_NAME = "Бауман Юнайтед"`, `pageTitle(title?: string): string`, `buildMetadata({ title?, description, path, image?, noindex?, type? }): Metadata` — canonical `${siteUrl()}${path}`, OpenGraph (`locale: "ru_RU"`, `siteName`), Twitter `summary_large_image`, robots.
  - `jsonld.ts`: `sportsTeamLd(club: Club)`, `sportsEventLd(m: MatchDetail | MatchSummary)`, `personLd(p: PlayerDetail)`, `newsArticleLd(n: NewsDetail)`, `breadcrumbsLd(items: {name: string; path: string}[])` — возвращают объекты с `@context: "https://schema.org"`.
  - `<JsonLd data={obj} />` — `<script type="application/ld+json">` с экранированием `<`.
  - `POST /api/revalidate` с `Authorization: Bearer <BU_REVALIDATE_SECRET>` и телом `{ tags: string[] }` → `revalidateTag(tag, "max")` для каждого, ответ `{ revalidated: tags }`; неверный секрет → 401; секрет не задан → 503.

- [ ] **Step 1: Падающие тесты**

`web/src/lib/seo.test.ts`:
```ts
import { buildMetadata, pageTitle, siteUrl } from "./seo";

describe("seo", () => {
  beforeEach(() => {
    process.env.BU_SITE_URL = "https://baumanunited.ru/";
    process.env.BU_NOINDEX = "1";
  });

  it("titles", () => {
    expect(pageTitle()).toBe("Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана");
    expect(pageTitle("Матчи")).toBe("Матчи — Бауман Юнайтед | футбольная команда МГТУ им. Баумана");
  });

  it("canonical, og and noindex", () => {
    expect(siteUrl()).toBe("https://baumanunited.ru");
    const m = buildMetadata({ title: "Матчи", description: "Календарь", path: "/matches" });
    expect(m.alternates?.canonical).toBe("https://baumanunited.ru/matches");
    expect(m.openGraph).toMatchObject({ locale: "ru_RU", url: "https://baumanunited.ru/matches" });
    expect(m.robots).toMatchObject({ index: false, follow: false });
  });

  it("indexable when BU_NOINDEX=0 unless page asks noindex", () => {
    process.env.BU_NOINDEX = "0";
    expect(buildMetadata({ description: "x", path: "/" }).robots).toMatchObject({ index: true });
    expect(buildMetadata({ description: "x", path: "/m", noindex: true }).robots).toMatchObject({ index: false, follow: true });
  });
});
```

`web/src/lib/jsonld.test.ts`:
```ts
import { breadcrumbsLd, sportsEventLd, sportsTeamLd } from "./jsonld";

describe("json-ld", () => {
  beforeEach(() => { process.env.BU_SITE_URL = "https://baumanunited.ru"; });

  it("SportsTeam with university and sameAs", () => {
    const ld = sportsTeamLd({
      name: "Бауман Юнайтед", name_en: "Bauman United", university: "МГТУ им. Н. Э. Баумана",
      city: "Москва", socials: { telegram: "https://t.me/x", vk: null, lfl: "https://lfl.ru/club14270" },
    });
    expect(ld).toMatchObject({
      "@context": "https://schema.org", "@type": "SportsTeam", sport: "Football",
      alternateName: "Bauman United",
      memberOf: { "@type": "CollegeOrUniversity", name: "МГТУ им. Н. Э. Баумана" },
      sameAs: ["https://t.me/x", "https://lfl.ru/club14270"],
    });
  });

  it("SportsEvent for away match", () => {
    const ld = sportsEventLd({
      slug: "2026-10-24-messiya", kickoff: "2026-10-24T21:30:00+03:00", home: false,
      opponent_name: "Мессия", status: "scheduled", venue_name: "Металлург", venue_address: "Москва",
      tournament: { name: "Лига Инженеров · Осень 2026" }, round: "6 тур",
    } as never);
    expect(ld).toMatchObject({
      "@type": "SportsEvent", startDate: "2026-10-24T21:30:00+03:00",
      homeTeam: { name: "Мессия" }, awayTeam: { name: "Бауман Юнайтед" },
      eventStatus: "https://schema.org/EventScheduled",
      url: "https://baumanunited.ru/matches/2026-10-24-messiya",
    });
  });

  it("breadcrumbs", () => {
    const ld = breadcrumbsLd([{ name: "Команда", path: "/team" }, { name: "Королев", path: "/team/a" }]);
    expect(ld.itemListElement[1]).toMatchObject({ position: 2, item: "https://baumanunited.ru/team/a" });
  });
});
```

`web/src/app/api/revalidate/route.test.ts`:
```ts
const revalidateTag = vi.fn();
vi.mock("next/cache", () => ({ revalidateTag }));

import { POST } from "./route";

const req = (auth: string | null, body: unknown) =>
  new Request("http://x/api/revalidate", {
    method: "POST",
    headers: auth ? { authorization: auth, "content-type": "application/json" } : { "content-type": "application/json" },
    body: JSON.stringify(body),
  });

describe("POST /api/revalidate", () => {
  beforeEach(() => { revalidateTag.mockReset(); process.env.BU_REVALIDATE_SECRET = "s3"; });

  it("rejects wrong secret", async () => {
    const res = await POST(req("Bearer nope", { tags: ["home"] }));
    expect(res.status).toBe(401);
    expect(revalidateTag).not.toHaveBeenCalled();
  });

  it("revalidates tags", async () => {
    const res = await POST(req("Bearer s3", { tags: ["home", "matches"] }));
    expect(res.status).toBe(200);
    expect(revalidateTag).toHaveBeenCalledWith("home", "max");
    expect(revalidateTag).toHaveBeenCalledWith("matches", "max");
  });

  it("503 when secret not configured", async () => {
    delete process.env.BU_REVALIDATE_SECRET;
    expect((await POST(req("Bearer s3", { tags: [] }))).status).toBe(503);
  });
});
```

Run: `pnpm test` → FAIL.

- [ ] **Step 2: Реализация**

`web/src/lib/seo.ts`:
```ts
import type { Metadata } from "next";

export const SITE_NAME = "Бауман Юнайтед";
const HOME_TITLE = "Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана";
const SUFFIX = "Бауман Юнайтед | футбольная команда МГТУ им. Баумана";

export function siteUrl(): string {
  return (process.env.BU_SITE_URL ?? "http://localhost:3000").replace(/\/+$/, "");
}

export function isNoindex(): boolean {
  return process.env.BU_NOINDEX !== "0";
}

export function pageTitle(title?: string): string {
  return title ? `${title} — ${SUFFIX}` : HOME_TITLE;
}

export function buildMetadata(opts: {
  title?: string;
  description: string;
  path: string;
  image?: string;
  noindex?: boolean;
  type?: "website" | "article" | "profile";
}): Metadata {
  const url = `${siteUrl()}${opts.path}`;
  const title = pageTitle(opts.title);
  const blocked = isNoindex();
  return {
    title: { absolute: title },
    description: opts.description,
    alternates: { canonical: url },
    openGraph: {
      type: opts.type ?? "website",
      locale: "ru_RU",
      siteName: SITE_NAME,
      url,
      title,
      description: opts.description,
      ...(opts.image ? { images: [{ url: opts.image, width: 1200, height: 630 }] } : {}),
    },
    twitter: { card: "summary_large_image", title, description: opts.description },
    robots: blocked
      ? { index: false, follow: false }
      : opts.noindex
        ? { index: false, follow: true }
        : { index: true, follow: true },
  };
}
```

`web/src/lib/jsonld.ts`:
```ts
import type { Club, MatchDetail, MatchSummary, NewsDetail, PlayerDetail } from "./types";
import { SITE_NAME, siteUrl } from "./seo";

const CTX = "https://schema.org";
const UNIVERSITY = "МГТУ им. Н. Э. Баумана";

export function sportsTeamLd(club: Club) {
  const sameAs = Object.values(club.socials ?? {}).filter((v): v is string => Boolean(v));
  return {
    "@context": CTX,
    "@type": "SportsTeam",
    name: club.name ?? SITE_NAME,
    alternateName: club.name_en ?? "Bauman United",
    sport: "Football",
    url: siteUrl(),
    logo: `${siteUrl()}/icon.svg`,
    location: { "@type": "Place", address: { "@type": "PostalAddress", addressLocality: club.city ?? "Москва", addressCountry: "RU" } },
    memberOf: { "@type": "CollegeOrUniversity", name: club.university ?? UNIVERSITY },
    ...(club.founded ? { foundingDate: String(club.founded) } : {}),
    sameAs,
  };
}

const STATUS: Record<string, string> = {
  scheduled: "https://schema.org/EventScheduled",
  live: "https://schema.org/EventScheduled",
  finished: "https://schema.org/EventCompleted",
  cancelled: "https://schema.org/EventCancelled",
};

export function sportsEventLd(m: MatchSummary | MatchDetail) {
  const us = { "@type": "SportsTeam", name: SITE_NAME };
  const them = { "@type": "SportsTeam", name: m.opponent_name };
  const home = m.home ? us : them;
  const away = m.home ? them : us;
  return {
    "@context": CTX,
    "@type": "SportsEvent",
    name: `${home.name} — ${away.name}`,
    sport: "Football",
    startDate: m.kickoff,
    eventStatus: STATUS[m.status] ?? STATUS.scheduled,
    homeTeam: home,
    awayTeam: away,
    url: `${siteUrl()}/matches/${m.slug}`,
    location: { "@type": "Place", name: m.venue_name ?? "Москва", address: m.venue_address ?? "Москва" },
    superEvent: { "@type": "SportsEvent", name: m.tournament.name },
    ...(m.round ? { description: `${m.tournament.name}, ${m.round}` } : {}),
  };
}

export function personLd(p: PlayerDetail) {
  return {
    "@context": CTX,
    "@type": "Person",
    name: `${p.first_name} ${p.last_name}`.trim(),
    url: `${siteUrl()}/team/${p.slug}`,
    ...(p.photo ? { image: p.photo } : {}),
    memberOf: { "@type": "SportsTeam", name: SITE_NAME },
    ...(p.nickname ? { alternateName: p.nickname } : {}),
  };
}

export function newsArticleLd(n: NewsDetail) {
  return {
    "@context": CTX,
    "@type": "NewsArticle",
    headline: n.title,
    datePublished: n.date,
    url: `${siteUrl()}/news/${n.slug}`,
    ...(n.cover ? { image: [n.cover] } : {}),
    author: { "@type": "SportsTeam", name: SITE_NAME },
    publisher: { "@type": "Organization", name: SITE_NAME, logo: { "@type": "ImageObject", url: `${siteUrl()}/icon.svg` } },
    ...(n.lead ? { description: n.lead } : {}),
  };
}

export function breadcrumbsLd(items: { name: string; path: string }[]) {
  return {
    "@context": CTX,
    "@type": "BreadcrumbList",
    itemListElement: items.map((it, i) => ({
      "@type": "ListItem", position: i + 1, name: it.name, item: `${siteUrl()}${it.path}`,
    })),
  };
}
```

`web/src/components/JsonLd.tsx`:
```tsx
export function JsonLd({ data }: { data: unknown }) {
  const json = JSON.stringify(data).replace(/</g, "\\u003c");
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json }} />;
}
```

`web/src/app/api/revalidate/route.ts`:
```ts
import { revalidateTag } from "next/cache";

export async function POST(request: Request): Promise<Response> {
  const secret = process.env.BU_REVALIDATE_SECRET;
  if (!secret) return Response.json({ error: "not configured" }, { status: 503 });
  if (request.headers.get("authorization") !== `Bearer ${secret}`) {
    return Response.json({ error: "unauthorized" }, { status: 401 });
  }
  const body = (await request.json().catch(() => ({}))) as { tags?: unknown };
  const tags = Array.isArray(body.tags) ? body.tags.filter((t): t is string => typeof t === "string") : [];
  for (const tag of tags) revalidateTag(tag, "max");
  return Response.json({ revalidated: tags });
}
```

`web/src/app/robots.ts`:
```ts
import type { MetadataRoute } from "next";
import { isNoindex, siteUrl } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  if (isNoindex()) return { rules: { userAgent: "*", disallow: "/" } };
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/"] },
    sitemap: `${siteUrl()}/sitemap.xml`,
    host: siteUrl(),
  };
}
```

`web/src/app/sitemap.ts`:
```ts
import type { MetadataRoute } from "next";
import { getSitemap } from "@/lib/api";
import { siteUrl } from "@/lib/seo";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const items = await getSitemap();
  return items.map((it) => ({
    url: `${siteUrl()}${it.path}`,
    ...(it.lastmod ? { lastModified: it.lastmod } : {}),
    changeFrequency: it.path.startsWith("/matches") || it.path === "/" ? "daily" : "weekly",
    priority: it.path === "/" ? 1 : it.path.split("/").length === 2 ? 0.8 : 0.6,
  }));
}
```

- [ ] **Step 3: Тесты зелёные**

Run: `pnpm test && pnpm typecheck`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add web && git commit -m "feat(web): metadata, JSON-LD, robots, sitemap and revalidate endpoint"
```

---

### Task 3: UI-кит по `Kit.dc.html`

**Files:**
- Create (каждый компонент — `*.tsx` + `*.module.css` в `web/src/components/ui/`): `Crest`, `Button` (`ButtonLink`), `Stripes`, `Photo` (плейсхолдер `.ph`/`.phl` или `next/image`), `FormBadge`, `ScoreBadge`, `LiveBadge`, `NewsTag`, `SectionHeader`, `Countdown` (client), `MatchCard`, `PlayerCardTile`, `NewsCardTile`, `StandingsTable`, `EmptyState`
- Create: `web/public/icon.svg` (герб из `design/package/assets/crest-placeholder.svg`)
- Test: `web/src/components/ui/ui.test.tsx`, `web/src/components/ui/Countdown.test.tsx`

**Interfaces:**
- Consumes: `format.ts`, `types.ts`.
- Produces (props):
  - `Crest({ size?: number; inverted?: boolean })` — SVG герба из шапки `Main.dc.html` (40×46), `aria-hidden`.
  - `ButtonLink({ href, children, variant?: "primary" | "secondary"; onPaper?: boolean; external?: boolean })`.
  - `Stripes({ height?: number; opacity?: number })`.
  - `Photo({ src?: string | null; alt: string; ratio?: string; light?: boolean; sizes?: string; priority?: boolean })` — без `src` рисует штриховку.
  - `FormBadge({ outcome: Outcome; us?: number; them?: number; opponent?: string; size?: "m" | "s" })` — круг с буквой, `aria-label="Победа 3:1 vs Энергия"`.
  - `ScoreBadge({ outcome: Outcome; us: number; them: number })` — `aria-label`.
  - `LiveBadge()`; `NewsTag({ tag: string; platform?: string | null })` — подписи: match «Матч», club «Клуб», transfer «Трансфер», social «Из соцсетей»/название платформы.
  - `SectionHeader({ title: string; eyebrow?: string; link?: { href: string; label: string }; as?: "h1" | "h2" })`.
  - `Countdown({ kickoff: string })` — client; блоки дни/часы/минуты со склонением; `role="timer"`, `aria-label` полным текстом; обновление раз в 60 с; после начала — «Матч идёт», после +2 ч — ничего.
  - `MatchCard({ match: MatchSummary | MatchDetail; variant: "result" | "upcoming" })` — по «Карточке матча» из Kit.
  - `PlayerCardTile({ player: PlayerCard })` — ссылка на `/team/[slug]`, фото 4:5, номер-водяной знак, на ховер/фокус — панель статистики сезона (матчи, голы, передачи, ЖК) и «Профиль →».
  - `NewsCardTile({ item: NewsCard; onPaper?: boolean })` — обычная и «пост из соцсети» (рамка, «Открыть оригинал ↗»).
  - `StandingsTable({ standings: Standings; compact?: boolean; caption?: string })` — колонки `# / Команда / И / В / Н / П / М / О` (compact: `# / Команда / И / О`), наша строка — белая; под таблицей «Обновлено {дата}» и ссылка на источник.
  - `EmptyState({ text: string })`.

- [ ] **Step 1: Падающие тесты**

`web/src/components/ui/ui.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { FormBadge } from "./FormBadge";
import { NewsTag } from "./NewsTag";
import { ScoreBadge } from "./ScoreBadge";
import { StandingsTable } from "./StandingsTable";

const standings = {
  tournament: { slug: "li", name: "Лига Инженеров", short: "ЛИ", kind: "league", season: "2026-27", url: null },
  updated_at: "2026-10-12T10:00:00+03:00",
  source_url: "https://jf/tables",
  rows: [
    { pos: 1, team_name: "Раскат", team_logo: null, played: 5, won: 5, drawn: 0, lost: 0, gf: 21, ga: 4, pts: 15, is_us: false },
    { pos: 6, team_name: "Bauman United", team_logo: null, played: 5, won: 2, drawn: 0, lost: 3, gf: 17, ga: 19, pts: 6, is_us: true },
  ],
};

describe("ui kit", () => {
  it("form badge is accessible without color", () => {
    render(<FormBadge outcome="W" us={3} them={1} opponent="Энергия" />);
    expect(screen.getByLabelText("Победа 3:1 vs Энергия")).toHaveTextContent("В");
  });

  it("score badge", () => {
    render(<ScoreBadge outcome="L" us={2} them={3} />);
    expect(screen.getByLabelText("Поражение 2:3")).toHaveTextContent("2:3");
  });

  it("news tag labels", () => {
    render(<NewsTag tag="social" platform="telegram" />);
    expect(screen.getByText("Telegram")).toBeInTheDocument();
  });

  it("standings marks our row", () => {
    render(<StandingsTable standings={standings as never} />);
    const us = screen.getByText("Bauman United").closest("tr");
    expect(us).toHaveAttribute("aria-current", "true");
    expect(screen.getByText(/Обновлено/)).toHaveTextContent("12 октября 2026");
  });
});
```

`web/src/components/ui/Countdown.test.tsx`:
```tsx
import { act, render, screen } from "@testing-library/react";
import { Countdown } from "./Countdown";

describe("Countdown", () => {
  afterEach(() => vi.useRealTimers());

  it("declines units and ticks every minute", () => {
    vi.useFakeTimers();
    const kickoff = "2026-10-24T21:30:00+03:00";
    vi.setSystemTime(Date.parse(kickoff) - (2 * 86400 + 1 * 3600 + 5 * 60) * 1000);
    render(<Countdown kickoff={kickoff} />);
    expect(screen.getByRole("timer")).toHaveAccessibleName("До матча 2 дня 1 час 5 минут");
    act(() => { vi.advanceTimersByTime(60_000); });
    expect(screen.getByRole("timer")).toHaveAccessibleName("До матча 2 дня 1 час 4 минуты");
  });

  it("shows live text after kickoff", () => {
    vi.useFakeTimers();
    vi.setSystemTime(Date.parse("2026-10-24T21:40:00+03:00"));
    render(<Countdown kickoff="2026-10-24T21:30:00+03:00" />);
    expect(screen.getByText("Матч идёт")).toBeInTheDocument();
  });
});
```

Run: `pnpm test` → FAIL.

- [ ] **Step 2: Реализация компонентов**

Для каждого компонента открыть `design/artboards/Kit.dc.html` (и `Main.dc.html` для карточек), перенести разметку и inline-стили в JSX + CSS Module 1:1 (цвета — через переменные из `globals.css`). Требования, которые тесты проверяют, — в Interfaces выше. Обязательная логика:

`FormBadge.tsx`:
```tsx
import type { Outcome } from "@/lib/types";
import { outcomeLabel, outcomeLetter } from "@/lib/format";
import s from "./FormBadge.module.css";

export function FormBadge({ outcome, us, them, opponent, size = "m" }: {
  outcome: Outcome; us?: number; them?: number; opponent?: string; size?: "m" | "s";
}) {
  const score = us !== undefined && them !== undefined ? ` ${us}:${them}` : "";
  const vs = opponent ? ` vs ${opponent}` : "";
  return (
    <span className={`${s.badge} ${s[outcome]} ${s[size]}`} role="img" aria-label={`${outcomeLabel(outcome)}${score}${vs}`}>
      {outcomeLetter(outcome)}
    </span>
  );
}
```
`FormBadge.module.css` (размеры и цвета из 02-design-system «Бейдж формы»):
```css
.badge { display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; font-family: var(--f-display); font-weight: 700; flex: none; }
.m { width: 52px; height: 52px; font-size: 20px; }
.s { width: 44px; height: 44px; font-size: 18px; }
@media (max-width: 640px) { .m { width: 44px; height: 44px; } }
.W { background: var(--c-paper); color: var(--c-ink); }
.D { background: var(--c-draw); color: var(--c-paper); }
.L { background: transparent; color: var(--c-paper); box-shadow: inset 0 0 0 2px var(--c-paper); }
```

`ScoreBadge` — аналогично, `aria-label={`${outcomeLabel(o)} ${us}:${them}`}`, текст `{us}:{them}`, `min-width: 64px`, Oswald 700 20px.

`Countdown.tsx`:
```tsx
"use client";

import { useEffect, useState } from "react";
import { countdownParts, plural } from "@/lib/format";
import s from "./Countdown.module.css";

const UNITS: [keyof ReturnType<typeof countdownParts>, [string, string, string]][] = [
  ["days", ["день", "дня", "дней"]],
  ["hours", ["час", "часа", "часов"]],
  ["minutes", ["минута", "минуты", "минут"]],
];

export function Countdown({ kickoff }: { kickoff: string }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);
  const p = countdownParts(kickoff, now);
  if (p.over) return null;
  if (p.started) return <p className={s.live}>Матч идёт</p>;
  const label = UNITS.map(([k, forms]) => `${p[k]} ${plural(p[k] as number, forms)}`).join(" ");
  return (
    <div className={s.timer} role="timer" aria-label={`До матча ${label}`}>
      {UNITS.map(([k, forms]) => (
        <div key={k} className={s.unit} aria-hidden="true">
          <span className={s.value}>{String(p[k]).padStart(2, "0")}</span>
          <span className={s.caption}>{plural(p[k] as number, forms)}</span>
        </div>
      ))}
    </div>
  );
}
```
(Сервер рендерит исходное значение; гидрация может дать расхождение в минуту — добавить `suppressHydrationWarning` на `.value`.)

`StandingsTable` — `<table>` в `.table-scroll`, `<caption className="visually-hidden">`, строка `is_us` с `aria-current="true"` и классом инверсии; подпись «Обновлено {formatDate(updated_at)}» и ссылка «Полная таблица ↗» на `source_url` (`target="_blank" rel="noopener"`).

`NewsTag` — словарь `{ match: "Матч", club: "Клуб", transfer: "Трансфер", social: "Из соцсетей" }`, для `social` с платформой — `{ telegram: "Telegram", vk: "ВКонтакте", youtube: "YouTube" }[platform]`.

`Photo` — при `src` использует `next/image` с `fill` внутри контейнера с `aspect-ratio: ratio` и `object-fit: cover`; без `src` — `div.ph`/`.phl` с той же пропорцией и `role="img" aria-label={alt}`.

Скопировать `design/package/assets/crest-placeholder.svg` в `web/public/icon.svg` и `web/src/app/icon.svg` (фавикон Next).

- [ ] **Step 3: Тесты зелёные**

Run: `pnpm test && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add web && git commit -m "feat(web): UI kit components from design system"
```

---

### Task 4: Каркас приложения: layout, шапка, подвал, 404, ошибки, e2e-окружение

**Files:**
- Create: `web/src/app/layout.tsx`, `web/src/app/not-found.tsx`, `web/src/app/error.tsx`, `web/src/app/global-error.tsx`
- Create: `web/src/components/layout/Header.tsx` (+ `.module.css`), `web/src/components/layout/MobileMenu.tsx` (client), `web/src/components/layout/Footer.tsx` (+ css), `web/src/components/layout/nav.ts`
- Create: `api/bu_api/e2e_seed.py`, `web/playwright.config.ts`, `web/e2e/global-setup.ts`, `web/e2e/layout.spec.ts`
- Modify: `web/package.json` (script `e2e`)

**Interfaces:**
- Consumes: UI-кит (Task 3), `getClub()`.
- Produces: `NAV: { href: string; label: string }[]` (`/matches` Матчи, `/standings` Таблицы, `/team` Команда, `/news` Новости, `/about` О клубе); `<Header club={Club} />` с `aria-current="page"` для активного пункта (через `usePathname` в маленьком клиентском `NavLinks`); `<Footer club={Club} />`; `python -m bu_api.e2e_seed <database_url>` — пересоздаёт схему и наполняет детерминированными данными (2 турнира, 6 игроков на всех позициях, 4 матча: 3 сыгранных (дома победа, в гостях ничья, дома поражение) и 1 будущий, 5 новостей включая social, таблица из 8 строк, club/history docs) и вызывает `recompute`; `python -m bu_api.e2e_seed <url> --empty` — только схема и `club`.

Playwright: `webServer` поднимает API (`uv run uvicorn bu_api.app:build --factory --port 8001` с `BU_DATABASE_URL=postgresql+psycopg://localhost/bu_e2e`) и web (`pnpm build && pnpm start --port 3100` с `BU_API_URL=http://localhost:8001`, `BU_SITE_URL=https://baumanunited.test`, `BU_NOINDEX=0`, `BU_REVALIDATE_SECRET=e2e`); `globalSetup` выполняет `createdb bu_e2e` (игнорируя «уже существует») и `uv run python -m bu_api.e2e_seed postgresql+psycopg://localhost/bu_e2e`. Проекты: `desktop` (1280×800) и `mobile` (Pixel 5).

- [ ] **Step 1: E2E-сид**

`api/bu_api/e2e_seed.py` — по образцу `api/tests/seed.py`, но:
```python
"""Детерминированные данные для Playwright: python -m bu_api.e2e_seed <url> [--empty]."""

import sys
from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from bu_core.models import (
    Base, ContentDoc, Match, MatchEvent, News, Player, PlayerTournamentStats, Season,
    StandingRow, Tournament,
)
from bu_core.recompute import recompute

CLUB = {
    "name": "Бауман Юнайтед", "name_en": "Bauman United", "founded": 2019, "city": "Москва",
    "university": "МГТУ им. Н. Э. Баумана", "format": "8x8", "primary_tournament": None,
    "socials": {"telegram": "https://t.me/baumanunited", "vk": "https://vk.com/baumanunited",
                "youtube": None, "lfl": "https://lfl.ru/club14270", "joinfootball": None},
    "contacts": {"captain_name": "Александр Королев", "captain_telegram": "https://t.me/captain",
                 "email": "team@example.com"},
    "training": {"days": "Вторник и четверг", "time": "20:00", "place": "Спорткомплекс МГТУ",
                 "map_url": "https://yandex.ru/maps/-/test"},
    "looking_for": ["Вратаря", "Защитника ×2"],
    "player_of_month": {"player": "aleksandr-korolev", "month": "2026-10", "stat": "3 гола"},
}


def _player(slug, first, last, number, position, **extra):
    return Player(slug=slug, first_name=first, last_name=last, number=number, position=position,
                  aliases=[], manual_fields=[], achievements=[], **extra)


def seed(session: Session, empty: bool = False) -> None:
    session.add(ContentDoc(key="club", data=CLUB))
    session.add(ContentDoc(key="history", data={"timeline": [], "trophies": [{"place": 1}],
                                                 "legends": []}))
    if empty:
        session.flush()
        recompute(session)
        return
    season = Season(slug="2026-27", label="2026/27")
    li = Tournament(slug="liga-inzhenerov-osen-2026", name="Лига Инженеров · Осень 2026",
                    short="Лига Инженеров", source="joinfootball", external_id="1066703",
                    season=season, url="https://bauman_league.join.football/tournament/1066703")
    lfl = Tournament(slug="lfl-2026-27", name="ЛФЛ 8×8 · 2026/27", short="ЛФЛ", source="manual",
                     season=season)
    players = [
        _player("egor-kucha", "Егор", "Куча", 1, "GK"),
        _player("fedor-meshkov", "Федор", "Мешков", 5, "DF"),
        _player("kirill-kolochkov", "Кирилл", "Колочков", 15, "DF"),
        _player("aleksandr-korolev", "Александр", "Королев", 10, "MF", nickname="Король",
                is_captain=True, fact="Отдал 6 передач за пять туров.", faculty="ИУ7",
                foot="Правая", joined=2019),
        _player("konstantin-konstantinopolskiy", "Константин", "Константинопольский", 8, "MF"),
        _player("dmitriy-pisarev", "Дмитрий", "Писарев", 11, "FW"),
    ]
    session.add_all([season, li, lfl, *players])
    session.flush()
    by = {p.slug: p for p in players}
    for slug, (pl, g, a) in {"egor-kucha": (3, 0, 0), "fedor-meshkov": (3, 1, 1),
                             "kirill-kolochkov": (3, 2, 0), "aleksandr-korolev": (3, 2, 4),
                             "konstantin-konstantinopolskiy": (2, 0, 1),
                             "dmitriy-pisarev": (3, 3, 1)}.items():
        session.add(PlayerTournamentStats(player_id=by[slug].id, tournament_id=li.id,
                                          played=pl, goals=g, assists=a))

    def match(slug, day, home, opp, status, us=None, them=None, t=li, rnd=None):
        return Match(slug=slug, tournament_id=t.id, season_id=season.id, round=rnd,
                     kickoff=datetime(*day, tzinfo=UTC), home=home, venue_name="Металлург",
                     venue_address="Москва, улица Новая Дорога, 11с1",
                     opponent_name=opp, status=status, score_us=us, score_them=them,
                     source=t.source, external_id=slug if t.source != "manual" else None)

    m1 = match("2026-09-06-energiya", (2026, 9, 6, 17, 30), True, "Энергия", "finished", 3, 1,
               rnd="1 тур")
    m1.events.extend([
        MatchEvent(minute=12, type="goal", team="us", player_id=by["aleksandr-korolev"].id,
                   assist_id=by["dmitriy-pisarev"].id),
        MatchEvent(minute=30, type="yellow", team="them", player_name="Сидоров Петр"),
        MatchEvent(minute=44, type="goal", team="them", player_name="Сидоров Петр"),
        MatchEvent(minute=51, type="goal", team="us", player_id=by["dmitriy-pisarev"].id),
        MatchEvent(minute=60, type="goal", team="us", player_id=by["kirill-kolochkov"].id),
    ])
    m1.mvp_player_id = by["aleksandr-korolev"].id
    m1.report_news_slug = "pobeda-nad-energiey"
    m2 = match("2026-09-20-dolgoprudnenskiy-politekh-imeni-ochen-dlinnogo-nazvaniya",
               (2026, 9, 20, 16, 0), False,
               "Долгопрудненский политех имени очень длинного названия", "finished", 2, 2,
               t=lfl, rnd="2 тур")
    m3 = match("2026-10-04-raskat", (2026, 10, 4, 18, 0), True, "Раскат", "finished", 0, 2,
               rnd="3 тур")
    m4 = match("2030-10-24-messiya", (2030, 10, 24, 18, 30), False, "Мессия", "scheduled",
               rnd="6 тур")
    session.add_all([m1, m2, m3, m4])
    teams = ["Раскат", "ФК ФН", "Реактор", "Bauman United", "Энергия", "Мессия", "Армада",
             "Поршень"]
    for pos, team in enumerate(teams, start=1):
        session.add(StandingRow(
            tournament_id=li.id, pos=pos, team_name=team, played=3, won=max(0, 3 - pos // 3),
            drawn=0, lost=min(3, pos // 3), gf=10 - pos, ga=pos, pts=max(0, 9 - pos),
            is_us=team == "Bauman United", updated_at=datetime(2026, 10, 12, 9, 0, tzinfo=UTC)))
    session.add_all([
        News(slug="pobeda-nad-energiey", date=date(2026, 9, 7), tag="match",
             title="Победа над «Энергией» на старте", lead="3:1 в первом туре Лиги Инженеров.",
             body_md="## Как это было\n\nКоролев открыл счёт на **12-й** минуте.",
             match_slug="2026-09-06-energiya", featured=True),
        News(slug="nabor-v-komandu", date=date(2026, 9, 1), tag="club",
             title="Открыт набор в команду", body_md="Ищем вратаря и защитников."),
        News(slug="novyy-zashchitnik", date=date(2026, 9, 10), tag="transfer",
             title="У нас новый защитник", body_md="Добро пожаловать!"),
        News(slug="post-tg-1", date=date(2026, 9, 12), tag="social",
             title="Тренировка перед Раскатом", body_md="Готовимся.",
             source_platform="telegram", source_url="https://t.me/baumanunited/1"),
        News(slug="itogi-sentyabrya", date=date(2026, 9, 30), tag="club",
             title="Итоги сентября", body_md="Три матча, четыре очка."),
    ])
    session.flush()
    recompute(session)


def main() -> None:
    url = sys.argv[1]
    engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session, empty="--empty" in sys.argv)
        session.commit()


if __name__ == "__main__":
    main()
```

Run: `createdb bu_e2e 2>/dev/null; uv run python -m bu_api.e2e_seed postgresql+psycopg://localhost/bu_e2e && psql bu_e2e -Atc "select count(*) from match"`
Expected: `4`.

- [ ] **Step 2: Playwright-конфиг и падающий e2e-тест каркаса**

`web/playwright.config.ts`:
```ts
import { defineConfig, devices } from "@playwright/test";

const API = "http://localhost:8001";
const WEB = "http://localhost:3100";

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: true,
  reporter: [["list"]],
  use: { baseURL: WEB },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
    { name: "mobile", use: { ...devices["Pixel 5"] } },
  ],
  webServer: [
    {
      command: "uv run uvicorn bu_api.app:build --factory --port 8001",
      cwd: "..",
      url: `${API}/health`,
      env: { BU_DATABASE_URL: "postgresql+psycopg://localhost/bu_e2e" },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "pnpm build && pnpm start --port 3100",
      url: WEB,
      timeout: 240_000,
      env: {
        BU_API_URL: API, BU_SITE_URL: "https://baumanunited.test", BU_NOINDEX: "0",
        BU_REVALIDATE_SECRET: "e2e",
      },
      reuseExistingServer: !process.env.CI,
    },
  ],
});
```

`web/e2e/global-setup.ts`:
```ts
import { execSync } from "node:child_process";

export default function globalSetup() {
  try { execSync("createdb bu_e2e", { stdio: "ignore" }); } catch { /* уже есть */ }
  execSync("uv run python -m bu_api.e2e_seed postgresql+psycopg://localhost/bu_e2e", {
    cwd: "..", stdio: "inherit",
  });
}
```

`web/e2e/layout.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

test("header, footer and active nav", async ({ page, isMobile }) => {
  await page.goto("/news");
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  if (isMobile) {
    await page.getByRole("button", { name: "Открыть меню" }).click();
    await expect(page.getByRole("dialog", { name: "Меню" })).toBeVisible();
    await expect(page.getByRole("dialog").getByRole("link", { name: "Новости" })).toHaveAttribute("aria-current", "page");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
  } else {
    await expect(page.getByRole("navigation", { name: "Основное меню" }).getByRole("link", { name: "Новости" }))
      .toHaveAttribute("aria-current", "page");
  }
  await expect(page.getByRole("contentinfo")).toContainText("МГТУ им. Н. Э. Баумана");
});

test("404 page in site style", async ({ page }) => {
  const res = await page.goto("/team/no-such-player-xyz");
  expect(res?.status()).toBe(404);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("404");
  await expect(page.getByRole("link", { name: "На главную" })).toBeVisible();
});

test("no horizontal page scroll", async ({ page }) => {
  await page.goto("/");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
```

Run: `cd web && pnpm exec playwright install chromium && pnpm e2e e2e/layout.spec.ts`
Expected: FAIL (layout и страниц нет).

- [ ] **Step 3: Layout, шапка, подвал, 404, ошибки**

`web/src/components/layout/nav.ts`:
```ts
export const NAV = [
  { href: "/matches", label: "Матчи" },
  { href: "/standings", label: "Таблицы" },
  { href: "/team", label: "Команда" },
  { href: "/news", label: "Новости" },
  { href: "/about", label: "О клубе" },
] as const;

export function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
```

`web/src/app/layout.tsx`:
```tsx
import type { Metadata, Viewport } from "next";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { getClub } from "@/lib/api";
import { buildMetadata, siteUrl } from "@/lib/seo";
import type { Club } from "@/lib/types";
import { manrope, oswald } from "./fonts";
import "./globals.css";

export const dynamic = "force-dynamic";

export function generateMetadata(): Metadata {
  return {
    metadataBase: new URL(siteUrl()),
    ...buildMetadata({
      description: "Бауман Юнайтед — любительская футбольная команда МГТУ им. Н. Э. Баумана: матчи, состав, статистика и новости.",
      path: "/",
    }),
  };
}

export const viewport: Viewport = { themeColor: "#0A0A0A", width: "device-width", initialScale: 1 };

const FALLBACK_CLUB: Club = { name: "Бауман Юнайтед", university: "МГТУ им. Н. Э. Баумана", city: "Москва" };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const club = await getClub().catch(() => FALLBACK_CLUB);
  return (
    <html lang="ru" className={`${oswald.variable} ${manrope.variable}`}>
      <body>
        <a href="#main" className="visually-hidden">Перейти к содержимому</a>
        <Header club={club} />
        <main id="main">{children}</main>
        <Footer club={club} />
      </body>
    </html>
  );
}
```

`Header` — разметка «Шапка» из `Main.dc.html`: герб + «Бауман Юнайтед» (ссылка `/`), `<nav aria-label="Основное меню">` с `NAV` (клиентский `NavLinks` ставит `aria-current="page"` через `usePathname` + `isActive`, подчёркивание 2px), соцсети из `club.socials` (только заданные; `aria-label`), белая кнопка «Хочу в команду» → `/join`. На `< 1024px` вместо nav/соцсетей — кнопка `aria-label="Открыть меню"` 44×44, открывающая `MobileMenu`: полноэкранный `<div role="dialog" aria-modal="true" aria-label="Меню">` (чёрный фон, пункты Oswald 32px капсом, внизу соцсети и «Хочу в команду»), закрытие по кнопке «Закрыть меню», `Escape` и переходу; фокус переносится в диалог и возвращается на кнопку; `body` не скроллится, пока меню открыто.

`Footer` — «Футер» из `Main.dc.html`: `<footer>` (role contentinfo), название, «Москва · МГТУ им. Н. Э. Баумана», контакты из `club.contacts`, колонки ссылок (`NAV` + соцсети + «Страница в ЛФЛ», «Bauman League» из `club.socials`), полоса-мотив 8px снизу.

`web/src/app/not-found.tsx`:
```tsx
import { ButtonLink } from "@/components/ui/Button";
import s from "./not-found.module.css";

export default function NotFound() {
  return (
    <section className={`section ${s.wrap}`}>
      <div className="container">
        <p className="eyebrow">Ошибка</p>
        <h1 className={s.title}>404 — офсайд</h1>
        <p className={s.text}>Такой страницы нет. Возможно, матч перенесли или ссылка устарела.</p>
        <ButtonLink href="/">На главную</ButtonLink>
      </div>
    </section>
  );
}
```
(`not-found.module.css`: `.title { font-size: var(--fs-h1); margin: 12px 0 16px }`, `.text { color: var(--c-muted-2); max-width: 560px; margin: 0 0 32px }`, `.wrap { min-height: 50vh }`.)

`web/src/app/error.tsx` — клиентский компонент в том же стиле: заголовок «Что-то пошло не так», текст «Данные временно недоступны. Попробуйте обновить страницу через минуту.», кнопка `onClick={reset}` «Обновить» и ссылка «На главную». `global-error.tsx` — то же с `<html lang="ru"><body>`.

- [ ] **Step 4: E2E зелёный**

Каждая страница-заглушка, нужная тестам каркаса (`/`, `/news`), появится в Tasks 5 и 9; до тех пор создать временные `web/src/app/page.tsx` и `web/src/app/news/page.tsx` с одним `<h1>` — их заменят соответствующие задачи. `/team/[slug]` для теста 404 — временный `web/src/app/team/[slug]/page.tsx`, вызывающий `notFound()`.

Run: `pnpm e2e e2e/layout.spec.ts && pnpm test && pnpm typecheck && pnpm lint`
Expected: PASS (оба проекта, desktop и mobile).

- [ ] **Step 5: Commit**

```bash
git add web api/bu_api/e2e_seed.py && git commit -m "feat(web): layout, header with mobile menu, footer, error pages, e2e harness"
```

---

### Task 5: Главная `/`

**Files:**
- Create/replace: `web/src/app/page.tsx`, `web/src/app/page.module.css`, `web/src/components/home/*` (`Hero`, `NextMatch`, `ResultFormTable`, `HomeNews`, `Leaders`, `ClubNumbers`, `JoinCta`)
- Test: `web/e2e/home.spec.ts`

**Interfaces:**
- Consumes: `getHome()`, `getClub()`, UI-кит, `sportsTeamLd`, `buildMetadata`.
- Produces: страница по `Main.dc.html` (desktop) и `HomeMobile.dc.html` (mobile, через медиазапросы на тех же компонентах).

Состав и источники (порядок блоков — `01-spec.md` «Главная»; блоки «Фото последнего матча» и «Мы в соцсетях» — v2, не делаем):
1. **Hero** — заголовок `<h1>Бауман<br/>Юнайтед</h1>`, подзаголовок «Футбольная команда МГТУ им. Н. Э. Баумана. Играем в ЛФЛ и Bauman League, 8×8.» (фэнтази не упоминаем), фон `.ph` (фото — v2), полоса 12px. `LiveBadge` + ссылка «Смотреть трансляцию: Бауман Юнайтед — {opponent}» → `live.stream_url`, только если `home.live`.
2. **Следующий матч** (белая секция) — если `next_match`: гербы-плейсхолдеры (наш `Crest` и кружок с инициалом соперника или `opponent_logo`), «VS», `tournament.short · round`, дата/время (`formatDate`, `formatTime`, день недели), стадион, «Дома»/«В гостях», `<Countdown kickoff>`, кнопка «Как добраться» → `https://yandex.ru/maps/?text=${encodeURIComponent(venue_address ?? venue_name)}` (если есть адрес). Нет матча — секции нет.
3. **Три карточки** — «Последний результат» (`last_match`: счёт 64px, `scorers_us` с минутами, ссылка «Отчёт о матче» → `/matches/{slug}`), «Форма» (`form` кружками `FormBadge` от старого к новому + забито/пропущено/сухие из `totals`), «Таблица» (`StandingsTable compact` по `home.standings`, ссылка «Полная таблица» → `/standings`). Пустые части скрываются.
4. **Новости** — `news` (до 4) `NewsCardTile onPaper`, ссылка «Все новости» → `/news`. Пусто — секции нет.
5. **Лидеры сезона** — карточки: лучший бомбардир (`leaders.goals`, цифра голов), ассистент (`leaders.assists`), «Игрок месяца» (`player_of_month`, `stat`); третья — инвертирована. Ссылки на `/team/{slug}`. Нет ни одного — секции нет.
6. **Цифры клуба** — `numbers.founded` (если есть), `matches`, `goals`, `trophies`; Oswald 80px, полоса-текстура 6%.
7. **Хочешь играть с нами?** — заголовок 56px, кнопка «Написать в Telegram» → `club.contacts.captain_telegram` (если нет — ссылка на `/join`).

SEO: `generateMetadata` → `buildMetadata({ description: "Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана (бауманка). Матчи ЛФЛ и Лиги Инженеров Bauman League, состав, статистика, новости.", path: "/" })` (title — главный); `<JsonLd data={sportsTeamLd(club)} />` и, если есть `next_match`, `<JsonLd data={sportsEventLd(next_match)} />`.

- [ ] **Step 1: Падающий e2e**

`web/e2e/home.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

test("home renders data blocks from API", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Бауман");
  await expect(page.getByRole("timer")).toHaveAccessibleName(/^До матча \d+ (день|дня|дней)/);
  await expect(page.getByText("Мессия").first()).toBeVisible();
  await expect(page.getByRole("img", { name: /^Победа 3:1/ }).first()).toBeVisible();
  await expect(page.locator("tr[aria-current='true']")).toContainText("Bauman United");
  await expect(page.getByRole("link", { name: /Победа над «Энергией»/ })).toBeVisible();
  await expect(page.getByText("Дмитрий Писарев").first()).toBeVisible();
});

test("home has SportsTeam JSON-LD and canonical", async ({ page }) => {
  await page.goto("/");
  const ld = await page.locator('script[type="application/ld+json"]').allTextContents();
  const team = ld.map((t) => JSON.parse(t)).find((d) => d["@type"] === "SportsTeam");
  expect(team.memberOf.name).toBe("МГТУ им. Н. Э. Баумана");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://baumanunited.test/");
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /бауманка/);
});
```

Run: `pnpm e2e e2e/home.spec.ts` → FAIL.

- [ ] **Step 2: Реализация** по составу выше: перенести секции из `Main.dc.html` (разметка + стили 1:1, inline → CSS Modules), мобильные отличия — из `HomeMobile.dc.html` через `@media (max-width: 640px)` (таблица 3 строки внутри карточки формы — `compact` + обрезка до 3 строк вокруг нас; новости — одна большая + 3 строкой; лидеры — горизонтальная карусель со `scroll-snap`; цифры — сетка 2×2). `page.tsx` — серверный, `export const dynamic = "force-dynamic"`, данные: `const [home, club] = await Promise.all([getHome(), getClub()])`.

- [ ] **Step 3: Зелёный**

Run: `pnpm e2e e2e/home.spec.ts e2e/layout.spec.ts && pnpm typecheck && pnpm lint`
Expected: PASS на desktop и mobile.

- [ ] **Step 4: Commit**

```bash
git add web && git commit -m "feat(web): home page"
```

---

### Task 6: Матчи `/matches` и таблицы `/standings`

**Files:**
- Create: `web/src/app/matches/page.tsx` (+ css), `web/src/components/matches/Filters.tsx`, `web/src/components/matches/UpcomingList.tsx`, `web/src/components/matches/ResultsTable.tsx`, `web/src/app/standings/page.tsx` (+ css)
- Create: `web/src/lib/filters.ts`
- Test: `web/src/lib/filters.test.ts`, `web/e2e/matches.spec.ts`

**Interfaces:**
- Consumes: `getMatches`, `getSeasons`, `getTournaments`, `getStandings`, UI-кит.
- Produces: `parseMatchFilters(sp: Record<string, string | string[] | undefined>, tournaments: Tournament[], seasons: Season[]) -> { season?: string; tournament?: string; where?: "home" | "away"; isFiltered: boolean }` — неизвестные значения отбрасываются; `filterHref(current, patch) -> string` — URL с изменённым параметром (пустые удаляются).

Страница `/matches` по `Calendar.dc.html`: заголовок «МАТЧИ», фильтры — ссылки-переключатели (не JS: каждая кнопка — `<a>` на URL с изменённым query, `aria-pressed` у активной через `aria-current="true"` на ссылке) — сезон (из `getSeasons`), турнир («Все» + каждый турнир сезона по `short`), где («Все / Дома / В гостях»); блок «Ближайшие» (`status=scheduled|live`, по возрастанию; первый — белый с бейджем «2д 17ч» до начала) и «Сыгранные» (таблица: дата, турнир, соперник, где, `ScoreBadge`, «Матч →»; по убыванию даты; легенда В/Н/П под таблицей). Пусто — `EmptyState` «Матчей по выбранным фильтрам нет».

SEO `/matches`: description «Календарь и результаты матчей Бауман Юнайтед — футбольной команды МГТУ им. Баумана в ЛФЛ и Лиге Инженеров.»; canonical всегда `/matches` (без query); при `isFiltered` — `noindex: true`. JSON-LD: `breadcrumbsLd([{name:"Матчи", path:"/matches"}])` + `sportsEventLd` для ближайших (до 5).

`/standings`: заголовок «ТАБЛИЦЫ», для каждого турнира из `getStandings()` — `<h2>` с названием турнира и полный `StandingsTable`; пусто — `EmptyState`. Description «Турнирные таблицы Бауман Юнайтед: ЛФЛ и Лига Инженеров Bauman League (МГТУ им. Баумана).»

- [ ] **Step 1: Падающие тесты**

`web/src/lib/filters.test.ts`:
```ts
import { filterHref, parseMatchFilters } from "./filters";

const tournaments = [{ slug: "lfl-2026-27", short: "ЛФЛ" }, { slug: "liga", short: "ЛИ" }] as never;
const seasons = [{ slug: "2026-27", label: "2026/27", final_place: null }] as never;

describe("match filters", () => {
  it("drops unknown values", () => {
    expect(parseMatchFilters({ where: "xxx", t: "", season: "1999-00" }, tournaments, seasons))
      .toEqual({ season: undefined, tournament: undefined, where: undefined, isFiltered: false });
  });
  it("keeps known values", () => {
    expect(parseMatchFilters({ where: "home", t: "liga", season: "2026-27" }, tournaments, seasons))
      .toEqual({ season: "2026-27", tournament: "liga", where: "home", isFiltered: true });
  });
  it("builds hrefs", () => {
    expect(filterHref({ season: "2026-27", where: "home" }, { where: undefined })).toBe("/matches?season=2026-27");
    expect(filterHref({}, { t: "liga" })).toBe("/matches?t=liga");
  });
});
```

`web/e2e/matches.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

test("matches page lists upcoming and results with filters", async ({ page }) => {
  await page.goto("/matches");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Матчи/i);
  await expect(page.getByRole("img", { name: "Победа 3:1" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Ничья 2:2" })).toBeVisible();
  await expect(page.getByText("Мессия").first()).toBeVisible();
  await page.getByRole("link", { name: "Дома", exact: true }).click();
  await expect(page).toHaveURL(/where=home/);
  await expect(page.getByRole("img", { name: "Ничья 2:2" })).toHaveCount(0);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://baumanunited.test/matches");
});

test("garbage query does not break the page", async ({ page }) => {
  const res = await page.goto("/matches?where=xxx&t=&season=zzz");
  expect(res?.status()).toBe(200);
  await expect(page.getByRole("img", { name: "Победа 3:1" })).toBeVisible();
});

test("standings page", async ({ page }) => {
  await page.goto("/standings");
  await expect(page.getByRole("heading", { level: 2, name: /Лига Инженеров/ })).toBeVisible();
  await expect(page.locator("tr[aria-current='true']")).toContainText("Bauman United");
  await expect(page.getByText(/Обновлено 12 октября 2026/)).toBeVisible();
});
```

Run: `pnpm test src/lib/filters.test.ts && pnpm e2e e2e/matches.spec.ts` → FAIL.

- [ ] **Step 2: Реализация `filters.ts`**

```ts
import type { Season, Tournament } from "./types";

type SP = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) || undefined;

export function parseMatchFilters(sp: SP, tournaments: Tournament[], seasons: Season[]) {
  const season = seasons.some((s) => s.slug === one(sp.season)) ? one(sp.season) : undefined;
  const tournament = tournaments.some((t) => t.slug === one(sp.t)) ? one(sp.t) : undefined;
  const w = one(sp.where);
  const where = w === "home" || w === "away" ? w : undefined;
  return { season, tournament, where, isFiltered: Boolean(season || tournament || where) } as {
    season?: string; tournament?: string; where?: "home" | "away"; isFiltered: boolean;
  };
}

export function filterHref(current: Record<string, string | undefined>, patch: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries({ ...current, ...patch })) if (v) params.set(k, v);
  const qs = params.toString();
  return `/matches${qs ? `?${qs}` : ""}`;
}
```

- [ ] **Step 3: Страницы** по описанию выше и `Calendar.dc.html`.

- [ ] **Step 4: Зелёный**

Run: `pnpm test && pnpm e2e e2e/matches.spec.ts && pnpm typecheck && pnpm lint` → PASS.

- [ ] **Step 5: Commit**

```bash
git add web && git commit -m "feat(web): matches calendar with filters and standings page"
```

---

### Task 7: Страница матча `/matches/[slug]` + OG-картинка

**Files:**
- Create: `web/src/app/matches/[slug]/page.tsx` (+ css), `web/src/app/matches/[slug]/opengraph-image.tsx`, `web/src/components/match/Scoreboard.tsx`, `web/src/components/match/EventsList.tsx`, `web/src/components/match/Report.tsx`, `web/src/components/Markdown.tsx`
- Test: `web/e2e/match.spec.ts`

**Interfaces:**
- Consumes: `getMatch`, `sportsEventLd`, `breadcrumbsLd`, UI-кит.
- Produces: `<Markdown source={string} />` — серверный рендер `react-markdown` без raw HTML (по умолчанию HTML экранируется), ссылки с `rel="noopener"` и `target="_blank"` для внешних.

По `Match.dc.html`, MVP-объём (spec 6.1): **Табло** (турнир · тур, дата и время, стадион; наша команда слева, если `home`, иначе справа; авторы голов под каждой командой из `scorers_us`/`scorers_them`; счёт Oswald `--fs-score-xl`; статус «Финальный свисток» / «LIVE» / дата для будущих; `Countdown` для будущих). **События** (если `events` не пусто): список по минутам, наши слева, минута по центру, соперника справа; бейдж типа: Гол — белая заливка, ЖК — белый контур, КК — контур 2px + «КК», Замена — `#404040`; для наших событий с `player_slug` — ссылка на игрока; ассист в скобках. **Лучший игрок матча** — `mvp` (если есть). **Отчёт** (белая секция) — если `report`: тег, дата, заголовок, ссылка «Читать полностью →» на `/news/{slug}` и лид. **Источник** — ссылка «Протокол на join.football ↗» (`source_url`), если есть. Внизу — «← Предыдущий матч / Следующий матч →» (`prev_slug`/`next_slug`). Схема поля, фото, голосование — v2/v3, не делаем.

SEO: title `Бауман Юнайтед {us}:{them} {opponent}` (сыгран) или `Бауман Юнайтед — {opponent}, {formatDate}` (будущий); description: «{tournament.name}, {round}. {Победа/Ничья/Поражение} {us}:{them}. Голы: {scorers_us}.» / «Матч {tournament.name}, {round}: {дата} {время}, {venue_name}.»; `type: "article"`; JSON-LD `sportsEventLd(match)` + `breadcrumbsLd([Матчи, {название}])`. Несуществующий slug → `notFound()`.

OG-картинка (`opengraph-image.tsx`, `next/og` `ImageResponse`, 1200×630, ч/б): сверху «{tournament.short} · {round}», по центру «БАУМАН ЮНАЙТЕД {us}:{them} {OPPONENT}» (или «VS» и дата для будущего), снизу полоса-мотив; шрифт — Oswald 700, загруженный из `node_modules/@fontsource/oswald/files/oswald-cyrillic-700-normal.woff` (добавить `@fontsource/oswald` в dependencies), `export const alt`, `size`, `contentType`.

- [ ] **Step 1: Падающий e2e**

`web/e2e/match.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

test("finished match page", async ({ page }) => {
  await page.goto("/matches/2026-09-06-energiya");
  await expect(page).toHaveTitle(/^Бауман Юнайтед 3:1 Энергия — /);
  await expect(page.getByText("Финальный свисток")).toBeVisible();
  await expect(page.getByText("Королев 12'").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Александр Королев" }).first()).toHaveAttribute("href", "/team/aleksandr-korolev");
  await expect(page.getByRole("link", { name: /Читать полностью/ })).toHaveAttribute("href", "/news/pobeda-nad-energiey");
  const ld = (await page.locator('script[type="application/ld+json"]').allTextContents()).map((t) => JSON.parse(t));
  const ev = ld.find((d) => d["@type"] === "SportsEvent");
  expect(ev.eventStatus).toBe("https://schema.org/EventCompleted");
  expect(ev.homeTeam.name).toBe("Бауман Юнайтед");
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /opengraph-image/);
});

test("upcoming away match page", async ({ page }) => {
  await page.goto("/matches/2030-10-24-messiya");
  await expect(page.getByRole("timer")).toBeVisible();
  await expect(page.getByText("В гостях").first()).toBeVisible();
});

test("og image renders", async ({ request }) => {
  const res = await request.get("/matches/2026-09-06-energiya/opengraph-image");
  expect(res.status()).toBe(200);
  expect(res.headers()["content-type"]).toContain("image/png");
});

test("unknown match is 404", async ({ page }) => {
  expect((await page.goto("/matches/nope"))?.status()).toBe(404);
});
```

Run: `pnpm e2e e2e/match.spec.ts` → FAIL.

- [ ] **Step 2: Реализация** по описанию и `Match.dc.html` (секции «Табло», «События + состав» — только события, «Отчёт + MVP»).

- [ ] **Step 3: Зелёный**

Run: `pnpm e2e e2e/match.spec.ts && pnpm typecheck && pnpm lint` → PASS.

- [ ] **Step 4: Commit**

```bash
git add web && git commit -m "feat(web): match page with events, report, JSON-LD and OG image"
```

---

### Task 8: Состав `/team` и профиль `/team/[slug]` + OG-картинка

**Files:**
- Create: `web/src/app/team/page.tsx` (+ css), `web/src/app/team/[slug]/page.tsx` (+ css, заменить временный), `web/src/app/team/[slug]/opengraph-image.tsx`, `web/src/components/team/PlayerStatsTiles.tsx`, `web/src/components/team/SeasonToggle.tsx` (client)
- Test: `web/e2e/team.spec.ts`

**Interfaces:**
- Consumes: `getPlayers`, `getPlayer`, `personLd`, `breadcrumbsLd`, `positionGroup`, `positionLabel`, UI-кит.

`/team` по `Squad.dc.html`: заголовок «СОСТАВ», подзаголовок «Сезон {label}», якорные ссылки по группам (Вратари / Защитники / Полузащитники / Нападающие — только непустые), группы с заголовком, белой линией 2px и счётчиком «05»; сетка `PlayerCardTile` (`auto-fill minmax(220px,1fr)`). Капитан — пометка «C». Пусто — `EmptyState`. (Блок «Штаб» — v2.) Description «Состав Бауман Юнайтед — футбольной команды МГТУ им. Баумана: вратари, защитники, полузащитники и нападающие.»

`/team/[slug]` по `Player.dc.html`: хлебные крошки «Состав / {Позиция} / {Имя}»; Hero (фото или штриховка, гигантский номер на фоне, «№ {number} · {positionLabel}», имя в две строки, прозвище, сетка данных — «В команде с», «Рабочая нога», «Факультет», «Амплуа» — только заданные; плашка «Факт», если есть); Статистика (белая секция): `SeasonToggle` «Сезон / За всё время» (клиентский переключатель между `season` и `total`, по умолчанию «Сезон»), 6 плиток (Матчи, Голы, Передачи, ЖК, КК, MVP), плитки из `team_best` инвертированы с подписью «№1 в команде»; таблица по сезонам (`seasons`) с итоговой строкой (`total`); Достижения — список, если есть; «← {prev} / {next} →» по `prev_slug`/`next_slug`. Даты рождения не выводятся.

SEO: title `{Имя Фамилия} — {positionLabel}`, description «{Имя Фамилия}{, «прозвище»} — {positionLabel} Бауман Юнайтед (МГТУ им. Баумана), № {number}. Сезон: {played} матчей, {goals} голов, {assists} передач.» (склонения через `plural`); `type: "profile"`; JSON-LD `personLd` + `breadcrumbsLd`; OG-картинка: номер, имя, позиция, ключевые цифры сезона. Несуществующий slug → `notFound()`.

- [ ] **Step 1: Падающий e2e**

`web/e2e/team.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

test("squad grouped by position", async ({ page }) => {
  await page.goto("/team");
  for (const g of ["Вратари", "Защитники", "Полузащитники", "Нападающие"]) {
    await expect(page.getByRole("heading", { level: 2, name: new RegExp(g) })).toBeVisible();
  }
  await expect(page.getByRole("link", { name: /Константинопольский/ })).toBeVisible();
  await page.getByRole("link", { name: /Королев/ }).first().click();
  await expect(page).toHaveURL("/team/aleksandr-korolev");
});

test("player profile", async ({ page }) => {
  await page.goto("/team/aleksandr-korolev");
  await expect(page).toHaveTitle(/^Александр Королев — Полузащитник — /);
  await expect(page.getByText("Король").first()).toBeVisible();
  await expect(page.getByText("№1 в команде").first()).toBeVisible();
  await expect(page.getByText(/Отдал 6 передач/)).toBeVisible();
  await page.getByRole("button", { name: "За всё время" }).click();
  await expect(page.getByRole("button", { name: "За всё время" })).toHaveAttribute("aria-pressed", "true");
  const ld = (await page.locator('script[type="application/ld+json"]').allTextContents()).map((t) => JSON.parse(t));
  expect(ld.find((d) => d["@type"] === "Person").name).toBe("Александр Королев");
  await expect(page.locator("body")).not.toContainText(/\d{2}\.\d{2}\.\d{4}/);
});

test("player og image", async ({ request }) => {
  const res = await request.get("/team/aleksandr-korolev/opengraph-image");
  expect(res.headers()["content-type"]).toContain("image/png");
});
```

Run: `pnpm e2e e2e/team.spec.ts` → FAIL.

- [ ] **Step 2: Реализация** по описанию, `Squad.dc.html`, `Player.dc.html`.

- [ ] **Step 3: Зелёный**

Run: `pnpm e2e e2e/team.spec.ts e2e/layout.spec.ts && pnpm typecheck && pnpm lint` → PASS.

- [ ] **Step 4: Commit**

```bash
git add web && git commit -m "feat(web): squad and player profile pages"
```

---

### Task 9: Новости `/news` и `/news/[slug]`

**Files:**
- Create/replace: `web/src/app/news/page.tsx` (+ css), `web/src/app/news/[slug]/page.tsx` (+ css)
- Test: `web/e2e/news.spec.ts`

**Interfaces:**
- Consumes: `getNews`, `getNewsItem`, `Markdown`, `newsArticleLd`, `breadcrumbsLd`, UI-кит.

`/news` по `News.dc.html` (светлая страница: белый фон, шапка чёрная): заголовок «НОВОСТИ»; фильтр-теги ссылками `?tag=` (Все / Матч / Клуб / Трансфер / Из соцсетей; активный — `aria-current="true"`); главная новость (первая с `featured`, иначе самая свежая на первой странице без фильтра) — большой блок (обложка 3/5, текст 2/5 на чёрном); лента `NewsCardTile onPaper` (`auto-fill minmax(280px,1fr)`); пагинация «← Новее / Старее →» ссылками `?page=` (9 на страницу). Неизвестный `tag` игнорируется; `page` вне диапазона → пустой список с `EmptyState`. Canonical — `/news` для первой страницы без тега, `/news?page=N` для остальных страниц; с тегом — `noindex`.

`/news/[slug]` — как блок «Отчёт» из `Match.dc.html`, колонка 720px: тег, дата, заголовок (h1), лид, обложка, тело `Markdown`, кнопка «Оригинал в {Telegram/VK/YouTube} ↗» если `source_url`, ссылка «К матчу →» если `match_slug`. SEO: title = заголовок новости, description = `lead` или первые 160 символов текста без Markdown, `type: "article"`, JSON-LD `newsArticleLd` + `breadcrumbsLd`. Несуществующий slug → `notFound()`.

- [ ] **Step 1: Падающий e2e**

`web/e2e/news.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

test("news list with featured, tags and social post", async ({ page }) => {
  await page.goto("/news");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Новости/i);
  await expect(page.getByRole("link", { name: /Победа над «Энергией»/ }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Открыть оригинал/ })).toHaveAttribute("href", "https://t.me/baumanunited/1");
  await page.getByRole("link", { name: "Трансфер", exact: true }).click();
  await expect(page).toHaveURL(/tag=transfer/);
  await expect(page.getByText("У нас новый защитник")).toBeVisible();
  await expect(page.getByText("Итоги сентября")).toHaveCount(0);
});

test("news article renders markdown and JSON-LD", async ({ page }) => {
  await page.goto("/news/pobeda-nad-energiey");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Победа над «Энергией» на старте");
  await expect(page.getByRole("heading", { level: 2, name: "Как это было" })).toBeVisible();
  await expect(page.locator("article strong")).toHaveText("12-й");
  await expect(page.getByRole("link", { name: /К матчу/ })).toHaveAttribute("href", "/matches/2026-09-06-energiya");
  const ld = (await page.locator('script[type="application/ld+json"]').allTextContents()).map((t) => JSON.parse(t));
  expect(ld.find((d) => d["@type"] === "NewsArticle").headline).toBe("Победа над «Энергией» на старте");
});

test("unknown news is 404", async ({ page }) => {
  expect((await page.goto("/news/nope"))?.status()).toBe(404);
});
```

Run: `pnpm e2e e2e/news.spec.ts` → FAIL.

- [ ] **Step 2: Реализация** по описанию и `News.dc.html`.

- [ ] **Step 3: Зелёный**

Run: `pnpm e2e e2e/news.spec.ts && pnpm typecheck && pnpm lint` → PASS.

- [ ] **Step 4: Commit**

```bash
git add web && git commit -m "feat(web): news list and article pages"
```

---

### Task 10: «О клубе» `/about` и «Хочу в команду» `/join`

**Files:**
- Create: `web/src/app/about/page.tsx` (+ css), `web/src/app/join/page.tsx` (+ css)
- Modify: `content/club.yaml` (добавить поле `about` — SEO-текст), `worker/bu_worker/sources/content.py` не меняется (`club.yaml` — свободный словарь)
- Test: `web/e2e/about-join.spec.ts`

**Interfaces:**
- Consumes: `getClub`, `getHome` (цифры клуба), `Markdown`, `sportsTeamLd`, UI-кит.

`/about`: h1 «О клубе», текст `club.about` (Markdown), блок цифр клуба (`getHome().numbers`), ссылки на профили команды (lfl.ru, join.football, соцсети из `club.socials`), CTA «Хочу в команду». JSON-LD `sportsTeamLd`. Description: «Бауман Юнайтед — любительская футбольная команда МГТУ им. Н. Э. Баумана (бауманка): история, формат 8×8, ЛФЛ и Лига Инженеров Bauman League.»

`content/club.yaml` — добавить:
```yaml
about: |
  **Бауман Юнайтед** — любительская футбольная команда студентов и выпускников МГТУ им. Н. Э. Баумана. Бауманка, Лефортово, футбол 8×8 — это про нас.

  Мы играем в Лиге Любителей Футбола (ЛФЛ) и в Bauman League — университетской футбольной лиге МГТУ, где выступаем в Лиге Инженеров. Тренируемся каждую неделю и всегда рады новым игрокам с любого факультета.

  На сайте — календарь и результаты матчей, турнирные таблицы, состав и статистика игроков, отчёты и новости команды.
```
(Тренировки, контакты и «ищем» заполняет команда — чеклист `design/package/docs/05-content-checklist.md`.)

`/join` по `Contacts.dc.html`: слева — заголовок «Хочешь в команду?», текст, «Сейчас ищем» (бейджи из `club.looking_for`, если есть), сетка «Тренировки / Матчи / Капитан / Почта» (только заданные поля), кнопка «Открыть в Яндекс Картах» (`training.map_url`, если есть); справа — вместо формы (v2) белая карточка: «Напиши капитану в Telegram — расскажи, на какой позиции играешь, с какого ты факультета и где играл раньше», кнопка «Написать капитану» → `contacts.captain_telegram` (если нет — `socials.telegram`; если нет ничего — почта `mailto:`). Внизу — ряд соцсетей и «Страница в ЛФЛ». Description: «Как попасть в футбольную команду МГТУ им. Баумана: тренировки, кого ищем, контакты капитана Бауман Юнайтед.»

- [ ] **Step 1: Падающий e2e**

`web/e2e/about-join.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

test("join page shows contacts and CTA", async ({ page }) => {
  await page.goto("/join");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Хочешь в команду/i);
  await expect(page.getByText("Вратаря")).toBeVisible();
  await expect(page.getByText("Вторник и четверг")).toBeVisible();
  await expect(page.getByRole("link", { name: "Написать капитану" })).toHaveAttribute("href", "https://t.me/captain");
});

test("about page", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/О клубе/i);
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /МГТУ им\. Н\. Э\. Баумана/);
});
```

(Сид e2e не содержит `about` — страница должна рендериться без текста: блок пропускается.)

Run: `pnpm e2e e2e/about-join.spec.ts` → FAIL.

- [ ] **Step 2: Реализация** по описанию и `Contacts.dc.html`.

- [ ] **Step 3: Зелёный**

Run: `pnpm e2e e2e/about-join.spec.ts && pnpm typecheck && pnpm lint && cd .. && uv run pytest worker/tests/test_content_load.py` → PASS.

- [ ] **Step 4: Commit**

```bash
git add web content/club.yaml && git commit -m "feat(web): about and join pages; SEO about text"
```

---

### Task 11: SEO-смоук всех страниц, пустая база, мобильная вёрстка

**Files:**
- Create: `web/e2e/seo.spec.ts`, `web/e2e/empty.spec.ts`, `web/playwright.empty.config.ts`
- Modify: `web/package.json` (скрипт `"e2e:empty": "playwright test -c playwright.empty.config.ts"`)

**Interfaces:**
- Consumes: все страницы.

- [ ] **Step 1: Тесты**

`web/e2e/seo.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

const PAGES = ["/", "/matches", "/standings", "/team", "/team/aleksandr-korolev", "/news",
  "/news/pobeda-nad-energiey", "/matches/2026-09-06-energiya", "/about", "/join"];

for (const path of PAGES) {
  test(`seo basics ${path}`, async ({ page }) => {
    const res = await page.goto(path);
    expect(res?.status()).toBe(200);
    const title = await page.title();
    expect(title).toContain("Бауман Юнайтед");
    const description = await page.locator('meta[name="description"]').getAttribute("content");
    expect(description?.length ?? 0).toBeGreaterThan(50);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /^https:\/\/baumanunited\.test\//);
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", title);
    await expect(page.locator("h1")).toHaveCount(1);
    for (const json of await page.locator('script[type="application/ld+json"]').allTextContents()) {
      expect(() => JSON.parse(json)).not.toThrow();
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}

test("html is server-rendered (works without JS)", async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto("/matches/2026-09-06-energiya");
  await expect(page.getByText("Финальный свисток")).toBeVisible();
  await ctx.close();
});

test("robots and sitemap", async ({ request }) => {
  const robots = await (await request.get("/robots.txt")).text();
  expect(robots).toContain("Sitemap: https://baumanunited.test/sitemap.xml");
  const sitemap = await (await request.get("/sitemap.xml")).text();
  expect(sitemap).toContain("<loc>https://baumanunited.test/team/aleksandr-korolev</loc>");
  expect(sitemap).toContain("<loc>https://baumanunited.test/matches/2026-09-06-energiya</loc>");
});

test("revalidate endpoint requires secret", async ({ request }) => {
  expect((await request.post("/api/revalidate", { data: { tags: ["home"] } })).status()).toBe(401);
  const ok = await request.post("/api/revalidate", {
    data: { tags: ["home"] }, headers: { authorization: "Bearer e2e" },
  });
  expect(ok.status()).toBe(200);
});
```

`web/playwright.empty.config.ts` — копия `playwright.config.ts` с портами API 8002 / web 3200, БД `bu_e2e_empty`, `globalSetup` с флагом `--empty` (вынести `globalSetup` в функцию, читающую `process.env.E2E_DB` и `E2E_EMPTY`), `testMatch: "empty.spec.ts"`; в основном конфиге — `testIgnore: "empty.spec.ts"`.

`web/e2e/empty.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

for (const path of ["/", "/matches", "/standings", "/team", "/news", "/about", "/join"]) {
  test(`empty db renders ${path}`, async ({ page }) => {
    const res = await page.goto(path);
    expect(res?.status()).toBe(200);
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.getByText("Что-то пошло не так")).toHaveCount(0);
  });
}

test("empty home hides data blocks", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("timer")).toHaveCount(0);
  await expect(page.locator("table")).toHaveCount(0);
});
```

Run: `pnpm e2e && pnpm e2e:empty`
Expected: сначала возможны падения — это и есть находки: чинить код страниц (не ослабляя тесты), пока всё не станет зелёным в обоих проектах (desktop, mobile).

- [ ] **Step 2: Полный прогон**

Run: `pnpm test && pnpm typecheck && pnpm lint && pnpm e2e && pnpm e2e:empty && cd .. && uv run pytest`
Expected: всё PASS.

- [ ] **Step 3: Commit**

```bash
git add web && git commit -m "test(web): SEO smoke for all pages, empty-database and mobile overflow checks"
```
