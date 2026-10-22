import { GET } from "./route";

describe("/indexnow.txt", () => {
  afterEach(() => { delete process.env.BU_INDEXNOW_KEY; });

  it("serves the key as plain text", async () => {
    process.env.BU_INDEXNOW_KEY = "k3y";
    const res = GET();
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toContain("text/plain");
    expect(await res.text()).toBe("k3y");
  });

  it("404 without a key", () => {
    expect(GET().status).toBe(404);
  });
});
