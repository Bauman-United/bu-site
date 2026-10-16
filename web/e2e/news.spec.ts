import { expect, test } from "@playwright/test";

test("news list with featured, tags and social post", async ({ page }) => {
  await page.goto("/news");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Новости/i);
  await expect(page.getByRole("link", { name: /Победа над «Энергией»/ }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Открыть оригинал/ })).toHaveAttribute("href", "https://t.me/baumanunited/1");
  await page.getByRole("link", { name: "Трансфер", exact: true }).click();
  await expect(page).toHaveURL(/tag=transfer/);
  await expect(page.getByText("У нас новый защитник")).toBeVisible();
  await expect(page.getByText("Итоги сентября")).toHaveCount(0);
});

test("news article renders markdown and JSON-LD", async ({ page }) => {
  await page.goto("/news/pobeda-nad-energiey");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Победа над «Энергией» на старте");
  await expect(page.getByRole("heading", { level: 2, name: "Как это было" })).toBeVisible();
  await expect(page.locator("article strong")).toHaveText("12-й");
  await expect(page.getByRole("link", { name: /К матчу/ })).toHaveAttribute("href", "/matches/2026-09-06-energiya");
  const ld = (await page.locator('script[type="application/ld+json"]').allTextContents()).map((t) => JSON.parse(t));
  expect(ld.find((d) => d["@type"] === "NewsArticle").headline).toBe("Победа над «Энергией» на старте");
});

test("unknown news is 404", async ({ page }) => {
  expect((await page.goto("/news/nope"))?.status()).toBe(404);
});

test("tag filter serves noindex on a hard load", async ({ request }) => {
  const res = await request.get("/news?tag=transfer");
  expect(res.status()).toBe(200);
  const html = await res.text();
  expect(html).toMatch(/<meta name="robots" content="noindex, follow"\/?>/);
  expect(html).toContain('<link rel="canonical" href="https://baumanunited.test/news"');
});

test("unfiltered list is indexable with a plain canonical", async ({ request }) => {
  const html = await (await request.get("/news")).text();
  expect(html).toMatch(/<meta name="robots" content="index, follow"\/?>/);
  expect(html).toContain('<link rel="canonical" href="https://baumanunited.test/news"');
});

test("unknown tag is ignored, out-of-range page shows empty state", async ({ page }) => {
  const res = await page.goto("/news?tag=xxx&page=0");
  expect(res?.status()).toBe(200);
  await expect(page.getByText("Итоги сентября")).toBeVisible();
  await page.goto("/news?page=99");
  await expect(page.getByText("Новостей пока нет")).toBeVisible();
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://baumanunited.test/news?page=99");
});
