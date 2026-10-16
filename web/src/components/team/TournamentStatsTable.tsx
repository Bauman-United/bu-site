"use client";

import { useState } from "react";
import { seasonOptions, tournamentRowsFor, type TournamentStatsRow } from "@/lib/tournament-stats";
import type { Season } from "@/lib/types";
import toggle from "./SeasonToggle.module.css";
import s from "./TournamentStatsTable.module.css";

const KEYS = ["played", "goals", "assists", "yellow", "red", "mvp"] as const;

/** «По турнирам» с фильтром по сезону (по умолчанию — текущий сезон игрока). */
export function TournamentStatsTable({
  rows,
  seasons,
  currentSeason,
  tableClass,
  captionClass,
  totalRowClass,
}: {
  rows: TournamentStatsRow[];
  seasons: Season[];
  currentSeason?: string;
  tableClass: string;
  captionClass: string;
  totalRowClass: string;
}) {
  const options = seasonOptions(rows, seasons);
  const initial = options.some((o) => o.value === currentSeason) ? currentSeason! : options[0].value;
  const [season, setSeason] = useState(initial);
  const { rows: visible, total } = tournamentRowsFor(rows, season);
  if (options.length === 1) return null; // только «Все сезоны» — значит, турниров нет

  return (
    <div className={s.wrap}>
      <div className={s.head}>
        <h3 className={captionClass} id="by-tournament">По турнирам</h3>
        <div className={`${toggle.group} ${s.seasons}`} role="group" aria-label="Сезон">
          {options.map((o) => (
            <button
              key={o.value}
              type="button"
              className={toggle.button}
              aria-pressed={season === o.value}
              onClick={() => setSeason(o.value)}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>
      <div className={s.scroll}>
        <table className={tableClass} aria-labelledby="by-tournament">
          <thead>
            <tr>
              <th scope="col">Турнир</th>
              <th scope="col">Матчи</th>
              <th scope="col">Голы</th>
              <th scope="col">Передачи</th>
              <th scope="col">ЖК</th>
              <th scope="col">КК</th>
              <th scope="col">MVP</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.tournament.slug}>
                <th scope="row">{row.tournament.name}</th>
                {KEYS.map((k) => (
                  <td key={k}>{row.stats[k] ?? 0}</td>
                ))}
              </tr>
            ))}
            {visible.length > 1 && (
              <tr className={totalRowClass}>
                <th scope="row">Итого</th>
                {KEYS.map((k) => (
                  <td key={k}>{total[k]}</td>
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
