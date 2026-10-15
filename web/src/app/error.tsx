"use client";

import { ButtonLink } from "@/components/ui/Button";
import b from "@/components/ui/Button.module.css";
import s from "./not-found.module.css";

export default function ErrorPage({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <section className={`section ${s.wrap}`}>
      <div className="container">
        <p className="eyebrow">Ошибка</p>
        <h1 className={s.title}>Что-то пошло не так</h1>
        <p className={s.text}>Данные временно недоступны. Попробуйте обновить страницу через минуту.</p>
        <div className={s.actions}>
          <button type="button" className={`${b.button} ${b.primary}`} onClick={() => retry()}>Обновить</button>
          <ButtonLink href="/" variant="secondary">На главную</ButtonLink>
        </div>
      </div>
    </section>
  );
}
