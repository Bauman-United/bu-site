import type { Club, MatchDetail, MatchSummary, NewsDetail, PlayerDetail } from "./types";
import { SITE_NAME, siteUrl } from "./seo";

const CTX = "https://schema.org";
const UNIVERSITY = "МГТУ им. Н. Э. Баумана";

export function sportsTeamLd(club: Club) {
  const sameAs = Object.values(club.socials ?? {}).filter((v): v is string => typeof v === "string" && /^https?:\/\//i.test(v));
  return {
    "@context": CTX,
    "@type": "SportsTeam",
    name: club.name ?? SITE_NAME,
    alternateName: club.name_en ?? "Bauman United",
    sport: "Football",
    url: siteUrl(),
    logo: `${siteUrl()}/icon.svg`,
    location: { "@type": "Place", address: { "@type": "PostalAddress", addressLocality: club.city ?? "Москва", addressCountry: "RU" } },
    memberOf: { "@type": "CollegeOrUniversity", name: club.university ?? UNIVERSITY },
    ...(club.founded ? { foundingDate: String(club.founded) } : {}),
    sameAs,
  };
}

const STATUS: Record<string, string> = {
  scheduled: "https://schema.org/EventScheduled",
  live: "https://schema.org/EventScheduled",
  finished: "https://schema.org/EventCompleted",
  cancelled: "https://schema.org/EventCancelled",
};

export function sportsEventLd(m: MatchSummary | MatchDetail) {
  const us = { "@type": "SportsTeam", name: SITE_NAME };
  const them = { "@type": "SportsTeam", name: m.opponent_name };
  const home = m.home ? us : them;
  const away = m.home ? them : us;
  return {
    "@context": CTX,
    "@type": "SportsEvent",
    name: `${home.name} — ${away.name}`,
    sport: "Football",
    startDate: m.kickoff,
    eventStatus: STATUS[m.status] ?? STATUS.scheduled,
    homeTeam: home,
    awayTeam: away,
    url: `${siteUrl()}/matches/${m.slug}`,
    location: { "@type": "Place", name: m.venue_name ?? "Москва", address: m.venue_address ?? "Москва" },
    superEvent: { "@type": "SportsEvent", name: m.tournament.name },
    ...(m.round ? { description: `${m.tournament.name}, ${m.round}` } : {}),
  };
}

export function personLd(p: PlayerDetail) {
  return {
    "@context": CTX,
    "@type": "Person",
    name: `${p.first_name} ${p.last_name}`.trim(),
    url: `${siteUrl()}/team/${p.slug}`,
    ...(p.photo ? { image: p.photo } : {}),
    memberOf: { "@type": "SportsTeam", name: SITE_NAME },
    ...(p.nickname ? { alternateName: p.nickname } : {}),
  };
}

export function newsArticleLd(n: NewsDetail) {
  return {
    "@context": CTX,
    "@type": "NewsArticle",
    headline: n.title,
    datePublished: n.date,
    url: `${siteUrl()}/news/${n.slug}`,
    ...(n.cover ? { image: [n.cover] } : {}),
    author: { "@type": "SportsTeam", name: SITE_NAME },
    publisher: { "@type": "Organization", name: SITE_NAME, logo: { "@type": "ImageObject", url: `${siteUrl()}/icon.svg` } },
    ...(n.lead ? { description: n.lead } : {}),
  };
}

export function breadcrumbsLd(items: { name: string; path: string }[]) {
  return {
    "@context": CTX,
    "@type": "BreadcrumbList",
    itemListElement: items.map((it, i) => ({
      "@type": "ListItem", position: i + 1, name: it.name, item: `${siteUrl()}${it.path}`,
    })),
  };
}
