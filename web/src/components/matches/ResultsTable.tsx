import Link from "next/link";
import type { MatchSummary, Outcome } from "@/lib/types";
import { formatDayMonth, outcomeLabel, outcomeLetter } from "@/lib/format";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import s from "./ResultsTable.module.css";

const LEGEND: Outcome[] = ["W", "D", "L"];

/** «Сыгранные»: таблица со счётом-бейджем; на узком экране скроллится внутри `.table-scroll`. */
export function ResultsTable({ matches }: { matches: MatchSummary[] }) {
  return (
    <div className={s.wrap}>
      <div className="table-scroll">
        <table className={s.table}>
          <caption className="visually-hidden">Сыгранные матчи</caption>
          <thead>
            <tr className={s.head}>
              <th scope="col">Дата</th>
              <th scope="col">Турнир</th>
              <th scope="col">Соперник</th>
              <th scope="col">Где</th>
              <th scope="col" className={s.center}>Счёт</th>
              <th scope="col"><span className="visually-hidden">Ссылка</span></th>
            </tr>
          </thead>
          <tbody>
            {matches.map((m) => (
              <tr key={m.slug} className={s.row}>
                <td className={s.date}>{formatDayMonth(m.kickoff)}</td>
                <td className={s.tournament}>{[m.tournament.short, m.round].filter(Boolean).join(" · ")}</td>
                <td className={s.opponent}>{m.opponent_name}</td>
                <td className={s.where}>{m.home ? "Дома" : "В гостях"}</td>
                <td className={s.center}>
                  {m.outcome && m.score_us !== null && m.score_them !== null ? (
                    <ScoreBadge outcome={m.outcome} us={m.score_us} them={m.score_them} />
                  ) : (
                    "—"
                  )}
                </td>
                <td className={s.link}>
                  <Link href={`/matches/${m.slug}`}>
                    Матч →<span className="visually-hidden">: {m.opponent_name}</span>
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className={s.legend} aria-label="Обозначения">
        {LEGEND.map((o) => (
          <li key={o} className={s.legendItem}>
            <span className={`${s.swatch} ${s[o]}`} aria-hidden="true">{outcomeLetter(o)}</span>
            {outcomeLabel(o)}
          </li>
        ))}
      </ul>
    </div>
  );
}
