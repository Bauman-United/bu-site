import type { PlayerDetail } from "@/lib/types";
import { plural, positionLabel } from "@/lib/format";
import { SITE_NAME } from "@/lib/seo";

export function playerName(p: PlayerDetail): string {
  return `${p.first_name} ${p.last_name}`.trim();
}

/** «Александр Королев — Полузащитник». */
export function playerTitle(p: PlayerDetail): string {
  return `${playerName(p)} — ${positionLabel(p.position)}`;
}

function statLine({ played = 0, goals = 0, assists = 0 }: { played?: number; goals?: number; assists?: number }): string {
  return (
    `${played} ${plural(played, ["матч", "матча", "матчей"])}, ${goals} ${plural(goals, ["гол", "гола", "голов"])}, ` +
    `${assists} ${plural(assists, ["передача", "передачи", "передач"])}`
  );
}

/**
 * Сниппет в выдаче. Карьера в клубе есть у всех, а сезон — только у тех, кто сейчас играет:
 * у бывших игроков «Сезон: 0 матчей» ничего не сообщает.
 */
export function playerDescription(p: PlayerDetail): string {
  const nick = p.nickname ? `, «${p.nickname}»` : "";
  const number = p.number !== null ? `, № ${p.number}` : "";
  const season = p.season.played ? ` В этом сезоне: ${statLine(p.season)}.` : "";
  const career = p.total.played ? ` За клуб: ${statLine(p.total)}.` : "";
  return `${playerName(p)}${nick} — ${positionLabel(p.position).toLowerCase()} ${SITE_NAME} (МГТУ им. Баумана)${number}.${career}${season}`;
}
