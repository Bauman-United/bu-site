import { expect, test } from "@playwright/test";

test("squad grouped by position", async ({ page }) => {
  await page.goto("/team");
  for (const g of ["Вратари", "Защитники", "Полузащитники", "Нападающие"]) {
    await expect(page.getByRole("heading", { level: 2, name: new RegExp(g) })).toBeVisible();
  }
  await expect(page.getByRole("link", { name: /Константинопольский/ })).toBeVisible();
  await page.getByRole("link", { name: /Королев/ }).first().click();
  await expect(page).toHaveURL("/team/aleksandr-korolev");
});

test("squad tabs: Общий / БЛ / ЛФЛ", async ({ page }) => {
  await page.goto("/team");
  const tabs = page.getByRole("navigation", { name: "Лига" });
  await expect(tabs.getByRole("link")).toHaveText(["Общий", "БЛ", "ЛФЛ"]);
  await expect(tabs.getByRole("link", { name: "Общий" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("link", { name: /Егор Куча/ })).toBeVisible();

  await tabs.getByRole("link", { name: "ЛФЛ" }).click();
  await expect(page).toHaveURL(/\/team\?league=lfl$/);
  await expect(tabs.getByRole("link", { name: "ЛФЛ" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("link", { name: /Дмитрий Писарев/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Егор Куча/ })).toHaveCount(0);

  await page.goto("/team?league=nope");
  await expect(tabs.getByRole("link", { name: "Общий" })).toHaveAttribute("aria-current", "page");
});

test("player profile", async ({ page }) => {
  await page.goto("/team/aleksandr-korolev");
  await expect(page).toHaveTitle(/^Александр Королев — Полузащитник — /);
  await expect(page.getByText("Король").first()).toBeVisible();
  await expect(page.getByText("№1 в команде").first()).toBeVisible();
  await expect(page.getByText(/Отдал 6 передач/)).toBeVisible();
  await page.getByRole("button", { name: "За всё время" }).click();
  await expect(page.getByRole("button", { name: "За всё время" })).toHaveAttribute("aria-pressed", "true");
  const ld = (await page.locator('script[type="application/ld+json"]').allTextContents()).map((t) => JSON.parse(t));
  expect(ld.find((d) => d["@type"] === "Person").name).toBe("Александр Королев");
  await expect(page.locator("body")).not.toContainText(/\d{2}\.\d{2}\.\d{4}/);
});

test("player page uses its own og:image", async ({ page }) => {
  await page.goto("/team/aleksandr-korolev");
  await expect(page.locator('meta[property="og:image"]'))
    .toHaveAttribute("content", /\/team\/aleksandr-korolev\/opengraph-image/);
});

test("player og image", async ({ request }) => {
  const res = await request.get("/team/aleksandr-korolev/opengraph-image");
  expect(res.headers()["content-type"]).toContain("image/png");
});

test("player profile splits stats by tournament", async ({ page }) => {
  await page.goto("/team/aleksandr-korolev");
  const table = page.getByRole("table", { name: "По турнирам" });
  await expect(table).toBeVisible();
  const row = table.getByRole("row", { name: /Лига Инженеров/ });
  await expect(row).toContainText("3"); // сыграно матчей в сид-данных e2e
  await expect(table.getByRole("columnheader", { name: "КК" })).toBeVisible();
});

test("tournament stats can be filtered by season", async ({ page }) => {
  await page.goto("/team/dmitriy-pisarev");
  const table = page.getByRole("table", { name: "По турнирам" });
  const seasons = page.getByRole("group", { name: "Сезон" });
  await expect(seasons.getByRole("button", { name: "2026" })).toHaveAttribute("aria-pressed", "true");
  await expect(table).not.toContainText("Весна 2020");
  await seasons.getByRole("button", { name: "2020" }).click();
  await expect(table).toContainText("Весна 2020");
  await expect(table).not.toContainText("Осень 2026");
  await seasons.getByRole("button", { name: "Все сезоны" }).click();
  await expect(table.getByRole("row", { name: /Итого/ })).toBeVisible();
});
