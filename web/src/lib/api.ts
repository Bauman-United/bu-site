import "server-only";

import type {
  AllTimeRecords, Club, Home, MatchDetail, MatchSummary, NewsDetail, NewsPage, PlayerCard, PlayerDetail,
  Season, SitemapItem, Standings, Tournament,
} from "./types";
import type { League } from "@/components/tournament/LeagueTabs";
import type { History } from "./history";

export const REVALIDATE_SECONDS = 300;

export class ApiError extends Error {
  constructor(public status: number, path: string) {
    super(`API ${status} for ${path}`);
  }
}

type Query = Record<string, string | undefined>;

export function apiUrl(path: string, query?: Query): string {
  const base = process.env.BU_API_URL ?? "http://localhost:8000";
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) if (v) params.set(k, v);
  const qs = params.toString();
  return `${base}${path}${qs ? `?${qs}` : ""}`;
}

export async function apiGet<T>(path: string, opts: { tags?: string[]; query?: Query } = {}): Promise<T> {
  const cacheOptions: RequestInit = process.env.NODE_ENV === "development"
    ? { cache: "no-store" }
    : { next: { revalidate: REVALIDATE_SECONDS, tags: opts.tags ?? [] } } as RequestInit;
  const res = await fetch(apiUrl(path, opts.query), cacheOptions);
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
export const getPlayers = (q: { league?: League } = {}) =>
  apiGet<PlayerCard[]>("/players", {
    tags: ["players"],
    // Общий состав: текущая заявка + все, кто играл в сезоне (бывшие игроки ЛФЛ тоже);
    // league=bl|lfl|ifl|urban — суммы по турнирам лиги текущего сезона вместе с кубками.
    query: { roster: "true", league: q.league },
  });
export const getPlayer = (slug: string) =>
  apiGetOrNull<PlayerDetail>(`/players/${encodeURIComponent(slug)}`, { tags: ["players", `player:${slug}`] });
export const getNews = (q: { tag?: string; page?: number } = {}) =>
  apiGet<NewsPage>("/news", { tags: ["news"], query: { tag: q.tag, page: q.page ? String(q.page) : undefined } });
export const getNewsItem = (slug: string) =>
  apiGetOrNull<NewsDetail>(`/news/${encodeURIComponent(slug)}`, { tags: ["news", `news:${slug}`] });
export const getStandings = (tournament?: string) =>
  apiGet<Standings[]>("/standings", { tags: ["standings"], query: { tournament } });
export const getClub = () => apiGet<Club>("/club", { tags: ["club"] });
export const getHistory = () => apiGet<History>("/history", { tags: ["history"] });
/** Рекордсмены клуба за всё время (все сезоны и турниры, бывшие игроки тоже). */
export const getAllTimeRecords = () =>
  apiGet<AllTimeRecords>("/records/all-time", { tags: ["players", "matches"], query: { limit: "10" } });
export const getSeasons = () => apiGet<Season[]>("/seasons", { tags: ["matches"] });
export const getTournaments = (season?: string) =>
  apiGet<Tournament[]>("/tournaments", { tags: ["matches"], query: { season } });
export const getSitemap = () => apiGet<SitemapItem[]>("/sitemap", { tags: ["matches", "players", "news"] });
