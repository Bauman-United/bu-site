import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { Filters } from "@/components/matches/Filters";
import { ResultsTable } from "@/components/matches/ResultsTable";
import { UpcomingList } from "@/components/matches/UpcomingList";
import { EmptyState } from "@/components/ui/EmptyState";
import { getMatches, getSeasons, getTournaments, type MatchQuery } from "@/lib/api";
import { parseMatchFilters } from "@/lib/filters";
import { breadcrumbsLd, sportsEventLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";
import s from "./page.module.css";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

async function resolveFilters(searchParams: SearchParams) {
  const [sp, seasons, allTournaments] = await Promise.all([searchParams, getSeasons(), getTournaments()]);
  const parsed = parseMatchFilters(sp, allTournaments, seasons);
  // Без `season` показываем текущий (первый) сезон; турнир из другого сезона отбрасываем.
  const season = parsed.season ?? seasons[0]?.slug;
  const tournaments = allTournaments.filter((t) => t.season === season);
  const tournament = tournaments.some((t) => t.slug === parsed.tournament) ? parsed.tournament : undefined;
  return { parsed, seasons, tournaments, season, tournament };
}

/** Ближайшие (по возрастанию) и сыгранные (по убыванию) + момент запроса для отсчёта «2д 17ч». */
async function loadMatches(q: MatchQuery) {
  const matches = await getMatches(q);
  const upcoming = matches
    .filter((m) => m.status === "scheduled" || m.status === "live")
    .sort((a, b) => Date.parse(a.kickoff) - Date.parse(b.kickoff));
  const played = matches
    .filter((m) => m.status === "finished")
    .sort((a, b) => Date.parse(b.kickoff) - Date.parse(a.kickoff));
  // Страница динамическая (searchParams), поэтому отсчёт считается на момент запроса.
  return { upcoming, played, nowMs: Date.now() };
}

export async function generateMetadata({ searchParams }: { searchParams: SearchParams }): Promise<Metadata> {
  const { parsed } = await resolveFilters(searchParams);
  return buildMetadata({
    title: "Матчи",
    description:
      "Календарь и результаты матчей Бауман Юнайтед — футбольной команды МГТУ им. Баумана в ЛФЛ и Лиге Инженеров.",
    path: "/matches",
    noindex: parsed.isFiltered,
  });
}

export default async function MatchesPage({ searchParams }: { searchParams: SearchParams }) {
  const { parsed, seasons, tournaments, season, tournament } = await resolveFilters(searchParams);
  const { upcoming, played, nowMs } = await loadMatches({ season, tournament, where: parsed.where });
  const query = { season: parsed.season, t: tournament, where: parsed.where };

  return (
    <>
      <JsonLd data={breadcrumbsLd([{ name: "Матчи", path: "/matches" }])} />
      {upcoming.slice(0, 5).map((m) => (
        <JsonLd key={m.slug} data={sportsEventLd(m)} />
      ))}
      <section className={s.top}>
        <div className={`container ${s.topInner}`}>
          <h1 className={s.h1}>Матчи</h1>
          <Filters query={query} seasons={seasons} tournaments={tournaments} season={season} />
        </div>
      </section>
      {upcoming.length === 0 && played.length === 0 ? (
        <section className={s.upcoming}>
          <div className="container">
            <EmptyState text="Матчей по выбранным фильтрам нет" />
          </div>
        </section>
      ) : (
        <>
          {upcoming.length > 0 && (
            <section className={s.upcoming} aria-labelledby="upcoming">
              <div className={`container ${s.inner}`}>
                <h2 id="upcoming" className={s.h2}>Ближайшие</h2>
                <UpcomingList matches={upcoming} nowMs={nowMs} />
              </div>
            </section>
          )}
          {played.length > 0 && (
            <section className={s.played} aria-labelledby="played">
              <div className={`container ${s.inner}`}>
                <h2 id="played" className={s.h2}>Сыгранные</h2>
                <ResultsTable matches={played} />
              </div>
            </section>
          )}
        </>
      )}
    </>
  );
}
