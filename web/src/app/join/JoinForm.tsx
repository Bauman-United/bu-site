"use client";

import { useActionState } from "react";
import { BAUMAN_OPTIONS, type JoinField, POSITIONS, initialJoinState } from "@/lib/join";
import { submitJoin } from "./actions";
import s from "./JoinForm.module.css";

interface Props { contact: { href: string; external: boolean } | null }

function TelegramIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d="M22 3 2 11l7 2 2 7 4-5 5 4z" />
      <path d="m9 13 8-6" />
    </svg>
  );
}

function CaptainLink({ contact }: { contact: NonNullable<Props["contact"]> }) {
  return (
    <a className={s.secondary} href={contact.href}
      {...(contact.external ? { target: "_blank", rel: "noopener" } : {})}>
      <TelegramIcon />
      Написать капитану
    </a>
  );
}

export function JoinForm({ contact }: Props) {
  const [state, action, pending] = useActionState(submitJoin, initialJoinState);
  const { values, errors } = state;

  if (state.status === "success") {
    return (
      <section className={s.card} aria-labelledby="join-card">
        <h2 id="join-card" className={s.title}>Заявка</h2>
        <p className={s.success} role="status">Заявка отправлена! Капитан напишет тебе в ближайшее время.</p>
      </section>
    );
  }

  /** Связи поля с ошибкой: aria-invalid + aria-describedby. */
  const err = (field: JoinField, hint?: string) => {
    const ids = [hint, errors[field] ? `join-${field}-error` : undefined].filter(Boolean).join(" ");
    return {
      "aria-invalid": errors[field] ? true : undefined,
      "aria-describedby": ids || undefined,
    } as const;
  };
  const errorText = (field: JoinField) =>
    errors[field] ? <p id={`join-${field}-error`} className={s.error}>{errors[field]}</p> : null;

  return (
    <form className={s.card} action={action} noValidate aria-labelledby="join-card">
      <h2 id="join-card" className={s.title}>Заявка</h2>

      {state.status === "error" && (
        <div className={s.alert} role="alert">
          <p>{state.message}</p>
          {contact && <CaptainLink contact={contact} />}
        </div>
      )}

      <div className={s.field}>
        <label htmlFor="join-name" className={s.label}>Фамилия и имя</label>
        <input id="join-name" name="name" type="text" className={s.input} required minLength={2} maxLength={100}
          autoComplete="name" placeholder="Иванов Иван" defaultValue={values.name} {...err("name")} />
        {errorText("name")}
      </div>

      <div className={s.row}>
        <div className={s.field}>
          <label htmlFor="join-position" className={s.label}>Позиция</label>
          <select id="join-position" name="position" className={s.input} required
            defaultValue={values.position} {...err("position")}>
            <option value="" disabled>Выбери</option>
            {POSITIONS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          {errorText("position")}
        </div>
        <div className={s.field}>
          <label htmlFor="join-age" className={s.label}>Возраст</label>
          <input id="join-age" name="age" type="number" inputMode="numeric" className={s.input} required
            min={14} max={70} placeholder="20" defaultValue={values.age} {...err("age")} />
          {errorText("age")}
        </div>
      </div>

      <div className={s.field}>
        <label htmlFor="join-experience" className={s.label}>Опыт: где и сколько играл</label>
        <textarea id="join-experience" name="experience" rows={4} className={s.textarea} required
          minLength={10} maxLength={1500} placeholder="Секция, школа, любительские лиги, сколько лет"
          defaultValue={values.experience} {...err("experience")} />
        {errorText("experience")}
      </div>

      <fieldset className={s.fieldset} role="radiogroup" aria-labelledby="join-bauman-legend" {...err("bauman")}>
        <legend id="join-bauman-legend" className={s.label}>Учишься в Бауманке?</legend>
        <div className={s.radios}>
          {BAUMAN_OPTIONS.map((opt) => (
            <label key={opt} className={s.radio}>
              <input type="radio" name="bauman" value={opt} required defaultChecked={values.bauman === opt} />
              <span>{opt}</span>
            </label>
          ))}
        </div>
        {errorText("bauman")}
      </fieldset>

      <div className={s.field}>
        <label htmlFor="join-contact" className={s.label}>Контакт для связи</label>
        <input id="join-contact" name="contact" type="text" className={s.input} required minLength={3}
          maxLength={200} placeholder="@username или ссылка на соцсеть" defaultValue={values.contact}
          {...err("contact", "join-contact-hint")} />
        <p id="join-contact-hint" className={s.hint}>Ссылка на соцсеть или ник в Telegram</p>
        {errorText("contact")}
      </div>

      <div className={s.honeypot} aria-hidden="true">
        <label htmlFor="join-website">Сайт</label>
        <input id="join-website" name="website" type="text" tabIndex={-1} autoComplete="off" defaultValue="" />
      </div>

      <button type="submit" className={s.submit} disabled={pending} aria-disabled={pending}>
        {pending ? "Отправляем…" : "Отправить заявку"}
      </button>

      {contact && state.status !== "error" && (
        <>
          <div className={s.or} aria-hidden="true"><span />или<span /></div>
          <CaptainLink contact={contact} />
        </>
      )}
    </form>
  );
}
