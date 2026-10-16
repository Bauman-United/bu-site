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

export function playerDescription(p: PlayerDetail): string {
  const nick = p.nickname ? `, «${p.nickname}»` : "";
  const number = p.number !== null ? `, № ${p.number}` : "";
  const { played = 0, goals = 0, assists = 0 } = p.season;
  return (
    `${playerName(p)}${nick} — ${positionLabel(p.position).toLowerCase()} ${SITE_NAME} (МГТУ им. Баумана)${number}. ` +
    `Сезон: ${played} ${plural(played, ["матч", "матча", "матчей"])}, ${goals} ${plural(goals, ["гол", "гола", "голов"])}, ` +
    `${assists} ${plural(assists, ["передача", "передачи", "передач"])}.`
  );
}
