import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { EventOut } from "@/lib/types";
import { EventsList } from "./EventsList";

const ev = (type: string, player_name: string): EventOut => ({
  minute: 0,
  type,
  team: "us",
  player_slug: null,
  player_name,
  assist_slug: null,
  assist_name: null,
  note: "минута не указана",
});

describe("EventsList", () => {
  it("shows LFL assists as separate rows without counting them in the score", () => {
    render(<EventsList events={[ev("goal", "Прокопенко Тимофей"), ev("assist", "Гангелин Максим")]} home />);
    expect(screen.getByText("Голевая передача")).toBeInTheDocument();
    expect(screen.getByText("Гангелин Максим")).toBeInTheDocument();
    expect(screen.getByText("минута не указана · 1:0")).toBeInTheDocument();
    expect(screen.queryByText(/2:0/)).not.toBeInTheDocument();
  });
});
