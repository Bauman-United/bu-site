import { expect, test } from "@playwright/test";

test("finished match page", async ({ page }) => {
  await page.goto("/matches/2026-09-06-energiya");
  await expect(page).toHaveTitle(/^Бауман Юнайтед 3:1 Энергия — /);
  await expect(page.getByText("Финальный свисток")).toBeVisible();
  await expect(page.getByText("Королев 12'").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Александр Королев" }).first()).toHaveAttribute("href", "/team/aleksandr-korolev");
  await expect(page.getByRole("link", { name: /Читать полностью/ })).toHaveAttribute("href", "/news/pobeda-nad-energiey");
  const ld = (await page.locator('script[type="application/ld+json"]').allTextContents()).map((t) => JSON.parse(t));
  const ev = ld.find((d) => d["@type"] === "SportsEvent");
  expect(ev.eventStatus).toBe("https://schema.org/EventCompleted");
  expect(ev.homeTeam.name).toBe("Бауман Юнайтед");
  await expect(page.locator('meta[property="og:image"]'))
    .toHaveAttribute("content", /\/matches\/2026-09-06-energiya\/opengraph-image/);
});

test("upcoming away match page", async ({ page }) => {
  await page.goto("/matches/2030-10-24-messiya");
  await expect(page.getByRole("timer")).toBeVisible();
  await expect(page.getByText("В гостях").first()).toBeVisible();
  const history = page.getByRole("region", { name: "Против Мессия" });
  await expect(history).toContainText("Победы1");
  await expect(history.getByRole("link", { name: /1:0/ })).toBeVisible();
  const summary = history.getByLabel("Победы, ничьи и поражения");
  const trailingSpace = await summary.evaluate((element) => {
    const lastItem = element.lastElementChild;
    if (!lastItem) return Number.POSITIVE_INFINITY;
    return element.getBoundingClientRect().right - lastItem.getBoundingClientRect().right;
  });
  expect(trailingSpace).toBeLessThanOrEqual(2);
});

test("og image renders", async ({ request }) => {
  const res = await request.get("/matches/2026-09-06-energiya/opengraph-image");
  expect(res.status()).toBe(200);
  expect(res.headers()["content-type"]).toContain("image/png");
});

test("unknown match is 404", async ({ page }) => {
  expect((await page.goto("/matches/nope"))?.status()).toBe(404);
});
