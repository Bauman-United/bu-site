import { ButtonLink } from "@/components/ui/Button";
import s from "./not-found.module.css";

export default function NotFound() {
  return (
    <section className={`section ${s.wrap}`}>
      <div className="container">
        <p className="eyebrow">Ошибка</p>
        <h1 className={s.title}>404 — офсайд</h1>
        <p className={s.text}>Такой страницы нет. Возможно, матч перенесли или ссылка устарела.</p>
        <ButtonLink href="/">На главную</ButtonLink>
      </div>
    </section>
  );
}
