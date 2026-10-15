import Link from "next/link";
import type { PlayerCard } from "@/lib/types";
import { plural, positionLabel } from "@/lib/format";
import { Photo } from "./Photo";
import s from "./PlayerCardTile.module.css";

/** Карточка игрока: фото 4:5, номер-водяной знак; на ховер/фокус — статистика сезона и «Профиль →». */
export function PlayerCardTile({ player }: { player: PlayerCard }) {
  const name = `${player.first_name} ${player.last_name}`;
  const sub = [positionLabel(player.position), player.nickname && `«${player.nickname}»`].filter(Boolean).join(" · ");
  const st = player.season;
  const stats: [number, string][] = [
    [st.played ?? 0, plural(st.played ?? 0, ["матч", "матча", "матчей"])],
    [st.goals ?? 0, plural(st.goals ?? 0, ["гол", "гола", "голов"])],
    [st.assists ?? 0, plural(st.assists ?? 0, ["передача", "передачи", "передач"])],
    [st.yellow ?? 0, "ЖК"],
  ];
  return (
    <Link className={s.card} href={`/team/${player.slug}`}>
      <div className={s.media}>
        <Photo src={player.photo} alt={name} ratio="4 / 5" sizes="(max-width: 640px) 50vw, 300px" />
        {player.number !== null && (
          <span className={s.watermark} aria-hidden="true">
            {player.number}
          </span>
        )}
        <div className={s.panel} aria-hidden="true">
          <span className={s.panelLabel}>Сезон</span>
          <div className={s.stats}>
            {stats.map(([v, label]) => (
              <div key={label} className={s.stat}>
                <span className={s.statValue}>{v}</span>
                <span className={s.statLabel}>{label}</span>
              </div>
            ))}
          </div>
          <span className={s.profile}>Профиль →</span>
        </div>
      </div>
      <div className={s.info}>
        <div className={s.names}>
          <span className={s.name}>
            {name}
            {player.is_captain && (
              <abbr className={s.captain} title="Капитан" aria-label="капитан">
                C
              </abbr>
            )}
          </span>
          <span className={s.sub}>{sub}</span>
        </div>
        {player.number !== null && (
          <span className={s.number}>
            <span className="visually-hidden">Номер </span>
            {player.number}
          </span>
        )}
      </div>
    </Link>
  );
}
