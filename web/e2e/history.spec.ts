import { expect, test } from "@playwright/test";

test("history: intro, timeline with highlighted win, hall of fame", async ({ page }) => {
  await page.goto("/history");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/История клуба/i);
  await expect(page.getByText("С 2019 года — футбольная команда МГТУ им. Н. Э. Баумана.")).toBeVisible();
  const anchors = page.getByRole("navigation", { name: "Разделы истории" });
  await expect(anchors.getByRole("link")).toHaveText(["По сезонам", "Зал славы"]);

  const events = page.locator("#timeline li");
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

  const fame = page.getByRole("region", { name: "Зал славы" });
  await expect(fame.getByText("1 победа · 1 серебро · 1 бронза")).toBeVisible();
  await expect(fame.getByRole("listitem").locator("h3")).toHaveText([
    "Кубок BL", "Bauman League, первый дивизион", "IFL, второй дивизион",
  ]);
  await expect(fame.getByRole("listitem").first()).toContainText("1 место");
});
