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
