import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  // Шрифт для OG-картинок (src/lib/og.ts) читается с диска — включаем его в standalone-сборку.
  outputFileTracingIncludes: {
    "/**/opengraph-image*": ["./node_modules/@fontsource/oswald/files/oswald-{cyrillic,latin}-700-normal.woff"],
  },
  images: {
    formats: ["image/avif", "image/webp"],
    // Фото игроков и логотипы команд с источников: join.football (CDN joinsport) и ЛФЛ.
    remotePatterns: [
      { protocol: "https", hostname: "st.joinsport.io" },
      { protocol: "https", hostname: "lfl.ru" },
      { protocol: "https", hostname: "www.lfl.ru" },
    ],
  },
};

export default config;
