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
