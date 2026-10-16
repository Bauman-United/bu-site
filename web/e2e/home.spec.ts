import { expect, test } from "@playwright/test";

test("home renders data blocks from API", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Бауман");
  await expect(page.getByRole("timer")).toHaveAccessibleName(/^До матча \d+ (день|дня|дней)/);
  await expect(page.getByText("Мессия").first()).toBeVisible();
  await expect(page.getByRole("img", { name: /^Победа 3:1/ }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Победа над «Энергией»/ })).toBeVisible();
  await expect(page.getByText("Дмитрий Писарев").first()).toBeVisible();
});

test("home shows last result and mini table for both leagues", async ({ page }) => {
  await page.goto("/");
  const leagues: [string, RegExp][] = [
    ["Бауманская лига", /Отчёт о матче.*Раскат/],
    ["ЛФЛ", /Отчёт о матче.*Долгопрудненский политех/],
  ];
  for (const [title, report] of leagues) {
    const block = page.getByRole("region", { name: title, exact: true });
    await expect(block.getByRole("heading", { name: title, exact: true })).toBeVisible();
    await expect(block.getByRole("link", { name: report })).toBeVisible();
    await expect(block.locator("tr[aria-current='true']")).toHaveCount(1);
    await expect(block.locator("tr[aria-current='true']")).toContainText("Bauman United");
  }
  // форма — одна, общая для всех турниров
  await expect(page.getByRole("heading", { name: /^Форма/ })).toHaveCount(1);
});

test("home has SportsTeam JSON-LD and canonical", async ({ page }) => {
  await page.goto("/");
  const ld = await page.locator('script[type="application/ld+json"]').allTextContents();
  const team = ld.map((t) => JSON.parse(t)).find((d) => d["@type"] === "SportsTeam");
  expect(team.memberOf.name).toBe("МГТУ им. Н. Э. Баумана");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://baumanunited.test/");
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /бауманка/);
});
