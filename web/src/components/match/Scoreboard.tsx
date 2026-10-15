import Image from "next/image";
import type { MatchDetail } from "@/lib/types";
import { formatDate, formatTime, formatWeekday, outcomeLabel } from "@/lib/format";
import { SITE_NAME } from "@/lib/seo";
import { Countdown } from "@/components/ui/Countdown";
import { Crest } from "@/components/ui/Crest";
import { LiveBadge } from "@/components/ui/LiveBadge";
import s from "./Scoreboard.module.css";

function OpponentMark({ match }: { match: MatchDetail }) {
  if (match.opponent_logo) {
    return <Image className={s.logo} src={match.opponent_logo} alt="" width={96} height={110} />;
  }
  return (
    <span className={s.initial} aria-hidden="true">
      {match.opponent_name.trim().charAt(0)}
    </span>
  );
}

function Side({ mark, name, scorers }: { mark: React.ReactNode; name: string; scorers: string[] }) {
  return (
    <div className={s.side}>
      {mark}
      <span className={s.name}>{name}</span>
      {scorers.length > 0 && <span className={s.scorers}>{scorers.join(" · ")}</span>}
    </div>
  );
}

function Status({ match }: { match: MatchDetail }) {
  if (match.status === "live") return <LiveBadge />;
  if (match.status === "finished") return <span className={s.chip}>Финальный свисток</span>;
  if (match.status === "cancelled") return <span className={s.chip}>Матч отменён</span>;
  return <time className={s.chip} dateTime={match.kickoff}>{formatDate(match.kickoff)}</time>;
}

/** Табло матча: турнир, дата, место; наша команда слева дома и справа в гостях; счёт или VS + отсчёт. */
export function Scoreboard({ match, nav }: { match: MatchDetail; nav?: { href: string; label: string }[] }) {
  const us = <Side mark={<Crest size={96} />} name={SITE_NAME} scorers={match.scorers_us} />;
  const them = <Side mark={<OpponentMark match={match} />} name={match.opponent_name} scorers={match.scorers_them} />;
  const hasScore = match.score_us != null && match.score_them != null && match.status !== "scheduled";
  const [left, right] = match.home ? [match.score_us, match.score_them] : [match.score_them, match.score_us];
  const weekday = formatWeekday(match.kickoff);
  const when = `${weekday.charAt(0).toUpperCase()}${weekday.slice(1)}, ${formatDate(match.kickoff)} · ${formatTime(match.kickoff)}`;
  const head = [match.tournament.short, match.round].filter(Boolean).join(" · ");
  const [homeName, awayName] = match.home ? [SITE_NAME, match.opponent_name] : [match.opponent_name, SITE_NAME];

  return (
    <section className={s.board} aria-labelledby="match-title">
      <div className={`stripes ${s.texture}`} aria-hidden="true" />
      <div className={`container ${s.inner}`}>
        <h1 id="match-title" className="visually-hidden">
          {homeName} — {awayName}{hasScore ? `, ${left}:${right}` : ""}
        </h1>
        <p className={s.meta}>
          {head && <span>{head}</span>}
          <time dateTime={match.kickoff}>{when}</time>
          {match.venue_name && <span>{match.venue_name}</span>}
          <span>{match.home ? "Дома" : "В гостях"}</span>
        </p>
        <div className={s.teams}>
          {match.home ? us : them}
          <div className={s.center}>
            {hasScore ? (
              <p className={s.score}>
                {left}:{right}
                {match.outcome && <span className="visually-hidden"> — {outcomeLabel(match.outcome)}</span>}
              </p>
            ) : (
              <p className={`${s.score} ${s.vs}`}>VS</p>
            )}
            <Status match={match} />
          </div>
          {match.home ? them : us}
        </div>
        {match.status === "scheduled" && <Countdown kickoff={match.kickoff} />}
        {match.status === "live" && match.stream_url && (
          <a className={s.stream} href={match.stream_url} target="_blank" rel="noopener">
            Смотреть трансляцию ↗
          </a>
        )}
        {nav && nav.length > 0 && (
          <nav className={s.anchors} aria-label="Разделы матча">
            {nav.map((n, i) => (
              <a key={n.href} className={i === 0 ? s.anchorActive : s.anchor} href={n.href}>{n.label}</a>
            ))}
          </nav>
        )}
      </div>
    </section>
  );
}
