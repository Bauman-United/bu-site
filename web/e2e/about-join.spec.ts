import { expect, test } from "@playwright/test";

test("join page shows contacts and captain link", async ({ page }) => {
  await page.goto("/join");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Хочешь в команду/i);
  await expect(page.getByText("Вратаря")).toBeVisible();
  await expect(page.getByText("Вторник и четверг")).toBeVisible();
  await expect(page.getByRole("link", { name: "Написать капитану" })).toHaveAttribute("href", "https://t.me/captain");
});

/** Уникальный IP на тест: в API лимит 3 заявки с IP в час, а прогоны повторяются. */
async function uniqueIp(page: import("@playwright/test").Page) {
  const n = () => Math.floor(Math.random() * 250) + 1;
  await page.setExtraHTTPHeaders({ "X-Forwarded-For": `198.51.${n()}.${n()}` });
}

test("join form: submit application → success", async ({ page }) => {
  await uniqueIp(page);
  await page.goto("/join");
  await page.getByLabel("Фамилия и имя").fill("Иванов Иван");
  await page.getByLabel("Позиция").selectOption("Защитник");
  await page.getByLabel("Возраст").fill("21");
  await page.getByLabel("Опыт: где и сколько играл").fill("Секция ЦСКА 5 лет, любительская лига");
  await page.getByLabel("Выпускник").check();
  await page.getByLabel("Контакт для связи").fill("@ivanov");
  await page.getByRole("button", { name: "Отправить заявку" }).click();
  await expect(page.getByText("Заявка отправлена! Капитан напишет тебе в ближайшее время.")).toBeVisible();
});

test("join form: too short experience → field error", async ({ page }) => {
  await uniqueIp(page);
  await page.goto("/join");
  await page.getByLabel("Фамилия и имя").fill("Иванов Иван");
  await page.getByLabel("Позиция").selectOption("Вратарь");
  await page.getByLabel("Возраст").fill("19");
  await page.getByLabel("Опыт: где и сколько играл").fill("мало");
  await page.getByLabel("Да, учусь").check();
  await page.getByLabel("Контакт для связи").fill("@ivanov");
  await page.getByRole("button", { name: "Отправить заявку" }).click();
  const experience = page.getByLabel("Опыт: где и сколько играл");
  await expect(experience).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByText(/от 10 до 1500 символов/)).toBeVisible();
  await expect(experience).toHaveValue("мало");
  await expect(page.getByLabel("Фамилия и имя")).toHaveValue("Иванов Иван");
});

test("about page", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/О клубе/i);
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /МГТУ им\. Н\. Э\. Баумана/);
});
