import type { PlayerDetail } from "@/lib/types";
import { playerDescription } from "./player-meta";

const base = { first_name: "Наиль", last_name: "Мукминов", position: "MF", number: 98, nickname: null } as const;
const player = (season: object, total: object) => ({ ...base, season, total }) as unknown as PlayerDetail;

describe("playerDescription", () => {
  it("former player: club career, no empty season", () => {
    const d = playerDescription(player({ played: 0 }, { played: 31, goals: 7, assists: 4 }));
    expect(d).toContain("За клуб: 31 матч, 7 голов, 4 передачи.");
    expect(d).not.toContain("сезон");
  });

  it("current player: career and season", () => {
    const d = playerDescription(player({ played: 5, goals: 2, assists: 1 }, { played: 40, goals: 12, assists: 9 }));
    expect(d).toMatch(/За клуб: 40 матчей, 12 голов, 9 передач\. В этом сезоне: 5 матчей, 2 гола, 1 передача\.$/);
  });

  it("no games at all: just who the player is", () => {
    expect(playerDescription(player({ played: 0 }, { played: 0 }))).toBe(
      "Наиль Мукминов — полузащитник Бауман Юнайтед (МГТУ им. Баумана), № 98.",
    );
  });
});
