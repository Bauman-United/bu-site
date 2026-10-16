import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/JsonLd";
import { SeasonToggle } from "@/components/team/SeasonToggle";
import { TournamentStatsTable } from "@/components/team/TournamentStatsTable";
import { Stripes } from "@/components/ui/Stripes";
import { getPlayer, getPlayers, getSeasons } from "@/lib/api";
import { positionGroup, positionLabel } from "@/lib/format";
import { breadcrumbsLd, personLd } from "@/lib/jsonld";
import { currentSeason } from "@/lib/seasons";
import { buildMetadata } from "@/lib/seo";
import type { PlayerCard, PlayerStats } from "@/lib/types";
import { playerDescription, playerName, playerTitle } from "./player-meta";
import s from "./page.module.css";

type Params = Promise<{ slug: string }>;

const GROUP_ANCHOR: Record<string, string> = { GK: "gk", DF: "df", MF: "mf", FW: "fw" };
const TABLE_KEYS: (keyof PlayerStats)[] = ["played", "goals", "assists", "yellow", "mvp"];

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const player = await getPlayer(slug);
  if (!player) return {};
  return buildMetadata({
    title: playerTitle(player),
    description: playerDescription(player),
    path: `/team/${player.slug}`,
    type: "profile",
    ownOgImage: true,
  });
}

interface Achievement { title?: unknown; subtitle?: unknown; icon?: unknown }

function AchievementIcon({ icon }: { icon: unknown }) {
  const common = {
    width: 28, height: 28, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
    strokeWidth: 1.8, strokeLinejoin: "round" as const, "aria-hidden": true, className: s.achIcon,
  };
  if (icon === "medal") {
    return (
      <svg {...common}>
        <circle cx="12" cy="9" r="6" />
        <path d="m8.5 14-1.5 7 5-3 5 3-1.5-7" />
      </svg>
    );
  }
  if (icon === "star") {
    return (
      <svg {...common}>
        <path d="m12 3 2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M7 4h10v5a5 5 0 0 1-10 0z" />
      <path d="M7 6H4a3 3 0 0 0 3 4M17 6h3a3 3 0 0 1-3 4M12 14v4M8 20h8" />
    </svg>
  );
}

function siblingLabel(p: PlayerCard | undefined): string | null {
  if (!p) return null;
  return [p.number !== null ? `№ ${p.number}` : null, `${p.first_name} ${p.last_name}`].filter(Boolean).join(" ");
}

export default async function PlayerPage({ params }: { params: Params }) {
  const { slug } = await params;
  const player = await getPlayer(slug);
  if (!player) notFound();
  const [roster, seasons] = await Promise.all([getPlayers(), getSeasons()]);

  const name = playerName(player);
  const position = positionLabel(player.position);
  const group = positionGroup(player.position);
  const anchor = player.position ? GROUP_ANCHOR[player.position] : undefined;
  const groupHref = anchor ? `/team#${anchor}` : "/team";
  const season = currentSeason(seasons);

  const facts = [
    ["В команде с", player.joined],
    ["Рабочая нога", player.foot],
    ["Факультет", player.faculty],
    ["Амплуа", player.role],
  ].filter((f): f is [string, string | number] => f[1] !== null && f[1] !== undefined && f[1] !== "");

  const achievements = (player.achievements as Achievement[]).filter(
    (a): a is Achievement & { title: string } => typeof a.title === "string" && a.title.length > 0,
  );

  const bySlug = new Map(roster.map((p) => [p.slug, p]));
  const prev = player.prev_slug ? { slug: player.prev_slug, label: siblingLabel(bySlug.get(player.prev_slug)) } : null;
  const next = player.next_slug ? { slug: player.next_slug, label: siblingLabel(bySlug.get(player.next_slug)) } : null;

  return (
    <>
      <JsonLd data={personLd(player)} />
      <JsonLd
        data={breadcrumbsLd([
          { name: "Состав", path: "/team" },
          { name, path: `/team/${player.slug}` },
        ])}
      />
      <nav className={`container ${s.crumbs}`} aria-label="Хлебные крошки">
        <Link href="/team">Состав</Link>
        {" / "}
        <Link href={groupHref}>{group}</Link>
        {" / "}
        <span aria-current="page">{name}</span>
      </nav>

      <section className={`container ${s.hero}`}>
        <div className={`ph ${s.photo}`}>
          {player.photo && (
            <Image className={s.img} src={player.photo} alt={name} fill priority sizes="(max-width: 960px) 100vw, 600px" />
          )}
          {player.number !== null && (
            <span className={s.bigNumber} aria-hidden="true">
              {player.number}
            </span>
          )}
        </div>
        <div className={s.info}>
          <div className={s.titles}>
            <span className={s.eyebrow}>
              {[player.number !== null ? `№ ${player.number}` : null, position].filter(Boolean).join(" · ")}
            </span>
            <h1 className={s.h1}>
              <span className={s.line}>{player.first_name}</span> <span className={s.line}>{player.last_name}</span>
            </h1>
            {player.nickname && <span className={s.nick}>«{player.nickname}»</span>}
          </div>
          {facts.length > 0 && (
            <dl className={s.facts}>
              {facts.map(([label, value]) => (
                <div key={label} className={s.fact}>
                  <dt className={s.factLabel}>{label}</dt>
                  <dd className={s.factValue}>{value}</dd>
                </div>
              ))}
            </dl>
          )}
          {player.fact && (
            <blockquote className={s.quote}>
              <span className={s.quoteLabel}>Факт</span>
              <p className={s.quoteText}>{player.fact}</p>
            </blockquote>
          )}
        </div>
      </section>
      <Stripes height={8} />

      <section className={s.stats}>
        <div className={`container ${s.statsInner}`}>
          <SeasonToggle
            title={<h2 className={s.statsH2}>Статистика</h2>}
            seasonLabel={season?.label}
            season={player.season}
            total={player.total}
            teamBest={player.team_best}
          />
          <TournamentStatsTable
            rows={player.tournaments}
            seasons={seasons}
            currentSeason={season?.slug}
            tableClass={s.table}
            captionClass={s.caption}
            totalRowClass={s.totalRow}
          />
          {player.seasons.length > 0 && (
            <div className={s.tableWrap}>
              <table className={s.table}>
                <caption className={s.caption}>По сезонам</caption>
                <thead>
                  <tr>
                    <th scope="col">Сезон</th>
                    <th scope="col">Матчи</th>
                    <th scope="col">Голы</th>
                    <th scope="col">Передачи</th>
                    <th scope="col">ЖК</th>
                    <th scope="col">MVP</th>
                  </tr>
                </thead>
                <tbody>
                  {player.seasons.map((row) => (
                    <tr key={row.season} className={row.season === season?.slug ? s.current : undefined}>
                      <th scope="row">{row.label}</th>
                      {TABLE_KEYS.map((k) => (
                        <td key={k}>{row.stats[k] ?? 0}</td>
                      ))}
                    </tr>
                  ))}
                  <tr className={s.totalRow}>
                    <th scope="row">Всего</th>
                    {TABLE_KEYS.map((k) => (
                      <td key={k}>{player.total[k] ?? 0}</td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {achievements.length > 0 && (
        <section className={`container ${s.achievements}`} aria-labelledby="achievements">
          <h2 id="achievements" className={s.achH2}>Достижения</h2>
          <ul className={s.achList}>
            {achievements.map((a, i) => (
              <li key={i} className={s.ach}>
                <AchievementIcon icon={a.icon} />
                <div className={s.achText}>
                  <span className={s.achTitle}>{a.title}</span>
                  {typeof a.subtitle === "string" && a.subtitle && <span className={s.achSub}>{a.subtitle}</span>}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {(prev || next) && (
        <nav className={s.siblings} aria-label="Другие игроки">
          <div className={`container ${s.siblingsInner}`}>
            {prev ? (
              <Link className={s.sibling} href={`/team/${prev.slug}`}>
                <span className={s.siblingDir}>← Предыдущий</span>
                {prev.label && <span className={s.siblingName}>{prev.label}</span>}
              </Link>
            ) : <span />}
            {next && (
              <Link className={`${s.sibling} ${s.siblingNext}`} href={`/team/${next.slug}`}>
                <span className={s.siblingDir}>Следующий →</span>
                {next.label && <span className={s.siblingName}>{next.label}</span>}
              </Link>
            )}
          </div>
        </nav>
      )}
      <Stripes height={8} />
    </>
  );
}
