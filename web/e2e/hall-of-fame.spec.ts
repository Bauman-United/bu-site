import { expect, test } from "@playwright/test";

test("/history permanently redirects to /hall-of-fame", async ({ request }) => {
  const res = await request.get("/history", { maxRedirects: 0 });
  expect([301, 308]).toContain(res.status());
  expect(res.headers()["location"]).toMatch(/\/hall-of-fame$/);
});

test("hall of fame: trophies sorted by place", async ({ page, isMobile }) => {
  await page.goto("/hall-of-fame");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Зал славы/i);
  await expect(page).toHaveTitle(/Зал славы/);
  if (!isMobile) {
    await expect(page.getByRole("navigation", { name: "Основное меню" }).getByRole("link", { name: "Зал славы" }))
      .toHaveAttribute("aria-current", "page");
  }

  const fame = page.getByRole("region", { name: "Трофеи" });
  await expect(fame.getByText("1 победа · 1 серебро · 1 бронза")).toBeVisible();
  await expect(fame.getByRole("listitem").locator("h3")).toHaveText([
    "Кубок BL", "Bauman League, первый дивизион", "IFL, второй дивизион",
  ]);
  await expect(fame.getByRole("listitem").first()).toContainText("1 место");
});

test("hall of fame: all-time records include departed players", async ({ page }) => {
  await page.goto("/hall-of-fame");
  const records = page.getByRole("region", { name: "Рекордсмены клуба" });
  const goals = records.getByRole("list", { name: "Голы" }).getByRole("listitem");
  // Старый Ветеран играл в 2020 и ушёл — но в рекордах за всё время он первый
  await expect(goals.first()).toContainText("1");
  await expect(goals.first().getByRole("link")).toHaveText("Старый Ветеран");
  await expect(goals.first().getByRole("link")).toHaveAttribute("href", "/team/staryy-veteran");
  await expect(goals.first()).toContainText("25");
  await expect(goals.first()).toContainText("Нападающий");
  // Писарев: 4 гола в 2020 + 4 в этом сезоне
  await expect(goals.nth(1).getByRole("link")).toHaveText("Дмитрий Писарев");
  await expect(goals.nth(1)).toContainText("8");

  const assists = records.getByRole("list", { name: "Передачи" }).getByRole("listitem");
  await expect(assists.first().getByRole("link")).toHaveText("Дмитрий Писарев");
  await expect(assists.first()).toContainText("10");

  const played = records.getByRole("list", { name: "Матчи" }).getByRole("listitem");
  await expect(played.first().getByRole("link")).toHaveText("Старый Ветеран");
  await expect(played.first()).toContainText("40");
  await expect(played).toHaveCount(7);

  const keepers = records.getByRole("table");
  await expect(keepers.getByRole("row", { name: /Егор Куча/ })).toContainText("12");
});

test("home: «трофеев» in club numbers leads to the hall of fame", async ({ page }) => {
  await page.goto("/");
  const numbers = page.getByRole("region", { name: "Цифры клуба" });
  await expect(numbers.getByRole("link", { name: /трофе/ })).toHaveAttribute("href", "/hall-of-fame");
});
