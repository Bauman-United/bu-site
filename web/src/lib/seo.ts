import type { Metadata } from "next";

export const SITE_NAME = "Бауман Юнайтед";
const HOME_TITLE = "Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана";
const SUFFIX = "Бауман Юнайтед | футбольная команда МГТУ им. Баумана";
/** Матч, игрок, новость: в выдаче видно ~60–70 символов, длинный суффикс съел бы само название. */
const SHORT_SUFFIX = SITE_NAME;

const OG_DIMENSIONS = { width: 1200, height: 630 };

export function siteUrl(): string {
  return (process.env.BU_SITE_URL ?? "http://localhost:3000").replace(/\/+$/, "");
}

export function isNoindex(): boolean {
  return process.env.BU_NOINDEX !== "0";
}

export function pageTitle(title?: string, short = false): string {
  return title ? `${title} — ${short ? SHORT_SUFFIX : SUFFIX}` : HOME_TITLE;
}

/** Абсолютный адрес для og:image и JSON-LD: свои файлы (/media/…) приходят относительными. */
export function absUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : `${siteUrl()}${url.startsWith("/") ? "" : "/"}${url}`;
}

export function buildMetadata(opts: {
  title?: string;
  description: string;
  path: string;
  image?: string;
  /** У сегмента страницы свой `opengraph-image.tsx`: images не задаём, иначе Next его не подставит. */
  ownOgImage?: boolean;
  noindex?: boolean;
  type?: "website" | "article" | "profile";
}): Metadata {
  const url = `${siteUrl()}${opts.path}`;
  // Разделы (/matches) — с полным суффиксом, вложенные страницы (/matches/<slug>) — с коротким.
  const title = pageTitle(opts.title, opts.path.split("/").filter(Boolean).length > 1);
  const blocked = isNoindex();
  // `openGraph` страницы целиком заменяет родительский, поэтому корневой app/opengraph-image сам
  // до страниц не доходит — подставляем его явно как картинку по умолчанию.
  const images = opts.ownOgImage
    ? {}
    : { images: [opts.image ? { url: absUrl(opts.image), ...OG_DIMENSIONS } : { url: `${siteUrl()}/opengraph-image`, ...OG_DIMENSIONS, alt: SITE_NAME }] };
  return {
    title: { absolute: title },
    description: opts.description,
    alternates: { canonical: url },
    openGraph: {
      type: opts.type ?? "website",
      locale: "ru_RU",
      siteName: SITE_NAME,
      url,
      title,
      description: opts.description,
      ...images,
    },
    twitter: { card: "summary_large_image", title, description: opts.description },
    robots: blocked
      ? { index: false, follow: false }
      : opts.noindex
        ? { index: false, follow: true }
        : { index: true, follow: true },
  };
}
