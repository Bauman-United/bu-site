import { plural } from "./format";
import type { Club } from "./types";

export interface TimelineItem { year: string; tag?: string; title: string; text?: string | null; highlight?: boolean }
export interface Trophy { place: number; title: string; season?: string | null }
export interface Legend { name: string; years?: string | null; stat?: string | null; note?: string | null; photo?: string | null }
export interface History { timeline: TimelineItem[]; trophies: Trophy[]; legends: Legend[] }

const PLACES: Record<number, { note: string; forms: [string, string, string] }> = {
  1: { note: "Победа", forms: ["победа", "победы", "побед"] },
  2: { note: "Серебро", forms: ["серебро", "серебра", "серебра"] },
  3: { note: "Бронза", forms: ["бронза", "бронзы", "бронз"] },
};

/** Призовые места с названием, по месту (1 — первым), внутри места — порядок из контента. */
export function sortTrophies(list: Trophy[]): Trophy[] {
  return list
    .filter((t) => PLACES[t.place] && t.title?.trim())
    .map((t, i) => ({ t, i }))
    .sort((a, b) => a.t.place - b.t.place || a.i - b.i)
    .map(({ t }) => t);
}

/** «7 побед · 3 серебра · 2 бронзы» — пустые группы пропускаем. */
export function trophySummary(list: Trophy[]): string {
  return [1, 2, 3]
    .map((place) => {
      const n = list.filter((t) => t.place === place).length;
      return n ? `${n} ${plural(n, PLACES[place].forms)}` : "";
    })
    .filter(Boolean)
    .join(" · ");
}

export function placeLabel(place: number): { place: string; note: string } {
  return { place: `${place} место`, note: PLACES[place]?.note ?? "" };
}

/** Выделенное событие — победа, если в этом сезоне в «Зале славы» есть первое место. */
export function isWin(item: TimelineItem, trophies: Trophy[]): boolean {
  return Boolean(item.highlight) && trophies.some((t) => t.place === 1 && t.season === item.year);
}

const LEAGUES: [string[], string][] = [[["BL"], "Bauman League"], [["IFL"], "IFL"], [["ЛФЛ", "LFL"], "ЛФЛ"]];

/** Вводный текст только из данных: год основания, вуз, лиги из тегов таймлайна (+ ЛФЛ по ссылке клуба). */
export function historyIntro(club: Pick<Club, "founded" | "university" | "socials"> & { name: string }, timeline: TimelineItem[]): string {
  const parts: string[] = [];
  if (club.founded) parts.push(`С ${club.founded} года — футбольная команда${club.university ? ` ${club.university}` : ""}.`);
  const tags = new Set(timeline.map((t) => t.tag));
  const leagues = LEAGUES.filter(([codes, name]) =>
    codes.some((c) => tags.has(c)) || (name === "ЛФЛ" && club.socials?.lfl)).map(([, name]) => name);
  if (leagues.length && parts.length) parts.push(`${leagues.join(", ")}.`);
  return parts.join(" ");
}
