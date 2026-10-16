import { plural } from "@/lib/format";
import type { PlayerStats } from "@/lib/types";
import s from "./PlayerStatsTiles.module.css";

type Key = keyof PlayerStats;

const TILES: { key: Key; label: (n: number) => string }[] = [
  { key: "played", label: (n) => plural(n, ["матч", "матча", "матчей"]) },
  { key: "goals", label: (n) => plural(n, ["гол", "гола", "голов"]) },
  { key: "assists", label: (n) => plural(n, ["передача", "передачи", "передач"]) },
  { key: "yellow", label: (n) => plural(n, ["жёлтая", "жёлтые", "жёлтых"]) },
  { key: "red", label: (n) => plural(n, ["красная", "красные", "красных"]) },
  { key: "mvp", label: () => "лучший игрок матча" },
];

/** 6 плиток статистики; показатели из `best` (№1 в команде) — инвертированы. */
export function PlayerStatsTiles({ stats, best = [] }: { stats: PlayerStats; best?: string[] }) {
  return (
    <ul className={s.tiles}>
      {TILES.map(({ key, label }) => {
        const value = stats[key] ?? 0;
        const top = best.includes(key);
        return (
          <li key={key} className={top ? `${s.tile} ${s.top}` : s.tile}>
            <span className={s.value}>{value}</span>
            <span className={s.label}>
              {label(value)}
              {top && " · №1 в команде"}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
