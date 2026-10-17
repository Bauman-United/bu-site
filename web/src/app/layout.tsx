import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import { YandexMetrika } from "@/components/analytics/YandexMetrika";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { getClub } from "@/lib/api";
import { buildMetadata, siteUrl } from "@/lib/seo";
import type { Club } from "@/lib/types";
import { manrope, oswald } from "./fonts";
import "./globals.css";

export const dynamic = "force-dynamic";

export function generateMetadata(): Metadata {
  return {
    metadataBase: new URL(siteUrl()),
    ...buildMetadata({
      description: "Бауман Юнайтед — любительская футбольная команда МГТУ им. Н. Э. Баумана: матчи, состав, статистика и новости.",
      path: "/",
    }),
  };
}

export const viewport: Viewport = { themeColor: "#0A0A0A", width: "device-width", initialScale: 1 };

const FALLBACK_CLUB: Club = { name: "Бауман Юнайтед", university: "МГТУ им. Н. Э. Баумана", city: "Москва" };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const club = await getClub().catch(() => FALLBACK_CLUB);
  // Метрика только там, где задан счётчик (прод): dev и e2e не портят статистику.
  const metrikaId = Number(process.env.BU_METRIKA_ID) || null;
  return (
    <html lang="ru" className={`${oswald.variable} ${manrope.variable}`}>
      <body>
        <a href="#main" className="visually-hidden skip-link">Перейти к содержимому</a>
        <Header club={club} />
        <main id="main">{children}</main>
        <Footer club={club} />
        {metrikaId && (
          <Suspense fallback={null}>
            <YandexMetrika id={metrikaId} />
          </Suspense>
        )}
      </body>
    </html>
  );
}
