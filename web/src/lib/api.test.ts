import { ApiError, apiGet, apiGetOrNull } from "./api";

const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

describe("api client", () => {
  beforeEach(() => {
    process.env.BU_API_URL = "http://api.test";
  });
  afterEach(() => vi.restoreAllMocks());

  it("builds url with query, skips empty params and passes cache tags", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(ok([]));
    await apiGet("/matches", { tags: ["matches"], query: { season: "2026", where: undefined, t: "" } });
    const [url, init] = spy.mock.calls[0] as [string, RequestInit & { next: unknown }];
    expect(url).toBe("http://api.test/matches?season=2026");
    expect(init.next).toEqual({ revalidate: 300, tags: ["matches"] });
  });

  it("404 → null in apiGetOrNull, other errors throw ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("", { status: 404 }));
    expect(await apiGetOrNull("/matches/x")).toBeNull();
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("", { status: 502 }));
    await expect(apiGet("/home")).rejects.toBeInstanceOf(ApiError);
  });
});
