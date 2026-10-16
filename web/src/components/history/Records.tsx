import Link from "next/link";
import { Photo } from "@/components/ui/Photo";
import { positionLabel } from "@/lib/format";
import type { AllTimeRecords, RecordRow } from "@/lib/types";
import s from "./Records.module.css";

const LISTS: { key: keyof AllTimeRecords; title: string; unit: string }[] = [
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

/** «Рекордсмены клуба» за всё время: топ по голам, передачам и матчам, бывшие игроки тоже. */
export function Records({ records }: { records: AllTimeRecords }) {
  const lists = LISTS.filter(({ key }) => records[key].length > 0);
  if (lists.length === 0) return null;
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
      </div>
    </section>
  );
}
