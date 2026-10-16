import { expect, test } from "@playwright/test";

test("join page shows contacts and CTA", async ({ page }) => {
  await page.goto("/join");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Хочешь в команду/i);
  await expect(page.getByText("Вратаря")).toBeVisible();
  await expect(page.getByText("Вторник и четверг")).toBeVisible();
  await expect(page.getByRole("link", { name: "Написать капитану" })).toHaveAttribute("href", "https://t.me/captain");
});

test("about page", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/О клубе/i);
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /МГТУ им\. Н\. Э\. Баумана/);
});
