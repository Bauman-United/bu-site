import { act, render, screen } from "@testing-library/react";
import { Countdown } from "./Countdown";

describe("Countdown", () => {
  afterEach(() => vi.useRealTimers());

  it("declines units and ticks every minute", () => {
    vi.useFakeTimers();
    const kickoff = "2026-10-24T21:30:00+03:00";
    vi.setSystemTime(Date.parse(kickoff) - (2 * 86400 + 1 * 3600 + 5 * 60) * 1000);
    render(<Countdown kickoff={kickoff} />);
    expect(screen.getByRole("timer")).toHaveAccessibleName("До матча 2 дня 1 час 5 минут");
    act(() => { vi.advanceTimersByTime(60_000); });
    expect(screen.getByRole("timer")).toHaveAccessibleName("До матча 2 дня 1 час 4 минуты");
  });

  it("shows live text after kickoff", () => {
    vi.useFakeTimers();
    vi.setSystemTime(Date.parse("2026-10-24T21:40:00+03:00"));
    render(<Countdown kickoff="2026-10-24T21:30:00+03:00" />);
    expect(screen.getByText("Матч идёт")).toBeInTheDocument();
  });
});
