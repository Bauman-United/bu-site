import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
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

export default async function StandingsPage() {
  const standings = await getStandings();
  return (
    <>
      <JsonLd data={breadcrumbsLd([{ name: "Таблицы", path: "/standings" }])} />
      <section className={s.top}>
        <div className="container">
          <h1 className={s.h1}>Таблицы</h1>
        </div>
      </section>
      <section className={s.body}>
        <div className={`container ${s.list}`}>
          {standings.length === 0 ? (
            <EmptyState text="Турнирных таблиц пока нет" />
          ) : (
            standings.map((st) => (
              <section key={st.tournament.slug} className={s.block} aria-labelledby={`t-${st.tournament.slug}`}>
                <h2 id={`t-${st.tournament.slug}`} className={s.h2}>{st.tournament.name}</h2>
                <StandingsTable standings={st} />
              </section>
            ))
          )}
        </div>
      </section>
    </>
  );
}
