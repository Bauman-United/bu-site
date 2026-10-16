import type { MetadataRoute } from "next";
import { isNoindex, siteUrl } from "@/lib/seo";

// BU_NOINDEX/BU_SITE_URL читаются в рантайме: без этого Next пререндерит robots.txt на сборке.
export const dynamic = "force-dynamic";

export default function robots(): MetadataRoute.Robots {
  if (isNoindex()) return { rules: { userAgent: "*", disallow: "/" } };
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/"] },
    sitemap: `${siteUrl()}/sitemap.xml`,
    host: siteUrl(),
  };
}
