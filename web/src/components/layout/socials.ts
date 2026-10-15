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
