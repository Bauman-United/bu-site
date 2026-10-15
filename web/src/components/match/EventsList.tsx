import Link from "next/link";
import type { EventOut } from "@/lib/types";
import s from "./EventsList.module.css";

const KIND: Record<string, { label: string; title: string; style: string }> = {
  goal: { label: "Гол", title: "Гол", style: s.goal },
  penalty: { label: "Гол", title: "Гол с пенальти", style: s.goal },
  own_goal: { label: "Гол", title: "Автогол", style: s.goal },
  yellow: { label: "ЖК", title: "Жёлтая карточка", style: s.yellow },
  red: { label: "КК", title: "Красная карточка", style: s.red },
  sub: { label: "Замена", title: "Замена", style: s.sub },
};
const GOALS = new Set(["goal", "penalty", "own_goal"]);

function Player({ slug, name, ours }: { slug: string | null; name: string | null; ours: boolean }) {
  if (!name) return null;
  if (ours && slug) return <Link href={`/team/${slug}`}>{name}</Link>;
  return <>{name}</>;
}

function Side({ e, ours, score }: { e: EventOut; ours: boolean; score?: string }) {
  const notes = [
    e.type === "penalty" ? "пенальти" : null,
    e.type === "own_goal" ? "автогол" : null,
    e.note,
    score,
  ].filter(Boolean);
  return (
    <>
      <span className={s.player}>
        <Player slug={e.player_slug} name={e.player_name} ours={ours} />
        {e.assist_name && (
          <span className={s.assist}>
            {" ("}
            <Player slug={e.assist_slug} name={e.assist_name} ours={ours} />
            {")"}
          </span>
        )}
      </span>
      {notes.length > 0 && <span className={s.note}>{notes.join(" · ")}</span>}
    </>
  );
}

/**
 * События по минутам: наши — слева, минута и тип — по центру, соперника — справа.
 * Для голов показывается счёт после гола в порядке хозяева:гости.
 */
/** Счёт после каждого гола (хозяева:гости); для прочих событий — undefined. */
function runningScores(events: EventOut[], home: boolean): (string | undefined)[] {
  let us = 0;
  let them = 0;
  return events.map((e) => {
    if (!GOALS.has(e.type)) return undefined;
    if (e.team === "us") us += 1;
    else them += 1;
    return home ? `${us}:${them}` : `${them}:${us}`;
  });
}

export function EventsList({ events, home }: { events: EventOut[]; home: boolean }) {
  const scores = runningScores(events, home);
  return (
    <ol className={s.list}>
      {events.map((e, i) => {
        const ours = e.team === "us";
        const kind = KIND[e.type] ?? { label: e.type, title: e.type, style: s.sub };
        return (
          <li key={i} className={s.row}>
            <div className={s.ours}>{ours && <Side e={e} ours score={scores[i]} />}</div>
            <div className={s.mid}>
              <span className={s.minute}>{e.minute}&apos;</span>
              <span className={`${s.kind} ${kind.style}`} title={kind.title}>
                <span aria-hidden="true">{kind.label}</span>
                <span className="visually-hidden">{kind.title}{ours ? "" : " соперника"}</span>
              </span>
            </div>
            <div className={s.theirs}>{!ours && <Side e={e} ours={false} score={scores[i]} />}</div>
          </li>
        );
      })}
    </ol>
  );
}
