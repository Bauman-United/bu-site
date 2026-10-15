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

test("garbage query does not break the page", async ({ page }) => {
  const res = await page.goto("/matches?where=xxx&t=&season=zzz");
  expect(res?.status()).toBe(200);
  await expect(page.getByRole("img", { name: "Победа 3:1" })).toBeVisible();
});

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
  await expect(page.getByRole("heading", { level: 2, name: /Лига Инженеров/ })).toBeVisible();
  await expect(page.locator("tr[aria-current='true']")).toContainText("Bauman United");
  await expect(page.getByText(/Обновлено 12 октября 2026/)).toBeVisible();
});
