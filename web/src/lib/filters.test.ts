import { filterHref, parseMatchFilters } from "./filters";

const tournaments = [{ slug: "lfl-2026", short: "ЛФЛ" }, { slug: "liga", short: "ЛИ" }] as never;
const seasons = [{ slug: "2026", label: "2026", final_place: null }] as never;

describe("match filters", () => {
  it("drops unknown values but still counts them as filtered (noindex)", () => {
    expect(parseMatchFilters({ where: "xxx", t: "", season: "1999-00" }, tournaments, seasons))
      .toEqual({ season: undefined, tournament: undefined, where: undefined, isFiltered: true });
    for (const sp of [{ where: "xxx" }, { t: "zzz" }, { season: "zzz" }, { where: ["xxx"] }]) {
      expect(parseMatchFilters(sp, tournaments, seasons).isFiltered).toBe(true);
    }
  });
  it("empty or absent filter params are not filtered", () => {
    expect(parseMatchFilters({}, tournaments, seasons).isFiltered).toBe(false);
    expect(parseMatchFilters({ where: "", t: "", season: [""], utm_source: "tg" }, tournaments, seasons).isFiltered)
      .toBe(false);
  });
  it("keeps known values", () => {
    expect(parseMatchFilters({ where: "home", t: "liga", season: "2026" }, tournaments, seasons))
      .toEqual({ season: "2026", tournament: "liga", where: "home", isFiltered: true });
  });
  it("takes the first of repeated params", () => {
    expect(parseMatchFilters({ where: ["away", "home"] }, tournaments, seasons))
      .toEqual({ season: undefined, tournament: undefined, where: "away", isFiltered: true });
  });
  it("builds hrefs", () => {
    expect(filterHref({ season: "2026", where: "home" }, { where: undefined })).toBe("/matches?season=2026");
    expect(filterHref({}, { t: "liga" })).toBe("/matches?t=liga");
  });
});
