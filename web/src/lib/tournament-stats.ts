import type { PlayerStats, Season } from "./types";
import type { components } from "./api-types";

export type TournamentStatsRow = components["schemas"]["TournamentStatsRow"];

const KEYS = ["played", "goals", "assists", "yellow", "red", "mvp"] as const;

function isEmpty(stats: PlayerStats): boolean {
  return KEYS.every((k) => !stats[k]);
}

/** Сезоны, в которых у игрока есть турниры (новые сверху), и «Все сезоны» в конце. */
export function seasonOptions(rows: TournamentStatsRow[], seasons: Season[]) {
  const present = new Set(rows.filter((r) => !isEmpty(r.stats)).map((r) => r.season));
  const options = seasons
    .filter((s) => present.has(s.slug))
    .map((s) => ({ value: s.slug, label: s.label }));
  return [...options, { value: "all", label: "Все сезоны" }];
}

/** Строки выбранного сезона (без нулевых — был в заявке, но не играл) и итог по ним. */
export function tournamentRowsFor(rows: TournamentStatsRow[], season: string) {
  const picked = rows.filter((r) => (season === "all" || r.season === season) && !isEmpty(r.stats));
  const total = Object.fromEntries(
    KEYS.map((k) => [k, picked.reduce((sum, r) => sum + (r.stats[k] ?? 0), 0)]),
  ) as Required<PlayerStats>;
  return { rows: picked, total };
}
