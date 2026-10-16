import {
  historyIntro,
  isWin,
  placeLabel,
  sortTrophies,
  trophySummary,
  type Trophy,
} from "./history";

const T = (place: number, title = "Кубок", season = "Осень 2023"): Trophy => ({ place, title, season });

describe("sortTrophies", () => {
  it("keeps valid trophies, first places first, stable within a place", () => {
    const list = [T(3, "A"), T(1, "B"), T(2, "C"), T(1, "D"), { place: 1 } as Trophy, T(5, "E")];
    expect(sortTrophies(list).map((t) => t.title)).toEqual(["B", "D", "C", "A"]);
  });
});

describe("trophySummary", () => {
  it("counts places with Russian plurals", () => {
    const list = [...Array(7)].map(() => T(1)).concat([T(2), T(2), T(2), T(3), T(3)]);
    expect(trophySummary(list)).toBe("7 побед · 3 серебра · 2 бронзы");
  });
  it("skips zero groups", () => {
    expect(trophySummary([T(1), T(3)])).toBe("1 победа · 1 бронза");
    expect(trophySummary([])).toBe("");
  });
});

describe("placeLabel", () => {
  it("labels places", () => {
    expect(placeLabel(1)).toEqual({ place: "1 место", note: "Победа" });
    expect(placeLabel(2)).toEqual({ place: "2 место", note: "Серебро" });
    expect(placeLabel(3)).toEqual({ place: "3 место", note: "Бронза" });
  });
});

describe("isWin", () => {
  const trophies = [T(1, "Кубок BL", "Осень 2023"), T(2, "Финал", "Весна 2023")];
  it("is a win when highlighted and a first place was won that season", () => {
    expect(isWin({ year: "Осень 2023", title: "x", highlight: true }, trophies)).toBe(true);
  });
  it("is not a win for non-highlighted or seasons without gold", () => {
    expect(isWin({ year: "Осень 2023", title: "x", highlight: false }, trophies)).toBe(false);
    expect(isWin({ year: "Весна 2023", title: "x", highlight: true }, trophies)).toBe(false);
    expect(isWin({ year: "2016", title: "Основание", highlight: true }, trophies)).toBe(false);
  });
});

describe("historyIntro", () => {
  it("builds the intro from club data and timeline tags", () => {
    expect(
      historyIntro(
        { name: "Бауман Юнайтед", founded: 2016, university: "МГТУ им. Н. Э. Баумана", socials: { lfl: "https://lfl" } },
        [{ year: "2019", tag: "IFL", title: "x" }, { year: "2020", tag: "BL", title: "y" }, { year: "2016", tag: "Основание", title: "z" }],
      ),
    ).toBe("С 2016 года — футбольная команда МГТУ им. Н. Э. Баумана. Bauman League, IFL, ЛФЛ.");
  });
  it("degrades without data", () => {
    expect(historyIntro({ name: "Бауман Юнайтед" }, [])).toBe("");
    expect(historyIntro({ name: "Бауман Юнайтед", founded: 2019 }, [])).toBe("С 2019 года — футбольная команда.");
  });
});
