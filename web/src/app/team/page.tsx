import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { EmptyState } from "@/components/ui/EmptyState";
import { PlayerCardTile } from "@/components/ui/PlayerCardTile";
import { Stripes } from "@/components/ui/Stripes";
import { getPlayers, getSeasons } from "@/lib/api";
import { positionGroup } from "@/lib/format";
import { breadcrumbsLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";
import type { PlayerCard } from "@/lib/types";
import s from "./page.module.css";

const GROUPS = [
  { id: "gk", position: "GK" },
  { id: "df", position: "DF" },
  { id: "mf", position: "MF" },
  { id: "fw", position: "FW" },
  { id: "other", position: null },
] as const;

const KNOWN = new Set<string>(["GK", "DF", "MF", "FW"]);

/** Группы состава по позициям (только непустые); игроки без позиции — в конце. */
function groupPlayers(players: PlayerCard[]) {
  return GROUPS.map((g) => ({
    id: g.id,
    title: positionGroup(g.position),
    players: players.filter((p) =>
      g.position ? p.position === g.position : !p.position || !KNOWN.has(p.position),
    ),
  })).filter((g) => g.players.length > 0);
}

export const metadata: Metadata = buildMetadata({
  title: "Состав",
  description:
    "Состав Бауман Юнайтед — футбольной команды МГТУ им. Баумана: вратари, защитники, полузащитники и нападающие.",
  path: "/team",
});

export default async function TeamPage() {
  const [players, seasons] = await Promise.all([getPlayers(), getSeasons()]);
  const groups = groupPlayers(players);
  const season = seasons[0]?.label;

  return (
    <>
      <JsonLd data={breadcrumbsLd([{ name: "Состав", path: "/team" }])} />
      <section className={s.top}>
        <div className={`stripes ${s.texture}`} aria-hidden="true" />
        <div className={`container ${s.topInner}`}>
          <div className={s.titles}>
            {season && <span className={s.season}>Сезон {season}</span>}
            <h1 className={s.h1}>Состав</h1>
          </div>
          {groups.length > 0 && (
            <nav className={s.anchors} aria-label="Позиции">
              {groups.map((g) => (
                <a key={g.id} className={s.anchor} href={`#${g.id}`}>
                  {g.title}
                </a>
              ))}
            </nav>
          )}
        </div>
      </section>
      <div className={`container ${s.body}`}>
        {groups.length === 0 ? (
          <EmptyState text="Состав скоро появится" />
        ) : (
          groups.map((g) => (
            <section key={g.id} id={g.id} className={s.group} aria-labelledby={`${g.id}-title`}>
              <div className={s.groupHead}>
                <h2 id={`${g.id}-title`} className={s.h2}>
                  {g.title}
                </h2>
                <span className={s.count}>
                  <span className="visually-hidden">Игроков: </span>
                  {String(g.players.length).padStart(2, "0")}
                </span>
              </div>
              <div className={s.grid}>
                {g.players.map((p) => (
                  <PlayerCardTile key={p.slug} player={p} />
                ))}
              </div>
            </section>
          ))
        )}
      </div>
      <Stripes height={8} />
    </>
  );
}
