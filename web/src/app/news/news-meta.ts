import type { NewsDetail } from "@/lib/types";

/** Фильтр-теги ленты (ключ API → подпись). «Фэнтази» появится вместе с разделом лиги (v3). */
export const NEWS_FILTERS: { tag?: string; label: string }[] = [
  { label: "Все" },
  { tag: "match", label: "Матч" },
  { tag: "club", label: "Клуб" },
  { tag: "transfer", label: "Трансфер" },
  { tag: "social", label: "Из соцсетей" },
];

type SP = Record<string, string | string[] | undefined>;

const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

/** Неизвестный `tag` и некорректный `page` (не целое ≥ 1) игнорируются. */
export function parseNewsQuery(sp: SP): { tag?: string; page: number } {
  const rawTag = first(sp.tag);
  const tag = NEWS_FILTERS.some((f) => f.tag && f.tag === rawTag) ? rawTag : undefined;
  const rawPage = first(sp.page) ?? "";
  const page = /^\d{1,6}$/.test(rawPage) && Number(rawPage) >= 1 ? Number(rawPage) : 1;
  return { tag, page };
}

/** Страница за последней (`?page=99`): пустая лента первой страницы сюда не относится. */
export function isPageOutOfRange(page: number, total: number, perPage: number): boolean {
  return page > Math.max(Math.ceil(total / perPage), 1);
}

/** Адрес ленты: первая страница — без `page`, «Все» — без `tag`. */
export function newsHref({ tag, page = 1 }: { tag?: string; page?: number }): string {
  const params = new URLSearchParams();
  if (tag) params.set("tag", tag);
  if (page > 1) params.set("page", String(page));
  const qs = params.toString();
  return `/news${qs ? `?${qs}` : ""}`;
}

/** Грубое снятие Markdown-разметки для meta description. */
export function stripMarkdown(md: string): string {
  return md
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}(#{1,6}|>|[-*+]|\d+\.)\s+/gm, "")
    .replace(/[*_~`]+/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

const NEWS_CONTEXT = "Новости Бауман Юнайтед — футбольной команды МГТУ им. Баумана.";
/** Короче — слабый сниппет: дополняем контекстом клуба. */
const MIN_DESCRIPTION = 70;

/** `lead`, иначе первые 160 символов текста без разметки; короткий текст дополняется контекстом клуба. */
export function newsDescription(n: Pick<NewsDetail, "lead" | "body_md">): string {
  const raw = stripMarkdown(n.lead || n.body_md);
  const text = raw.length > 160 ? `${raw.slice(0, 159).trimEnd()}…` : raw;
  return text.length < MIN_DESCRIPTION ? `${text} ${NEWS_CONTEXT}`.trim() : text;
}

const SOURCE: Record<string, string> = { telegram: "Telegram", vk: "VK", youtube: "YouTube" };

/** «Оригинал в Telegram ↗» / «Оригинал ↗» для неизвестной платформы. */
export function sourceLinkLabel(platform: string | null): string {
  const name = platform ? SOURCE[platform] : undefined;
  return name ? `Оригинал в ${name} ↗` : "Оригинал ↗";
}
