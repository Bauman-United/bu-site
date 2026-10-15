import type { Season, Tournament } from "./types";

type SP = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) || undefined;

export interface MatchFilters {
  season?: string;
  tournament?: string;
  where?: "home" | "away";
  isFiltered: boolean;
}

/** Фильтры `/matches` из query (`season`, `t`, `where`); неизвестные значения отбрасываются. */
export function parseMatchFilters(sp: SP, tournaments: Tournament[], seasons: Season[]): MatchFilters {
  const season = seasons.some((s) => s.slug === one(sp.season)) ? one(sp.season) : undefined;
  const tournament = tournaments.some((t) => t.slug === one(sp.t)) ? one(sp.t) : undefined;
  const w = one(sp.where);
  const where = w === "home" || w === "away" ? w : undefined;
  return { season, tournament, where, isFiltered: Boolean(season || tournament || where) };
}

/** URL `/matches` с изменёнными параметрами; пустые значения удаляются. */
export function filterHref(current: Record<string, string | undefined>, patch: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries({ ...current, ...patch })) if (v) params.set(k, v);
  const qs = params.toString();
  return `/matches${qs ? `?${qs}` : ""}`;
}
