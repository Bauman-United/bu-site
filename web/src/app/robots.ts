import type { MetadataRoute } from "next";
import { isNoindex, siteUrl } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  if (isNoindex()) return { rules: { userAgent: "*", disallow: "/" } };
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/"] },
    sitemap: `${siteUrl()}/sitemap.xml`,
    host: siteUrl(),
  };
}
