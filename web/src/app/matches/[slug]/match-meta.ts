import type { MatchDetail } from "@/lib/types";
import { formatDate, formatTime, outcomeLabel } from "@/lib/format";
import { SITE_NAME } from "@/lib/seo";

export function isPlayed(m: MatchDetail): boolean {
  return m.status !== "scheduled" && m.score_us != null && m.score_them != null;
}

/** «Бауман Юнайтед 3:1 Энергия» / «Бауман Юнайтед — Мессия, 24 октября 2030». */
export function matchTitle(m: MatchDetail): string {
  return isPlayed(m)
    ? `${SITE_NAME} ${m.score_us}:${m.score_them} ${m.opponent_name}`
    : `${SITE_NAME} — ${m.opponent_name}, ${formatDate(m.kickoff)}`;
}

export function matchDescription(m: MatchDetail): string {
  const where = [m.tournament.name, m.round].filter(Boolean).join(", ");
  if (isPlayed(m)) {
    const result = m.outcome ? `${outcomeLabel(m.outcome)} ${m.score_us}:${m.score_them}.` : `${m.score_us}:${m.score_them}.`;
    const goals = m.scorers_us.length > 0 ? ` Голы: ${m.scorers_us.join(", ")}.` : "";
    return `${where}. ${result}${goals}`;
  }
  const venue = m.venue_name ? `, ${m.venue_name}` : "";
  return `Матч ${where}: ${formatDate(m.kickoff)} ${formatTime(m.kickoff)}${venue}.`;
}
