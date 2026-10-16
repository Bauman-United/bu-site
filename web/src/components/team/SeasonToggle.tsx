"use client";

import { type ReactNode, useState } from "react";
import type { PlayerStats } from "@/lib/types";
import { PlayerStatsTiles } from "./PlayerStatsTiles";
import s from "./SeasonToggle.module.css";

type Period = "season" | "total";

/**
 * Заголовок блока + переключатель «Сезон / За всё время» и плитки статистики.
 * Клиентское состояние (URL не меняется); «№1 в команде» считается по сезону — подсветка только в режиме сезона.
 */
export function SeasonToggle({
  title,
  seasonLabel,
  season,
  total,
  teamBest,
}: {
  title: ReactNode;
  seasonLabel?: string;
  season: PlayerStats;
  total: PlayerStats;
  teamBest: string[];
}) {
  const [period, setPeriod] = useState<Period>("season");
  const options: [Period, string][] = [
    ["season", seasonLabel ? `Сезон ${seasonLabel}` : "Сезон"],
    ["total", "За всё время"],
  ];
  return (
    <>
      <div className={s.head}>
        {title}
        <div className={s.group} role="group" aria-label="Период">
          {options.map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={s.button}
              aria-pressed={period === value}
              onClick={() => setPeriod(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <PlayerStatsTiles
        stats={period === "season" ? season : total}
        best={period === "season" ? teamBest : []}
      />
    </>
  );
}
