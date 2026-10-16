import type { Season } from "./types";

/** Текущий сезон (календарный год) — отмеченный API, иначе новейший (первый в списке). */
export function currentSeason(seasons: Season[]): Season | undefined {
  return seasons.find((s) => s.current) ?? seasons[0];
}
