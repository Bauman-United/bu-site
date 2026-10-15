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
  it("takes the first of repeated params", () => {
    expect(parseMatchFilters({ where: ["away", "home"] }, tournaments, seasons))
      .toEqual({ season: undefined, tournament: undefined, where: "away", isFiltered: true });
  });
  it("builds hrefs", () => {
    expect(filterHref({ season: "2026-27", where: "home" }, { where: undefined })).toBe("/matches?season=2026-27");
    expect(filterHref({}, { t: "liga" })).toBe("/matches?t=liga");
  });
});
