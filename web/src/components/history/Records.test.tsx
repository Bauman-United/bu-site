import { render, screen, within } from "@testing-library/react";
import type { AllTimeRecords } from "@/lib/types";
import { Records } from "./Records";

const row = (rank: number, slug: string, name: string, value: number, extra = {}) => ({
  rank, slug, name, value, played: value, photo: null, position: "FW", active: true, ...extra,
});

describe("Records", () => {
  it("three top lists: rank, photo or placeholder, linked name, value, position", () => {
    const records: AllTimeRecords = {
      goals: [row(1, "staryy-veteran", "Старый Ветеран", 25, { active: false, photo: "/crest-white.png" })],
      assists: [row(1, "a", "Игрок А", 13, { position: null })],
      played: [row(1, "b", "Игрок Б", 40, { position: "GK" })],
    };
    render(<Records records={records} />);
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Рекордсмены клуба");
    const goals = within(screen.getByRole("list", { name: "Голы" })).getAllByRole("listitem");
    expect(goals[0]).toHaveTextContent("1");
    expect(within(goals[0]).getByRole("link", { name: "Старый Ветеран" })).toHaveAttribute("href", "/team/staryy-veteran");
    expect(goals[0]).toHaveTextContent("25");
    expect(goals[0]).toHaveTextContent("Нападающий");
    expect(within(goals[0]).getByRole("img")).toBeInTheDocument();
    const assists = within(screen.getByRole("list", { name: "Передачи" })).getAllByRole("listitem");
    expect(assists[0]).toHaveTextContent("Игрок");
    expect(within(screen.getByRole("list", { name: "Матчи" })).getAllByRole("listitem")[0]).toHaveTextContent("Вратарь");
  });

  it("hides empty lists and renders nothing when all are empty", () => {
    const { container, rerender } = render(<Records records={{ goals: [], assists: [], played: [] }} />);
    expect(container).toBeEmptyDOMElement();
    rerender(<Records records={{ goals: [], assists: [], played: [row(1, "b", "Игрок Б", 1)] }} />);
    expect(screen.queryByRole("list", { name: "Голы" })).toBeNull();
    expect(screen.getByRole("list", { name: "Матчи" })).toBeInTheDocument();
  });
});
