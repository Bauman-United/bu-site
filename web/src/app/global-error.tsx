"use client";

import { manrope, oswald } from "./fonts";
import "./globals.css";
import b from "@/components/ui/Button.module.css";
import s from "./not-found.module.css";

export default function GlobalError({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <html lang="ru" className={`${oswald.variable} ${manrope.variable}`}>
      <body>
        <title>Ошибка — Бауман Юнайтед</title>
        <section className={`section ${s.wrap}`}>
          <div className="container">
            <p className="eyebrow">Ошибка</p>
            <h1 className={s.title}>Что-то пошло не так</h1>
            <p className={s.text}>Данные временно недоступны. Попробуйте обновить страницу через минуту.</p>
            <div className={s.actions}>
              <button type="button" className={`${b.button} ${b.primary}`} onClick={() => retry()}>Обновить</button>
              {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- корневой layout недоступен, нужна полная перезагрузка */}
              <a href="/" className={`${b.button} ${b.secondary}`}>На главную</a>
            </div>
          </div>
        </section>
      </body>
    </html>
  );
}
