import { expect, test } from "@playwright/test";

for (const path of ["/", "/matches", "/standings", "/team", "/news", "/about", "/join"]) {
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
