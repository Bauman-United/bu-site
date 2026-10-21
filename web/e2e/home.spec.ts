import { expect, test } from "@playwright/test";

test("home renders data blocks from API", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана");
  const title = page.getByRole("heading", { level: 1 });
  await expect(title).toContainText("Бауман");
  const titleOffset = await title.evaluate((element) => {
    const hero = element.closest("section");
    if (!hero) return Number.POSITIVE_INFINITY;
    return element.getBoundingClientRect().top - hero.getBoundingClientRect().top;
  });
  expect(titleOffset).toBeLessThanOrEqual(130);
  await expect(page.getByRole("timer")).toHaveAccessibleName(/^До матча \d+ (день|дня|дней)/);
  await expect(page.getByText("Мессия").first()).toBeVisible();
  const nextMatch = page.getByRole("region", { name: "Следующий матч" });
  await expect(nextMatch.getByRole("link", { name: /О матче/ })).toHaveAttribute("href", "/matches/2030-10-24-messiya");
  await expect(nextMatch.getByRole("link", { name: /Как добраться/ })).toHaveAttribute("target", "_blank");
  await expect(page.getByRole("img", { name: /^Победа 3:1/ }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Победа над «Энергией»/ })).toBeVisible();
  await expect(page.getByText("Дмитрий Писарев").first()).toBeVisible();
});

test("next match actions stay at the right on desktop and fit on mobile", async ({ page, isMobile }) => {
  await page.goto("/");
  const nextMatch = page.getByRole("region", { name: "Следующий матч" });
  const actions = nextMatch.getByRole("link", { name: /О матче/ }).locator("../..");
  const card = actions.locator("..");
  const [actionsBox, cardBox] = await Promise.all([actions.boundingBox(), card.boundingBox()]);

  expect(actionsBox).not.toBeNull();
  expect(cardBox).not.toBeNull();
  if (!actionsBox || !cardBox) return;

  if (isMobile) {
    expect(actionsBox.x + actionsBox.width).toBeLessThanOrEqual(cardBox.x + cardBox.width);
  } else {
    expect(actionsBox.x).toBeGreaterThan(cardBox.x + cardBox.width / 2);
    expect(cardBox.x + cardBox.width - (actionsBox.x + actionsBox.width)).toBeLessThanOrEqual(44);
  }
});

test("home shows last result and mini table for both leagues", async ({ page }) => {
  await page.goto("/");
  const leagues: [string, RegExp][] = [
    ["Бауманская лига", /Отчёт о матче.*Раскат/],
    ["ЛФЛ", /Отчёт о матче.*Долгопрудненский политех/],
  ];
  for (const [title, report] of leagues) {
    const block = page.getByRole("region", { name: title, exact: true });
    await expect(block.getByRole("heading", { name: title, exact: true })).toBeVisible();
    await expect(block.getByRole("link", { name: report })).toBeVisible();
    await expect(block.locator("tr[aria-current='true']")).toHaveCount(1);
    await expect(block.locator("tr[aria-current='true']")).toContainText("Bauman United");
  }
  // форма — одна, общая для всех турниров
  await expect(page.getByRole("heading", { name: /^Форма/ })).toHaveCount(1);
});

test("home has SportsTeam JSON-LD and canonical", async ({ page }) => {
  await page.goto("/");
  const ld = await page.locator('script[type="application/ld+json"]').allTextContents();
  const team = ld.map((t) => JSON.parse(t)).find((d) => d["@type"] === "SportsTeam");
  expect(team.memberOf.name).toBe("МГТУ им. Н. Э. Баумана");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://baumanunited.test/");
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /бауманка/);
});

test("season leaders show player photos", async ({ page }) => {
  await page.goto("/");
  const section = page.getByRole("region", { name: "Лидеры сезона" });
  for (const role of ["Бомбардир", "Ассистент"]) {
    const img = section.locator("article", { hasText: role }).locator("img");
    await expect(img).toHaveCount(1);
    await expect.poll(() => img.evaluate((el: HTMLImageElement) => el.complete && el.naturalWidth > 0)).toBe(true);
  }
});
