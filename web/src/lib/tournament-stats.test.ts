import { seasonOptions, tournamentRowsFor } from "./tournament-stats";

const stats = (played: number, goals = 0) => ({ played, goals, assists: 0, yellow: 0, red: 0, mvp: 0 });
const row = (slug: string, season: string, played: number, goals = 0) => ({
  tournament: { slug, name: slug, short: slug, kind: "league", season, url: null },
  season,
  stats: stats(played, goals),
});

const rows = [
  row("lfl-26", "2026", 9),
  row("cup-26", "2026", 0),
  row("li-25", "2025", 3, 1),
  row("ifl-19", "2019", 7, 5),
];
const seasons = [
  { slug: "2026", label: "2026", final_place: null },
  { slug: "2025", label: "2025", final_place: null },
  { slug: "2019", label: "2019", final_place: null },
  { slug: "2018", label: "2018", final_place: null },
];

describe("tournament stats by season", () => {
  it("offers only seasons the player has rows in, newest first, plus «all»", () => {
    expect(seasonOptions(rows as never, seasons as never)).toEqual([
      { value: "2026", label: "2026" },
      { value: "2025", label: "2025" },
      { value: "2019", label: "2019" },
      { value: "all", label: "Все сезоны" },
    ]);
  });

  it("filters by season, hides all-zero rows and sums the total", () => {
    const current = tournamentRowsFor(rows as never, "2026");
    expect(current.rows.map((r) => r.tournament.slug)).toEqual(["lfl-26"]);
    expect(current.total.played).toBe(9);
    const all = tournamentRowsFor(rows as never, "all");
    expect(all.rows).toHaveLength(3);
    expect(all.total).toMatchObject({ played: 19, goals: 6 });
  });
});
