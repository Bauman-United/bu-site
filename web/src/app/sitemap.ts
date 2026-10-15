import type { MetadataRoute } from "next";
import { getSitemap } from "@/lib/api";
import { siteUrl } from "@/lib/seo";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const items = await getSitemap();
  return items.map((it) => ({
    url: `${siteUrl()}${it.path}`,
    ...(it.lastmod ? { lastModified: it.lastmod } : {}),
    changeFrequency: it.path.startsWith("/matches") || it.path === "/" ? "daily" : "weekly",
    priority: it.path === "/" ? 1 : it.path.split("/").length === 2 ? 0.8 : 0.6,
  }));
}
