import type { Standings } from "@/lib/types";
import { formatDate } from "@/lib/format";
import s from "./StandingsTable.module.css";

const FULL: [string, string][] = [["И", "Игры"], ["В", "Победы"], ["Н", "Ничьи"], ["П", "Поражения"], ["М", "Мячи"], ["О", "Очки"]];
const COMPACT: [string, string][] = [["И", "Игры"], ["О", "Очки"]];

export function StandingsTable({ standings, compact = false, caption }: {
  standings: Standings; compact?: boolean; caption?: string;
}) {
  const cols = compact ? COMPACT : FULL;
  return (
    <div className={s.wrap}>
      <div className="table-scroll">
        <table className={s.table}>
          <caption className="visually-hidden">{caption ?? `Турнирная таблица: ${standings.tournament.name}`}</caption>
          <thead>
            <tr className={s.head}>
              <th scope="col" className={s.pos}>#</th>
              <th scope="col">Команда</th>
              {cols.map(([abbr, full]) => (
                <th key={abbr} scope="col" className={s.num}>
                  <abbr title={full}>{abbr}</abbr>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {standings.rows.map((r) => (
              <tr key={`${r.pos}-${r.team_name}`} className={r.is_us ? s.us : s.row} aria-current={r.is_us ? "true" : undefined}>
                <td className={s.pos}>{r.pos}</td>
                <th scope="row" className={s.team}>{r.team_name}</th>
                <td className={s.num}>{r.played}</td>
                {!compact && (
                  <>
                    <td className={s.num}>{r.won}</td>
                    <td className={s.num}>{r.drawn}</td>
                    <td className={s.num}>{r.lost}</td>
                    <td className={`${s.num} ${s.goals}`}>{r.gf}–{r.ga}</td>
                  </>
                )}
                <td className={`${s.num} ${s.pts}`}>{r.pts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(standings.updated_at || standings.source_url) && (
        <div className={s.meta}>
          {standings.updated_at && <span>Обновлено {formatDate(standings.updated_at)}</span>}
          {standings.source_url && (
            <a className={s.source} href={standings.source_url} target="_blank" rel="noopener">
              Полная таблица ↗
            </a>
          )}
        </div>
      )}
    </div>
  );
}
