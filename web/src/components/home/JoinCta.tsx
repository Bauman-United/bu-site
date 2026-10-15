import type { Club } from "@/lib/types";
import { ButtonLink } from "@/components/ui/Button";
import s from "./JoinCta.module.css";

/** «Хочешь играть с нами?» — кнопка в Telegram капитана, без него — на страницу заявки. */
export function JoinCta({ club }: { club: Club }) {
  const telegram = club.contacts?.captain_telegram;
  const training = [club.training?.days, club.training?.time].filter(Boolean).join(", ");
  const text = telegram
    ? "Пиши капитану в Telegram — позовём на тренировку."
    : "Оставь заявку — капитан напишет и позовёт на тренировку.";
  return (
    <section className={`section section--paper ${s.section}`} aria-labelledby="join-cta">
      <div className={`container ${s.wrap}`}>
        <div className={s.text}>
          <h2 id="join-cta" className={s.h2}>Хочешь играть с нами?</h2>
          <p className={s.lead}>
            {training && `Тренировки: ${training}. `}
            {text}
          </p>
        </div>
        <div className={s.action}>
          {telegram ? (
            <ButtonLink href={telegram} onPaper external>Написать в Telegram</ButtonLink>
          ) : (
            <ButtonLink href="/join" onPaper>Хочу в команду</ButtonLink>
          )}
        </div>
      </div>
    </section>
  );
}
