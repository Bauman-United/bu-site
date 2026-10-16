import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { TournamentToggle } from "@/components/tournament/TournamentToggle";
import { EmptyState } from "@/components/ui/EmptyState";
import { StandingsTable } from "@/components/ui/StandingsTable";
import { getStandings } from "@/lib/api";
import { breadcrumbsLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";
import s from "./page.module.css";

export const dynamic = "force-dynamic";

export function generateMetadata(): Metadata {
  return buildMetadata({
    title: "Таблицы",
    description: "Турнирные таблицы Бауман Юнайтед: ЛФЛ и Лига Инженеров Bauman League (МГТУ им. Баумана).",
    path: "/standings",
  });
}

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function single(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function StandingsPage({ searchParams }: { searchParams: SearchParams }) {
  const sp = await searchParams;
  const standings = await getStandings();
  const requested = single(sp.t);
  const selected = standings.find((item) => item.tournament.slug === requested) ?? standings[0];
  return (
    <>
      <JsonLd data={breadcrumbsLd([{ name: "Таблицы", path: "/standings" }])} />
      <section className={s.top}>
        <div className={`container ${s.topInner}`}>
          <h1 className={s.h1}>Таблицы</h1>
          <TournamentToggle
            tournaments={standings.map((item) => item.tournament)}
            selected={selected?.tournament.slug}
            pathname="/standings"
          />
        </div>
      </section>
      <section className={s.body}>
        <div className={`container ${s.list}`}>
          {!selected ? (
            <EmptyState text="Турнирных таблиц пока нет" />
          ) : (
            <section className={s.block} aria-labelledby={`t-${selected.tournament.slug}`}>
              <h2 id={`t-${selected.tournament.slug}`} className={s.h2}>{selected.tournament.name}</h2>
              <StandingsTable standings={selected} />
            </section>
          )}
        </div>
      </section>
    </>
  );
}
