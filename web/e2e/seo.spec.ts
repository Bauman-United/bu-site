import { expect, test } from "@playwright/test";

const PAGES = ["/", "/matches", "/standings", "/team", "/team/aleksandr-korolev", "/news",
  "/news/pobeda-nad-energiey", "/matches/2026-09-06-energiya", "/about", "/join", "/hall-of-fame"];

for (const path of PAGES) {
  test(`seo basics ${path}`, async ({ page }) => {
    const res = await page.goto(path);
    expect(res?.status()).toBe(200);
    const title = await page.title();
    expect(title).toContain("Бауман Юнайтед");
    const description = await page.locator('meta[name="description"]').getAttribute("content");
    expect(description?.length ?? 0).toBeGreaterThan(50);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /^https:\/\/baumanunited\.test\//);
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", title);
    await expect(page.locator("h1")).toHaveCount(1);
    for (const json of await page.locator('script[type="application/ld+json"]').allTextContents()) {
      expect(() => JSON.parse(json)).not.toThrow();
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}

test("html is server-rendered (works without JS)", async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto("/matches/2026-09-06-energiya");
  await expect(page.getByText("Финальный свисток")).toBeVisible();
  await ctx.close();
});

test("robots and sitemap", async ({ request }) => {
  const robots = await (await request.get("/robots.txt")).text();
  expect(robots).toContain("Sitemap: https://baumanunited.test/sitemap.xml");
  const sitemap = await (await request.get("/sitemap.xml")).text();
  expect(sitemap).toContain("<loc>https://baumanunited.test/team/aleksandr-korolev</loc>");
  expect(sitemap).toContain("<loc>https://baumanunited.test/matches/2026-09-06-energiya</loc>");
});

test("revalidate endpoint requires secret", async ({ request }) => {
  expect((await request.post("/api/revalidate", { data: { tags: ["home"] } })).status()).toBe(401);
  const ok = await request.post("/api/revalidate", {
    data: { tags: ["home"] }, headers: { authorization: "Bearer e2e" },
  });
  expect(ok.status()).toBe(200);
});
