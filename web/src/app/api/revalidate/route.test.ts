const { revalidateTag } = vi.hoisted(() => ({ revalidateTag: vi.fn() }));
vi.mock("next/cache", () => ({ revalidateTag }));

import { POST } from "./route";

const req = (auth: string | null, body: unknown) =>
  new Request("http://x/api/revalidate", {
    method: "POST",
    headers: auth ? { authorization: auth, "content-type": "application/json" } : { "content-type": "application/json" },
    body: JSON.stringify(body),
  });

describe("POST /api/revalidate", () => {
  beforeEach(() => { revalidateTag.mockReset(); process.env.BU_REVALIDATE_SECRET = "s3"; });

  it("rejects wrong secret", async () => {
    const res = await POST(req("Bearer nope", { tags: ["home"] }));
    expect(res.status).toBe(401);
    expect(revalidateTag).not.toHaveBeenCalled();
  });

  it("revalidates tags", async () => {
    const res = await POST(req("Bearer s3", { tags: ["home", "matches"] }));
    expect(res.status).toBe(200);
    expect(revalidateTag).toHaveBeenCalledWith("home", "max");
    expect(revalidateTag).toHaveBeenCalledWith("matches", "max");
  });

  it("503 when secret not configured", async () => {
    delete process.env.BU_REVALIDATE_SECRET;
    expect((await POST(req("Bearer s3", { tags: [] }))).status).toBe(503);
  });
});
