import type { components } from "./api-types";

type S = components["schemas"];
export type MatchSummary = S["MatchSummary"];
export type MatchDetail = S["MatchDetail"];
export type EventOut = S["EventOut"];
export type PlayerCard = S["PlayerCard"];
export type PlayerDetail = S["PlayerDetail"];
export type PlayerStats = S["PlayerStats"];
export type NewsCard = S["NewsCard"];
export type NewsDetail = S["NewsDetail"];
export type NewsPage = S["NewsPage"];
export type Tournament = S["TournamentOut"];
export type Standings = S["StandingsOut"];
export type StandingRow = S["StandingRowOut"];
export type Season = S["SeasonOut"];
export type AllTimeRecords = S["AllTimeRecords"];
export type RecordRow = S["RecordRow"];
export type GoalkeeperRecord = S["GoalkeeperRecord"];

export type Outcome = "W" | "D" | "L";

export interface FormItem { slug: string; outcome: Outcome; us: number; them: number }
export interface Totals {
  played?: number; won?: number; drawn?: number; lost?: number;
  gf?: number; ga?: number; clean_sheets?: number;
}
export interface Leader {
  slug: string; name: string; value: number; played: number;
  photo?: string | null; number?: number | null;
}
export interface PlayerOfMonth { player: string; month?: string; stat?: string; slug: string; name: string; photo?: string | null }

export interface LeagueBlock {
  league: "bl" | "lfl";
  title: string;
  last_match: MatchDetail | null;
  standings: Standings | null;
}

export interface Home {
  next_match: MatchSummary | null;
  last_match: MatchDetail | null;
  form: FormItem[];
  totals: Totals;
  standings: Standings | null;
  news: NewsCard[];
  leaders: { goals: Leader | null; assists: Leader | null; player_of_month: PlayerOfMonth | null };
  numbers: { founded?: number | null; matches?: number; goals?: number; trophies?: number };
  live: MatchSummary | null;
  /** Последний результат и мини-таблица по каждой лиге (БЛ, ЛФЛ); лиги без данных не приходят. */
  by_league?: LeagueBlock[];
}

export interface Club {
  name: string;
  name_en?: string;
  founded?: number | null;
  city?: string;
  university?: string;
  format?: string;
  primary_tournament?: string | null;
  socials?: Partial<Record<"telegram" | "vk" | "youtube" | "lfl" | "joinfootball" | "ifl" | "urban", string | null>>;
  contacts?: { captain_name?: string | null; captain_telegram?: string | null; email?: string | null };
  training?: { days?: string | null; time?: string | null; place?: string | null; map_url?: string | null };
  looking_for?: string[];
  about?: string;
}

export interface SitemapItem { path: string; lastmod: string | null }
