import { isActive } from "./nav";

describe("isActive", () => {
  it("matches the section and its subpages", () => {
    expect(isActive("/news", "/news")).toBe(true);
    expect(isActive("/news/pobeda", "/news")).toBe(true);
  });
  it("does not match prefixes of other sections", () => {
    expect(isActive("/newsletter", "/news")).toBe(false);
    expect(isActive("/", "/news")).toBe(false);
  });
});
