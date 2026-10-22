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
    logo: `${siteUrl()}/crest-black.png`,
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

/** Слот матча для endDate: точного времени окончания источники не дают. */
const MATCH_DURATION_MS = 90 * 60 * 1000;

/**
 * Google требует у мероприятия startDate и location, поэтому матч без даты разметки не получает.
 * Турнир — organizer, а не вложенный SportsEvent: тот Google проверяет как отдельное мероприятие.
 */
export function sportsEventLd(m: MatchSummary | MatchDetail) {
  if (!m.kickoff) return null;
  const us = { "@type": "SportsTeam", name: SITE_NAME, url: siteUrl() };
  const them = { "@type": "SportsTeam", name: m.opponent_name };
  const home = m.home ? us : them;
  const away = m.home ? them : us;
  const url = `${siteUrl()}/matches/${m.slug}`;
  return {
    "@context": CTX,
    "@type": "SportsEvent",
    name: `${home.name} — ${away.name}`,
    sport: "Football",
    startDate: m.kickoff,
    endDate: new Date(Date.parse(m.kickoff) + MATCH_DURATION_MS).toISOString(),
    eventStatus: STATUS[m.status] ?? STATUS.scheduled,
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    homeTeam: home,
    awayTeam: away,
    performer: [home, away],
    organizer: { "@type": "SportsOrganization", name: m.tournament.name },
    url,
    image: [`${url}/opengraph-image`],
    location: {
      "@type": "Place",
      name: m.venue_name ?? "Москва",
      address: {
        "@type": "PostalAddress",
        ...(m.venue_address ? { streetAddress: m.venue_address } : {}),
        addressLocality: "Москва",
        addressCountry: "RU",
      },
    },
    description: m.round ? `${m.tournament.name}, ${m.round}` : m.tournament.name,
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
    publisher: { "@type": "Organization", name: SITE_NAME, logo: { "@type": "ImageObject", url: `${siteUrl()}/crest-black.png` } },
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
