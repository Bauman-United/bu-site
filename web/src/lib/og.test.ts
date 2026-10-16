const { readFile } = vi.hoisted(() => ({ readFile: vi.fn(async (p: string) => Buffer.from(String(p))) }));
vi.mock("node:fs/promises", () => ({ readFile, default: { readFile } }));

import { ogFonts } from "./og";

describe("ogFonts", () => {
  it("reads the font files once and reuses the buffers", async () => {
    const a = await ogFonts();
    const b = await ogFonts();
    expect(readFile).toHaveBeenCalledTimes(2); // cyrillic + latin, only on the first call
    expect(b[0].data).toBe(a[0].data);
    expect(a.map((f) => f.name)).toEqual(["Oswald", "Oswald Latin"]);
    expect(String(a[0].data)).toContain("oswald-cyrillic-700-normal.woff");
  });
});
