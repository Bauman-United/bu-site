import { render, screen } from "@testing-library/react";
import { LeagueTabs, parseLeague } from "./LeagueTabs";

describe("LeagueTabs", () => {
  it("parseLeague: bl/lfl, anything else → «Общий» (undefined)", () => {
    expect(parseLeague("bl")).toBe("bl");
    expect(parseLeague("lfl")).toBe("lfl");
    expect(parseLeague(["lfl", "bl"])).toBe("lfl");
    expect(parseLeague("ifl")).toBe("ifl");
    expect(parseLeague("xyz")).toBeUndefined();
    expect(parseLeague(undefined)).toBeUndefined();
  });

  it("renders exactly three plain links with the active one marked", () => {
    render(<LeagueTabs pathname="/team" selected="lfl" />);
    const links = screen.getAllByRole("link");
    expect(links.map((l) => [l.textContent, l.getAttribute("href")])).toEqual([
      ["Общий", "/team"],
      ["БЛ", "/team?league=bl"],
      ["ЛФЛ", "/team?league=lfl"],
    ]);
    expect(screen.getByRole("link", { name: "ЛФЛ" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Общий" })).not.toHaveAttribute("aria-current");
  });

  it("adds «IFL» only when the team plays IFL this season", () => {
    render(<LeagueTabs pathname="/team" selected="ifl" withIfl />);
    const links = screen.getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual(["Общий", "БЛ", "ЛФЛ", "IFL"]);
    expect(screen.getByRole("link", { name: "IFL" })).toHaveAttribute("href", "/team?league=ifl");
    expect(screen.getByRole("link", { name: "IFL" })).toHaveAttribute("aria-current", "page");
  });
});
