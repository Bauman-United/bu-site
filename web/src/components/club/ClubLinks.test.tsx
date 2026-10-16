import { render, screen } from "@testing-library/react";
import { Footer } from "@/components/layout/Footer";
import { externalLinks } from "@/components/layout/socials";
import { ClubLinks } from "./ClubLinks";

const club = {
  name: "Бауман Юнайтед",
  socials: { telegram: "https://t.me/bu", lfl: "https://lfl.ru/club1", joinfootball: "https://bl.join.football/t/1" },
};

describe("league pages", () => {
  it("externalLinks: socials, then «Страница в ЛФЛ», then «Страница в БЛ»", () => {
    expect(externalLinks(club).map((l) => l.label)).toEqual(["Telegram", "Страница в ЛФЛ", "Страница в БЛ"]);
  });

  it("«Страница в IFL» goes after БЛ when set", () => {
    const labels = externalLinks({ ...club, socials: { ...club.socials, ifl: "https://ifl-bmstu.ru/team/1003070" } }).map((l) => l.label);
    expect(labels).toEqual(["Telegram", "Страница в ЛФЛ", "Страница в БЛ", "Страница в IFL"]);
  });

  it("«Страница в Urban Cup» goes after IFL when set", () => {
    const socials = { ...club.socials, ifl: "https://ifl-bmstu.ru/team/1003070", urban: "https://urban-cup.ru/team/1321682" };
    const links = externalLinks({ ...club, socials });
    expect(links.map((l) => l.label)).toEqual(["Telegram", "Страница в ЛФЛ", "Страница в БЛ", "Страница в IFL", "Страница в Urban Cup"]);
    expect(links.at(-1)?.href).toBe("https://urban-cup.ru/team/1321682");
  });

  it("skips «Страница в БЛ» when joinfootball is not set", () => {
    const labels = externalLinks({ ...club, socials: { lfl: "https://lfl.ru/club1" } }).map((l) => l.label);
    expect(labels).toEqual(["Страница в ЛФЛ"]);
  });

  it("ClubLinks («Следи за командой») shows both league pages", () => {
    render(<ClubLinks club={club} title="Следи за командой" />);
    expect(screen.getByRole("link", { name: "Страница в ЛФЛ" })).toHaveAttribute("href", "https://lfl.ru/club1");
    expect(screen.getByRole("link", { name: "Страница в БЛ" })).toHaveAttribute("href", "https://bl.join.football/t/1");
  });

  it("footer shows both league pages", () => {
    render(<Footer club={club} />);
    expect(screen.getByRole("link", { name: "Страница в БЛ" })).toHaveAttribute("href", "https://bl.join.football/t/1");
    expect(screen.getByRole("link", { name: "Страница в ЛФЛ" })).toBeInTheDocument();
  });
});
