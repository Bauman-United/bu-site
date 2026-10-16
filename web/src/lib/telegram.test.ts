import { telegramHandle, telegramUrl } from "./telegram";

describe("telegramUrl", () => {
  it("turns @handle and bare handle into a t.me link", () => {
    expect(telegramUrl("@captain")).toBe("https://t.me/captain");
    expect(telegramUrl("captain_10")).toBe("https://t.me/captain_10");
    expect(telegramUrl("  @captain ")).toBe("https://t.me/captain");
  });
  it("keeps or completes t.me links", () => {
    expect(telegramUrl("https://t.me/captain")).toBe("https://t.me/captain");
    expect(telegramUrl("t.me/captain")).toBe("https://t.me/captain");
    expect(telegramUrl("http://t.me/captain")).toBe("https://t.me/captain");
  });
  it("passes other URLs through and drops empty values", () => {
    expect(telegramUrl("https://telegram.me/captain")).toBe("https://telegram.me/captain");
    expect(telegramUrl("")).toBeNull();
    expect(telegramUrl(null)).toBeNull();
    expect(telegramUrl(undefined)).toBeNull();
    expect(telegramUrl("@")).toBeNull();
  });
});

describe("telegramHandle", () => {
  it("extracts @handle from links and handles", () => {
    expect(telegramHandle("https://t.me/captain")).toBe("@captain");
    expect(telegramHandle("@captain")).toBe("@captain");
    expect(telegramHandle("https://t.me/+invite")).toBeNull();
    expect(telegramHandle(null)).toBeNull();
  });
});
