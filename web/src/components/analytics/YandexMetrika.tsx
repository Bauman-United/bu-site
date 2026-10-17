"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";

type Ym = ((id: number, method: string, ...args: unknown[]) => void) & { a?: unknown[][]; l?: number };

declare global {
  interface Window {
    ym?: Ym;
  }
}

const TAG_URL = "https://mc.yandex.ru/metrika/tag.js";

/**
 * Яндекс Метрика. Первый просмотр счётчик засчитывает сам при init; переходы между
 * страницами в Next идут без перезагрузки, поэтому их отправляем вручную (`hit`).
 * `defer: true` автоматический хит не отключает (проверено: первая страница считалась
 * дважды), так что первый адрес только запоминаем.
 */
export function YandexMetrika({ id }: { id: number }) {
  const pathname = usePathname();
  const search = useSearchParams().toString();
  // Предыдущий адрес: referer для хита (document.referrer при переходах в SPA не меняется)
  const previous = useRef<string | null>(null);

  useEffect(() => {
    if (!window.ym) {
      // Очередь вызовов до загрузки tag.js — как в официальном сниппете.
      const ym: Ym = (...args: unknown[]) => {
        (ym.a = ym.a ?? []).push(args);
      };
      ym.l = Date.now();
      window.ym = ym;
      const script = document.createElement("script");
      script.async = true;
      script.src = `${TAG_URL}?id=${id}`;
      document.head.appendChild(script);
    }
    window.ym(id, "init", {
      ssr: true,
      webvisor: true,
      clickmap: true,
      accurateTrackBounce: true,
      trackLinks: true,
    });
  }, [id]);

  useEffect(() => {
    const url = window.location.origin + pathname + (search ? `?${search}` : "");
    if (previous.current !== null && previous.current !== url) {
      window.ym?.(id, "hit", url, { referer: previous.current });
    }
    previous.current = url;
  }, [id, pathname, search]);

  return (
    <noscript>
      <div>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={`https://mc.yandex.ru/watch/${id}`} style={{ position: "absolute", left: "-9999px" }} alt="" />
      </div>
    </noscript>
  );
}
