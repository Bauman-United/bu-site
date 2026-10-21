import Link from "next/link";
import { FormBadge } from "@/components/ui/FormBadge";
import { formatDate, plural } from "@/lib/format";
import type { MatchDetail, MatchSummary } from "@/lib/types";
import s from "./HeadToHead.module.css";

function score(match: MatchSummary): string {
  return `${match.score_us ?? 0}:${match.score_them ?? 0}`;
}

/** История встреч с соперником перед ещё не сыгранным матчем. */
export function HeadToHead({ data, opponent }: { data: NonNullable<MatchDetail["head_to_head"]>; opponent: string }) {
  const total = data.won + data.drawn + data.lost;
  return (
    <section className={s.section} aria-labelledby="head-to-head-title">
      <div className={`container ${s.inner}`}>
        <div className={s.head}>
          <div>
            <span className={s.eyebrow}>Личные встречи</span>
            <h2 id="head-to-head-title" className={s.h2}>Против {opponent}</h2>
          </div>
          <span className={s.total}>{total} {plural(total, ["матч", "матча", "матчей"])}</span>
        </div>
        <dl className={s.summary} aria-label="Победы, ничьи и поражения">
          <div><dt>Победы</dt><dd>{data.won}</dd></div>
          <div><dt>Ничьи</dt><dd>{data.drawn}</dd></div>
          <div><dt>Поражения</dt><dd>{data.lost}</dd></div>
        </dl>
        {data.recent.length > 0 ? (
          <div className={s.recent}>
            <h3 className={s.h3}>Последние встречи</h3>
            <ol className={s.matches}>
              {data.recent.map((match) => (
                <li key={match.slug}>
                  <Link className={s.match} href={`/matches/${match.slug}`}>
                    <time dateTime={match.kickoff ?? undefined}>{match.kickoff ? formatDate(match.kickoff) : "—"}</time>
                    <span className={s.tournament}>{match.tournament.short}</span>
                    <strong className={s.score}>{score(match)}</strong>
                    {match.outcome && <FormBadge outcome={match.outcome} />}
                  </Link>
                </li>
              ))}
            </ol>
          </div>
        ) : (
          <p className={s.empty}>Раньше с этой командой не встречались.</p>
        )}
      </div>
    </section>
  );
}
