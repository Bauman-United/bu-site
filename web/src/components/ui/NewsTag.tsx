import s from "./NewsTag.module.css";

const TAGS: Record<string, string> = { match: "Матч", club: "Клуб", transfer: "Трансфер", social: "Из соцсетей" };
const PLATFORMS: Record<string, string> = { telegram: "Telegram", vk: "ВКонтакте", youtube: "YouTube" };

export function newsTagLabel(tag: string, platform?: string | null): string {
  if (tag === "social" && platform && PLATFORMS[platform]) return PLATFORMS[platform];
  return TAGS[tag] ?? tag;
}

/** Тег новости: заливка для рубрик, рамка — для постов из соцсетей. */
export function NewsTag({ tag, platform }: { tag: string; platform?: string | null }) {
  return <span className={`${s.tag} ${tag === "social" ? s.social : s.solid}`}>{newsTagLabel(tag, platform)}</span>;
}
