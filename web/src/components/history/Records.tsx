import Link from "next/link";
import { Photo } from "@/components/ui/Photo";
import { positionLabel } from "@/lib/format";
import type { AllTimeRecords, GoalkeeperRecord, RecordRow } from "@/lib/types";
import s from "./Records.module.css";

const LISTS: { key: "goals" | "assists" | "played"; title: string; unit: string }[] = [
  { key: "goals", title: "Голы", unit: "голов" },
  { key: "assists", title: "Передачи", unit: "передач" },
  { key: "played", title: "Матчи", unit: "матчей" },
];

function Row({ row }: { row: RecordRow }) {
  return (
    <li className={s.row}>
      <span className={s.rank}>{row.rank}</span>
      <span className={s.photo}>
        <Photo src={row.photo} alt={row.photo ? row.name : ""} ratio="1 / 1" sizes="48px" />
      </span>
      <span className={s.who}>
        <Link className={s.name} href={`/team/${row.slug}`}>{row.name}</Link>
        <span className={s.position}>{positionLabel(row.position)}</span>
      </span>
      <span className={s.value}>{row.value}</span>
    </li>
  );
}

function Goalkeepers({ rows }: { rows: GoalkeeperRecord[] }) {
  if (rows.length === 0) return null;
  return (
    <div className={s.goalkeepers}>
      <div className={s.goalkeepersHead}>
        <h3 className={s.goalkeepersTitle}>Вратари по эффективности</h3>
        <span className={s.goalkeepersNote}>Минимум 11 матчей · меньше — лучше</span>
      </div>
      <div className={s.tableScroll}>
        <table className={s.table}>
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Вратарь</th>
              <th scope="col">Матчи</th>
              <th scope="col">Пропущено за матч</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.slug}>
                <td className={s.tableRank}>{row.rank}</td>
                <td>
                  <Link className={s.keeper} href={`/team/${row.slug}`}>
                    <span className={s.keeperPhoto}>
                      <Photo src={row.photo} alt={row.photo ? row.name : ""} ratio="1 / 1" sizes="40px" />
                    </span>
                    <span>{row.name}</span>
                  </Link>
                </td>
                <td>{row.played}</td>
                <td className={s.efficiency}>{row.efficiency.toFixed(2).replace(".", ",")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** «Рекордсмены клуба» за всё время: топ по голам, передачам и матчам, бывшие игроки тоже. */
export function Records({ records }: { records: AllTimeRecords }) {
  const lists = LISTS.filter(({ key }) => records[key].length > 0);
  if (lists.length === 0 && records.goalkeepers.length === 0) return null;
  return (
    <section id="records" className="section" aria-labelledby="records-title">
      <div className={`container ${s.wrap}`}>
        <div className={s.head}>
          <h2 id="records-title" className={s.h2}>Рекордсмены клуба</h2>
          <span className={s.note}>За всё время, во всех турнирах</span>
        </div>
        <div className={s.grid}>
          {lists.map(({ key, title, unit }) => (
            <div key={key} className={s.list}>
              <h3 id={`records-${key}`} className={s.h3}>
                {title}
                <span className={s.unit}>{unit}</span>
              </h3>
              <ol className={s.rows} aria-label={title}>
                {records[key].map((row) => <Row key={row.slug} row={row} />)}
              </ol>
            </div>
          ))}
        </div>
        <Goalkeepers rows={records.goalkeepers} />
      </div>
    </section>
  );
}
