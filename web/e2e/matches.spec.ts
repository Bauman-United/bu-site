import { expect, test } from "@playwright/test";

test("matches page lists upcoming and results with filters", async ({ page }) => {
  await page.goto("/matches");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Матчи/i);
  await expect(page.getByRole("img", { name: "Победа 3:1" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Ничья 2:2" })).toBeVisible();
  await expect(page.getByText("Мессия").first()).toBeVisible();
  await page.getByRole("link", { name: "Дома", exact: true }).click();
  await expect(page).toHaveURL(/where=home/);
  await expect(page.getByRole("img", { name: "Ничья 2:2" })).toHaveCount(0);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://baumanunited.test/matches");
});

test("filtered URL serves noindex on a hard load", async ({ page }) => {
  const res = await page.goto("/matches?where=home");
  expect(res?.status()).toBe(200);
  const html = (await res?.text()) ?? "";
  expect(html).toMatch(/<meta name="robots" content="noindex, follow"\/?>/);
  expect(html).toContain('<link rel="canonical" href="https://baumanunited.test/matches"');
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
});

test("garbage query does not break the page", async ({ page }) => {
  const res = await page.goto("/matches?where=xxx&t=&season=zzz");
  expect(res?.status()).toBe(200);
  await expect(page.getByRole("img", { name: "Победа 3:1" })).toBeVisible();
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, follow");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://baumanunited.test/matches");
});

for (const query of ["where=xxx", "t=zzz", "season=zzz"]) {
  test(`unrecognised filter ${query} is noindex`, async ({ request }) => {
    const html = await (await request.get(`/matches?${query}`)).text();
    expect(html).toMatch(/<meta name="robots" content="noindex, follow"\/?>/);
    expect(html).toContain('<link rel="canonical" href="https://baumanunited.test/matches"');
  });
}

test("results table scrolls inside its box, page does not", async ({ page, isMobile }) => {
  await page.goto("/matches");
  await expect(page.getByRole("cell", { name: "Долгопрудненский политех имени очень длинного названия", exact: true })).toBeVisible();
  const pageOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(pageOverflow).toBeLessThanOrEqual(0);
  if (isMobile) {
    const box = page.locator(".table-scroll").filter({ has: page.getByRole("table", { name: "Сыгранные матчи" }) });
    const scrolls = await box.evaluate((el) => el.scrollWidth > el.clientWidth);
    expect(scrolls).toBe(true);
  }
});

test("standings page", async ({ page }) => {
  await page.goto("/standings");
  await page.getByRole("navigation", { name: "Турнир" }).getByRole("link", { name: "Лига Инженеров" }).click();
  await expect(page.getByRole("heading", { level: 2, name: /Лига Инженеров/ })).toBeVisible();
  await expect(page.locator("tr[aria-current='true']")).toContainText("Bauman United");
  await expect(page.getByText(/Обновлено 12 октября 2026/)).toBeVisible();
});

test("undated match shows «Дата уточняется» and its page renders", async ({ page }) => {
  await page.goto("/matches");
  const card = page.locator("a", { hasText: "Квазар" }).first();
  await expect(card).toBeVisible();
  await expect(card).toContainText("Дата уточняется");
  const res = await page.goto("/matches/kvazar-5877228");
  expect(res?.status()).toBe(200);
  await expect(page.getByText("Квазар").first()).toBeVisible();
  await expect(page.getByText("Дата уточняется").first()).toBeVisible();
  await expect(page.getByRole("timer")).toHaveCount(0);
});
