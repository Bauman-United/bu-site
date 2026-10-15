import type { Metadata } from "next";

export const SITE_NAME = "Бауман Юнайтед";
const HOME_TITLE = "Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана";
const SUFFIX = "Бауман Юнайтед | футбольная команда МГТУ им. Баумана";

export function siteUrl(): string {
  return (process.env.BU_SITE_URL ?? "http://localhost:3000").replace(/\/+$/, "");
}

export function isNoindex(): boolean {
  return process.env.BU_NOINDEX !== "0";
}

export function pageTitle(title?: string): string {
  return title ? `${title} — ${SUFFIX}` : HOME_TITLE;
}

export function buildMetadata(opts: {
  title?: string;
  description: string;
  path: string;
  image?: string;
  noindex?: boolean;
  type?: "website" | "article" | "profile";
}): Metadata {
  const url = `${siteUrl()}${opts.path}`;
  const title = pageTitle(opts.title);
  const blocked = isNoindex();
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
      ...(opts.image ? { images: [{ url: opts.image, width: 1200, height: 630 }] } : {}),
    },
    twitter: { card: "summary_large_image", title, description: opts.description },
    robots: blocked
      ? { index: false, follow: false }
      : opts.noindex
        ? { index: false, follow: true }
        : { index: true, follow: true },
  };
}
