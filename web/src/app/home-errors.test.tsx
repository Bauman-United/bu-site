const { getHome, getClub } = vi.hoisted(() => ({ getHome: vi.fn(), getClub: vi.fn() }));
vi.mock("@/lib/api", () => ({ getHome, getClub }));

import HomePage from "./page";

/** Ошибка API не должна превращаться в пустую страницу с 200: страница бросает, Next рендерит error.tsx. */
describe("home page API errors", () => {
  it("propagates a getHome failure", async () => {
    getHome.mockRejectedValue(new Error("API 503 for /home"));
    getClub.mockResolvedValue({ name: "Бауман Юнайтед" });
    await expect(HomePage()).rejects.toThrow("API 503 for /home");
  });

  it("propagates a getClub failure", async () => {
    getHome.mockResolvedValue({});
    getClub.mockRejectedValue(new Error("API 500 for /club"));
    await expect(HomePage()).rejects.toThrow("API 500 for /club");
  });
});
