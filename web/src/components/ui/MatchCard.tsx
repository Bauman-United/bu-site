import Image from "next/image";
import Link from "next/link";
import type { MatchDetail, MatchSummary } from "@/lib/types";
import { formatDate, formatTime, outcomeLabel } from "@/lib/format";
import { Crest } from "./Crest";
import { LiveBadge } from "./LiveBadge";
import s from "./MatchCard.module.css";

const US = "Бауман Юнайтед";

function OpponentLogo({ src }: { src: string | null }) {
  if (!src) return <span className={s.logoPlaceholder} aria-hidden="true" />;
  return <Image className={s.logo} src={src} alt="" width={44} height={52} />;
}

/** Белая карточка матча (на чёрной странице): шапка, команды, счёт/время, низ со ссылкой. Хозяева — слева. */
export function MatchCard({ match, variant }: { match: MatchSummary | MatchDetail; variant: "result" | "upcoming" }) {
  const head = [match.tournament.short, match.round].filter(Boolean).join(" · ");
  const when = variant === "upcoming" ? `${formatDate(match.kickoff)} · ${formatTime(match.kickoff)}` : formatDate(match.kickoff);
  const where = match.home ? "Дома" : "В гостях";
  const hasScore = variant === "result" && match.score_us !== null && match.score_them !== null;
  const [left, right] = match.home ? [match.score_us, match.score_them] : [match.score_them, match.score_us];
  const scorers = "scorers_us" in match ? match.scorers_us : [];

  const us = (
    <div className={s.team}>
      <Crest size={44} inverted />
      <span className={s.name}>{US}</span>
    </div>
  );
  const them = (
    <div className={`${s.team} ${s.away}`}>
      <span className={s.name}>{match.opponent_name}</span>
      <OpponentLogo src={match.opponent_logo} />
    </div>
  );
  const themLeft = (
    <div className={s.team}>
      <OpponentLogo src={match.opponent_logo} />
      <span className={s.name}>{match.opponent_name}</span>
    </div>
  );
  const usRight = (
    <div className={`${s.team} ${s.away}`}>
      <span className={s.name}>{US}</span>
      <Crest size={44} inverted />
    </div>
  );

  return (
    <article className={s.card}>
      <div className={s.head}>
        <span className={s.headMain}>
          {match.status === "live" && <LiveBadge />}
          {head}
        </span>
        <span className={s.when}>
          {when} · {where}
        </span>
      </div>
      <div className={s.teams}>
        {match.home ? us : themLeft}
        {hasScore ? (
          <span className={s.score}>
            <span aria-hidden="true">
              {left}:{right}
            </span>
            <span className="visually-hidden">
              {match.outcome ? `${outcomeLabel(match.outcome)} ` : ""}
              {match.score_us}:{match.score_them}
            </span>
          </span>
        ) : (
          <span className={s.vs}>{variant === "upcoming" ? formatTime(match.kickoff) : "VS"}</span>
        )}
        {match.home ? them : usRight}
      </div>
      <div className={s.foot}>
        <span className={s.footText}>
          {variant === "result"
            ? scorers.join(" · ")
            : [match.venue_name, match.venue_address].filter(Boolean).join(", ")}
        </span>
        <Link className={s.more} href={`/matches/${match.slug}`}>
          {variant === "result" ? "Отчёт" : "Подробнее"} →<span className="visually-hidden">: {match.opponent_name}</span>
        </Link>
      </div>
    </article>
  );
}
