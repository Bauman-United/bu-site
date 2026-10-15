import { expect, test } from "@playwright/test";

test("header, footer and active nav", async ({ page, isMobile }) => {
  await page.goto("/news");
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  if (isMobile) {
    await page.getByRole("button", { name: "Открыть меню" }).click();
    await expect(page.getByRole("dialog", { name: "Меню" })).toBeVisible();
    await expect(page.getByRole("dialog").getByRole("link", { name: "Новости" })).toHaveAttribute("aria-current", "page");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
  } else {
    await expect(page.getByRole("navigation", { name: "Основное меню" }).getByRole("link", { name: "Новости" }))
      .toHaveAttribute("aria-current", "page");
  }
  await expect(page.getByRole("contentinfo")).toContainText("МГТУ им. Н. Э. Баумана");
});

test("404 page in site style", async ({ page }) => {
  const res = await page.goto("/team/no-such-player-xyz");
  expect(res?.status()).toBe(404);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("404");
  await expect(page.getByRole("link", { name: "На главную" })).toBeVisible();
});

test("no horizontal page scroll", async ({ page }) => {
  await page.goto("/");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
