import type { Club } from "@/lib/types";

export type SocialKey = "telegram" | "vk" | "youtube";

export interface SocialLink { key: SocialKey; label: string; href: string }

const SOCIALS: { key: SocialKey; label: string }[] = [
  { key: "telegram", label: "Telegram" },
  { key: "vk", label: "ВКонтакте" },
  { key: "youtube", label: "YouTube" },
];

/** Соцсети клуба в порядке шапки; пропускает незаданные. */
export function socialLinks(club: Club): SocialLink[] {
  return SOCIALS.flatMap(({ key, label }) => {
    const href = club.socials?.[key];
    return href ? [{ key, label, href }] : [];
  });
}

/** Все внешние профили клуба: соцсети, «Страница в ЛФЛ», «Страница в БЛ» (Бауманская лига), «Страница в IFL»; незаданные пропускаются. */
export function externalLinks(club: Club): { label: string; href: string }[] {
  const leagues = [
    { label: "Страница в ЛФЛ", href: club.socials?.lfl },
    { label: "Страница в БЛ", href: club.socials?.joinfootball },
    { label: "Страница в IFL", href: club.socials?.ifl },
  ].flatMap(({ label, href }) => (href ? [{ label, href }] : []));
  return [...socialLinks(club).map(({ label, href }) => ({ label, href })), ...leagues];
}
