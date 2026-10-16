import Image from "next/image";
import type { MatchSummary } from "@/lib/types";
import { formatWhen } from "@/lib/format";
import { ButtonLink } from "@/components/ui/Button";
import { Countdown } from "@/components/ui/Countdown";
import { Crest } from "@/components/ui/Crest";
import s from "./NextMatch.module.css";

function OpponentMark({ match }: { match: MatchSummary }) {
  if (match.opponent_logo) {
    return <Image className={s.logo} src={match.opponent_logo} alt="" width={72} height={84} />;
  }
  return (
    <span className={s.initial} aria-hidden="true">
      {match.opponent_name.trim().charAt(0)}
    </span>
  );
}

/** Белая секция «Следующий матч»: гербы, турнир/тур, дата и место, обратный отсчёт, «Как добраться». */
export function NextMatch({ match }: { match: MatchSummary }) {
  const head = [match.tournament.short, match.round].filter(Boolean).join(" · ");
  const when = formatWhen(match.kickoff);
  const venue = [match.venue_name, match.venue_address].filter(Boolean).join(", ");
  const mapQuery = match.venue_address ?? match.venue_name;
  return (
    <section className="section section--paper" aria-labelledby="next-match">
      <div className={`container ${s.wrap}`}>
        <div className={s.header}>
          <h2 id="next-match" className={s.h2}>Следующий матч</h2>
          {head && <span className={s.head}>{head}</span>}
        </div>
        <div className={s.box}>
          <div className={s.teams}>
            <div className={s.team}>
              <Crest size={72} inverted />
              <span className={s.name}>Бауман Юнайтед</span>
            </div>
            <span className={s.vs}>VS</span>
            <div className={s.team}>
              <OpponentMark match={match} />
              <span className={s.name}>{match.opponent_name}</span>
            </div>
          </div>
          <div className={s.info}>
            {match.kickoff ? (
              <time className={s.when} dateTime={match.kickoff}>{when}</time>
            ) : (
              <span className={s.when}>{when}</span>
            )}
            {venue && <span className={s.muted}>{venue}</span>}
            <span className={s.muted}>{match.home ? "Дома" : "В гостях"}</span>
          </div>
          <div className={s.actions}>
            {match.kickoff && (
              <div className={s.timer}>
                <Countdown kickoff={match.kickoff} />
              </div>
            )}
            {mapQuery && (
              <div className={s.route}>
                <ButtonLink href={`https://yandex.ru/maps/?text=${encodeURIComponent(mapQuery)}`} onPaper external>
                  Как добраться
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true" focusable="false">
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </ButtonLink>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
