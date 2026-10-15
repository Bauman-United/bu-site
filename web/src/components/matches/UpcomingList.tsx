import Link from "next/link";
import type { MatchSummary } from "@/lib/types";
import { countdownParts, formatDayMonth, formatTime, formatWeekday } from "@/lib/format";
import { LiveBadge } from "@/components/ui/LiveBadge";
import s from "./UpcomingList.module.css";

const US = "Бауман Юнайтед";

function capitalize(v: string) {
  return `${v.charAt(0).toUpperCase()}${v.slice(1)}`;
}

/** «2д 17ч» до начала; меньше суток — «5ч 40м»; null — если матч уже должен был начаться. */
export function timeLeft(kickoff: string, nowMs: number): string | null {
  const c = countdownParts(kickoff, nowMs);
  if (c.started) return null;
  return c.days > 0 ? `${c.days}д ${c.hours}ч` : `${c.hours}ч ${c.minutes}м`;
}

function Row({ match, first, nowMs }: { match: MatchSummary; first: boolean; nowMs: number }) {
  const tag = [match.tournament.short, match.round].filter(Boolean).join(" · ");
  const [home, away] = match.home ? [US, match.opponent_name] : [match.opponent_name, US];
  const place = [match.home ? "Дома" : "В гостях", match.venue_name].filter(Boolean).join(" · ");
  const left = first && match.status !== "live" ? timeLeft(match.kickoff, nowMs) : null;
  return (
    <li>
      <Link className={first ? s.first : s.card} href={`/matches/${match.slug}`}>
        <span className={s.when}>
          <span className={s.date}>{formatDayMonth(match.kickoff)}</span>
          <span className={s.sub}>
            {capitalize(formatWeekday(match.kickoff))} · {formatTime(match.kickoff)}
          </span>
        </span>
        {tag && <span className={s.tag}>{tag}</span>}
        <span className={s.teams}>
          <span>{home}</span>
          <span className={s.vs}>vs</span>
          <span>{away}</span>
        </span>
        <span className={s.sub}>{place}</span>
        {first && match.status === "live" && <LiveBadge />}
        {left && (
          <span className={s.left}>
            <span className="visually-hidden">До начала: </span>
            {left}
          </span>
        )}
      </Link>
    </li>
  );
}

/** «Ближайшие»: строки-карточки, первая (ближайшая) — белая с отсчётом до начала. */
export function UpcomingList({ matches, nowMs }: { matches: MatchSummary[]; nowMs: number }) {
  return (
    <ul className={s.list}>
      {matches.map((m, i) => (
        <Row key={m.slug} match={m} first={i === 0} nowMs={nowMs} />
      ))}
    </ul>
  );
}
