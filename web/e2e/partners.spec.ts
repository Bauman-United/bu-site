import { expect, type Page, test } from "@playwright/test";

/** Уникальный IP на тест: в API лимит 3 заявки с IP в час, а прогоны повторяются. */
async function uniqueIp(page: Page) {
  const n = () => Math.floor(Math.random() * 250) + 1;
  await page.setExtraHTTPHeaders({ "X-Forwarded-For": `203.0.${n()}.${n()}` });
}

test("header «Стать партнёром» button opens /partners", async ({ page, isMobile }) => {
  await page.goto("/");
  if (isMobile) await page.getByRole("button", { name: "Открыть меню" }).click();
  const scope = isMobile ? page.getByRole("dialog", { name: "Меню" }) : page.getByRole("banner");
  await scope.getByRole("link", { name: "Стать партнёром" }).click();
  await expect(page).toHaveURL(/\/partners$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Стать партнёром/i);
  await expect(page).toHaveTitle(/^Партнёрам — /);
});

test("partners form: submit → success", async ({ page }) => {
  await uniqueIp(page);
  await page.goto("/partners");
  await page.getByLabel("Расскажите о себе и предложении").fill("Магазин экипировки, готовы обсудить форму");
  await page.getByLabel("Контакт для связи").fill("partner@example.com");
  await page.getByRole("button", { name: "Отправить заявку" }).click();
  await expect(page.getByText("Заявка отправлена! Мы свяжемся с вами в ближайшее время.")).toBeVisible();
});

test("partners form: too short text → field error", async ({ page }) => {
  await uniqueIp(page);
  await page.goto("/partners");
  await page.getByLabel("Расскажите о себе и предложении").fill("мало");
  await page.getByLabel("Контакт для связи").fill("@partner");
  await page.getByRole("button", { name: "Отправить заявку" }).click();
  const about = page.getByLabel("Расскажите о себе и предложении");
  await expect(about).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByText(/от 10 до 2000 символов/)).toBeVisible();
  await expect(about).toHaveValue("мало");
  await expect(page.getByLabel("Контакт для связи")).toHaveValue("@partner");
});
