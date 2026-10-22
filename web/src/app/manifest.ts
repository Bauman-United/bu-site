import type { MetadataRoute } from "next";
import { SITE_NAME } from "@/lib/seo";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: `${SITE_NAME} — футбольная команда МГТУ им. Н. Э. Баумана`,
    short_name: SITE_NAME,
    description: "Матчи, состав, статистика и новости футбольной команды МГТУ им. Баумана.",
    lang: "ru",
    start_url: "/",
    display: "browser",
    background_color: "#0A0A0A",
    theme_color: "#0A0A0A",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
