import { placeLabel, sortTrophies, trophySummary, type Trophy } from "@/lib/history";
import { Cup } from "./Cup";
import s from "./Trophies.module.css";

function TrophyCard({ trophy }: { trophy: Trophy }) {
  const label = placeLabel(trophy.place);
  return (
    <li className={`${s.trophy} ${trophy.place === 1 ? s.gold : ""}`} data-place={trophy.place}>
      <Cup size={64} />
      <span className={s.place}>{label.place}</span>
      <span className={s.placeNote}>{label.note}</span>
      <h3 className={s.trophyTitle}>{trophy.title}</h3>
      {trophy.season && <span className={s.season}>{trophy.season}</span>}
    </li>
  );
}

/** Трофеи: призовые места по месту (1 — первым), сверху счётчик «N побед · …». */
export function Trophies({ trophies }: { trophies: Trophy[] }) {
  const list = sortTrophies(trophies);
  if (list.length === 0) return null;
  return (
    <section id="trophies" className="section section--paper" aria-labelledby="trophies-title">
      <div className={`container ${s.fame}`}>
        <div className={s.head}>
          <h2 id="trophies-title" className={s.title}>Трофеи</h2>
          <span className={s.summary}>{trophySummary(list)}</span>
        </div>
        <ul className={s.trophies}>
          {list.map((t, i) => <TrophyCard key={i} trophy={t} />)}
        </ul>
      </div>
    </section>
  );
}
