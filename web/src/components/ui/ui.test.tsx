import { render, screen } from "@testing-library/react";
import { FormBadge } from "./FormBadge";
import { NewsTag } from "./NewsTag";
import { ScoreBadge } from "./ScoreBadge";
import { StandingsTable } from "./StandingsTable";

const standings = {
  tournament: { slug: "li", name: "Лига Инженеров", short: "ЛИ", kind: "league", season: "2026-27", url: null },
  updated_at: "2026-10-12T10:00:00+03:00",
  source_url: "https://jf/tables",
  rows: [
    { pos: 1, team_name: "Раскат", team_logo: null, played: 5, won: 5, drawn: 0, lost: 0, gf: 21, ga: 4, pts: 15, is_us: false },
    { pos: 6, team_name: "Bauman United", team_logo: null, played: 5, won: 2, drawn: 0, lost: 3, gf: 17, ga: 19, pts: 6, is_us: true },
  ],
};

describe("ui kit", () => {
  it("form badge is accessible without color", () => {
    render(<FormBadge outcome="W" us={3} them={1} opponent="Энергия" />);
    expect(screen.getByLabelText("Победа 3:1 vs Энергия")).toHaveTextContent("В");
  });

  it("score badge", () => {
    render(<ScoreBadge outcome="L" us={2} them={3} />);
    expect(screen.getByLabelText("Поражение 2:3")).toHaveTextContent("2:3");
  });

  it("news tag labels", () => {
    render(<NewsTag tag="social" platform="telegram" />);
    expect(screen.getByText("Telegram")).toBeInTheDocument();
  });

  it("standings marks our row", () => {
    render(<StandingsTable standings={standings as never} />);
    const us = screen.getByText("Bauman United").closest("tr");
    expect(us).toHaveAttribute("aria-current", "true");
    expect(screen.getByText(/Обновлено/)).toHaveTextContent("12 октября 2026");
  });
});
