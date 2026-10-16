import { expect, test } from "@playwright/test";

for (const path of ["/", "/matches", "/standings", "/team", "/hall-of-fame", "/news", "/about", "/join", "/partners"]) {
  test(`empty db renders ${path}`, async ({ page }) => {
    const res = await page.goto(path);
    expect(res?.status()).toBe(200);
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.getByText("Что-то пошло не так")).toHaveCount(0);
  });
}

test("empty home hides data blocks", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("timer")).toHaveCount(0);
  await expect(page.locator("table")).toHaveCount(0);
});

test("empty about hides the timeline", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByRole("region", { name: "История по сезонам" })).toHaveCount(0);
});

test("empty hall of fame: intro, no trophies or records", async ({ page }) => {
  await page.goto("/hall-of-fame");
  await expect(page.getByText("С 2019 года — футбольная команда МГТУ им. Н. Э. Баумана.")).toBeVisible();
  await expect(page.getByRole("region", { name: "Трофеи" })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Рекордсмены клуба" })).toHaveCount(0);
  await expect(page.getByText("Трофеи и рекорды появятся")).toBeVisible();
});

// В пустой БД есть только контент клуба (основан 2019, один трофей в истории): матчей и голов 0 —
// эти пункты скрыты, без «0 матчей сыграно». Скрытие блока целиком — в ClubNumbers.test.tsx.
test("empty home shows no zero club numbers", async ({ page }) => {
  await page.goto("/");
  const numbers = page.getByRole("region", { name: "Цифры клуба" });
  await expect(numbers.locator("dd")).toHaveText(["2019", "1"]);
  await expect(numbers.locator("dt")).toHaveText(["основан", "трофей"]);
});

// Сервер этого прогона собран с BU_NOINDEX=0, а запущен с BU_NOINDEX=1 (см. playwright.empty.config):
// robots.txt должен отражать окружение рантайма, а не сборки.
test("robots.txt follows runtime BU_NOINDEX", async ({ request }) => {
  const robots = await (await request.get("/robots.txt")).text();
  expect(robots).toMatch(/^Disallow: \/$/m);
  expect(robots).not.toContain("Sitemap:");
});
