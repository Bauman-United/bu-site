import { expect, test } from "@playwright/test";

test("home renders data blocks from API", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Бауман");
  await expect(page.getByRole("timer")).toHaveAccessibleName(/^До матча \d+ (день|дня|дней)/);
  await expect(page.getByText("Мессия").first()).toBeVisible();
  await expect(page.getByRole("img", { name: /^Победа 3:1/ }).first()).toBeVisible();
  await expect(page.locator("tr[aria-current='true']")).toContainText("Bauman United");
  await expect(page.getByRole("link", { name: /Победа над «Энергией»/ })).toBeVisible();
  await expect(page.getByText("Дмитрий Писарев").first()).toBeVisible();
});

test("home has SportsTeam JSON-LD and canonical", async ({ page }) => {
  await page.goto("/");
  const ld = await page.locator('script[type="application/ld+json"]').allTextContents();
  const team = ld.map((t) => JSON.parse(t)).find((d) => d["@type"] === "SportsTeam");
  expect(team.memberOf.name).toBe("МГТУ им. Н. Э. Баумана");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://baumanunited.test/");
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /бауманка/);
});
