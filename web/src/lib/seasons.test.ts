import { describe, expect, it } from "vitest";
import { currentSeason } from "./seasons";

const season = (slug: string, current = false) => ({ slug, label: slug, final_place: null, current });

describe("currentSeason", () => {
  it("is the season marked current, not the newest", () => {
    expect(currentSeason([season("2027"), season("2026", true), season("2025")])?.slug).toBe("2026");
  });
  it("falls back to the newest season", () => {
    expect(currentSeason([season("2026"), season("2025")])?.slug).toBe("2026");
  });
  it("is undefined without seasons", () => {
    expect(currentSeason([])).toBeUndefined();
  });
});
