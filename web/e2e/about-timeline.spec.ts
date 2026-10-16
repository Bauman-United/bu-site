import { expect, test } from "@playwright/test";

test("about: timeline below the about text with highlighted win", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/О клубе/i);
  const timeline = page.getByRole("region", { name: "История по сезонам" });
  await expect(timeline.getByRole("heading", { level: 2 })).toHaveText("История по сезонам");

  const events = timeline.locator("li");
  await expect(events).toHaveCount(3);
  const win = events.filter({ hasText: "Победа в Кубке BL" });
  await expect(win).toHaveAttribute("data-highlight", "true");
  await expect(win.getByText("Победа", { exact: true })).toBeVisible();
  await expect(win.getByText("Финал на стадионе МГТУ.")).toBeVisible();
  // Ключевое событие без трофея — выделено, но без плашки «Победа»
  const founding = events.filter({ hasText: "Основание команды" });
  await expect(founding).toHaveAttribute("data-highlight", "true");
  await expect(founding.getByText("Победа", { exact: true })).toHaveCount(0);
  const silver = events.filter({ hasText: "Серебро первого дивизиона BL" });
  await expect(silver).not.toHaveAttribute("data-highlight", "true");
});
