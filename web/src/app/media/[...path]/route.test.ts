import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { GET } from "./route";

const dir = mkdtempSync(path.join(tmpdir(), "bu-media-"));
mkdirSync(path.join(dir, "tg"));
writeFileSync(path.join(dir, "tg", "tg-1.jpg"), "0123456789");
writeFileSync(path.join(dir, "secret.txt"), "x");

const get = (parts: string[], headers: Record<string, string> = {}) =>
  GET(new Request("http://x/media", { headers }), { params: Promise.resolve({ path: parts }) });

describe("/media", () => {
  beforeAll(() => { process.env.BU_MEDIA_DIR = dir; });
  afterAll(() => { delete process.env.BU_MEDIA_DIR; });

  it("serves a file with its type and long cache", async () => {
    const res = await get(["tg", "tg-1.jpg"]);
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toBe("image/jpeg");
    expect(res.headers.get("cache-control")).toContain("immutable");
    expect(await res.text()).toBe("0123456789");
  });

  it("answers range requests (video in Safari)", async () => {
    const res = await get(["tg", "tg-1.jpg"], { range: "bytes=2-4" });
    expect(res.status).toBe(206);
    expect(res.headers.get("content-range")).toBe("bytes 2-4/10");
    expect(await res.text()).toBe("234");
    expect((await get(["tg", "tg-1.jpg"], { range: "bytes=50-" })).status).toBe(416);
  });

  it("404 for missing files, foreign types and path tricks", async () => {
    expect((await get(["tg", "nope.jpg"])).status).toBe(404);
    expect((await get(["secret.txt"])).status).toBe(404);
    expect((await get(["..", "tg", "tg-1.jpg"])).status).toBe(404);
    expect((await get(["tg", "..%2Ftg-1.jpg"])).status).toBe(404);
  });
});
