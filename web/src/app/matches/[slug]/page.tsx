import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/JsonLd";
import { EventsList } from "@/components/match/EventsList";
import { Report } from "@/components/match/Report";
import { Scoreboard } from "@/components/match/Scoreboard";
import { Stripes } from "@/components/ui/Stripes";
import { getMatch } from "@/lib/api";
import { breadcrumbsLd, sportsEventLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";
import { matchDescription, matchTitle } from "./match-meta";
import s from "./page.module.css";

type Params = Promise<{ slug: string }>;

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const match = await getMatch(slug);
  if (!match) return {};
  return buildMetadata({
    title: matchTitle(match),
    description: matchDescription(match),
    path: `/matches/${match.slug}`,
    type: "article",
    ownOgImage: true,
  });
}

export default async function MatchPage({ params }: { params: Params }) {
  const { slug } = await params;
  const match = await getMatch(slug);
  if (!match) notFound();

  const hasEvents = match.events.length > 0;
  const hasReport = Boolean(match.report || match.mvp);
  const anchors = [
    ...(hasEvents ? [{ href: "#events", label: "События" }] : []),
    ...(hasReport ? [{ href: "#report", label: "Отчёт" }] : []),
  ];

  return (
    <>
      <JsonLd data={sportsEventLd(match)} />
      <JsonLd
        data={breadcrumbsLd([
          { name: "Матчи", path: "/matches" },
          { name: matchTitle(match), path: `/matches/${match.slug}` },
        ])}
      />
      <Scoreboard match={match} nav={anchors} />
      {(hasEvents || match.source_url) && (
        <section className={s.details}>
          <div className={`container ${s.detailsInner}`}>
            {hasEvents && (
              <div id="events" className={s.events}>
                <h2 className={s.h2}>События</h2>
                <EventsList events={match.events} home={match.home} />
              </div>
            )}
            {match.source_url && (
              <a className={s.source} href={match.source_url} target="_blank" rel="noopener">
                Протокол на join.football ↗
              </a>
            )}
          </div>
        </section>
      )}
      <Report report={match.report} mvp={match.mvp} />
      {(match.prev_slug || match.next_slug) && (
        <nav className={s.siblings} aria-label="Соседние матчи">
          <div className={`container ${s.siblingsInner}`}>
            {match.prev_slug ? (
              <Link className={s.prev} href={`/matches/${match.prev_slug}`}>← Предыдущий матч</Link>
            ) : <span />}
            {match.next_slug && (
              <Link className={s.next} href={`/matches/${match.next_slug}`}>Следующий матч →</Link>
            )}
          </div>
        </nav>
      )}
      <Stripes height={8} />
    </>
  );
}
