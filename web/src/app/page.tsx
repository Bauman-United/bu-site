import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { ClubNumbers } from "@/components/home/ClubNumbers";
import { Hero } from "@/components/home/Hero";
import { HomeNews } from "@/components/home/HomeNews";
import { JoinCta } from "@/components/home/JoinCta";
import { Leaders } from "@/components/home/Leaders";
import { NextMatch } from "@/components/home/NextMatch";
import { ResultFormTable } from "@/components/home/ResultFormTable";
import { getClub, getHome } from "@/lib/api";
import { sportsEventLd, sportsTeamLd, webSiteLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export function generateMetadata(): Metadata {
  return {
    ...buildMetadata({
      description:
        "Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана (бауманка). Матчи ЛФЛ и Лиги Инженеров Bauman League, состав, статистика, новости.",
      path: "/",
    }),
    // URL в buildMetadata уже абсолютные. С metadataBase Next срезает «/» у корня
    // (https://site/ → https://site), а canonical должен совпадать с адресом в sitemap.
    metadataBase: null,
  };
}

export default async function HomePage() {
  const [home, club] = await Promise.all([getHome(), getClub()]);
  return (
    <>
      <JsonLd data={webSiteLd(club)} />
      <JsonLd data={sportsTeamLd(club)} />
      {home.next_match && <JsonLd data={sportsEventLd(home.next_match)} />}
      <Hero live={home.live} />
      {home.next_match && <NextMatch match={home.next_match} />}
      <ResultFormTable last={home.last_match} form={home.form} totals={home.totals} standings={home.standings} byLeague={home.by_league} />
      <HomeNews news={home.news} />
      <Leaders leaders={home.leaders} />
      <ClubNumbers numbers={home.numbers} />
      <JoinCta club={club} />
    </>
  );
}
