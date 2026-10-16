import { matchDescription, matchTitle } from "./match-meta";

const undated = {
  slug: "kvazar-5877228", kickoff: null, home: false, opponent_name: "Квазар", status: "scheduled",
  score_us: null, score_them: null, outcome: null, venue_name: null, round: "Четвертьфинал",
  tournament: { name: "Кубок Специалистов · Осень 2026" }, scorers_us: [],
} as never;

describe("match meta without a date", () => {
  it("title says the date is TBD", () => {
    expect(matchTitle(undated)).toBe("Бауман Юнайтед — Квазар, дата уточняется");
  });
  it("description says the date is TBD", () => {
    expect(matchDescription(undated)).toBe("Матч Кубок Специалистов · Осень 2026, Четвертьфинал: дата уточняется.");
  });
});
