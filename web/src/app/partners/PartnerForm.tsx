"use client";

import { useActionState } from "react";
import f from "@/components/ui/FormCard.module.css";
import { type PartnerField, initialPartnerState } from "@/lib/partners";
import { submitPartner } from "./actions";

/** `email` — почта клуба: запасной путь, если отправка не удалась. */
export function PartnerForm({ email }: { email: string | null }) {
  const [state, action, pending] = useActionState(submitPartner, initialPartnerState);
  const { values, errors } = state;

  if (state.status === "success") {
    return (
      <section className={f.card} aria-labelledby="partner-card">
        <h2 id="partner-card" className={f.title}>Заявка</h2>
        <p className={f.success} role="status">Заявка отправлена! Мы свяжемся с вами в ближайшее время.</p>
      </section>
    );
  }

  const err = (field: PartnerField, hint?: string) => {
    const ids = [hint, errors[field] ? `partner-${field}-error` : undefined].filter(Boolean).join(" ");
    return {
      "aria-invalid": errors[field] ? true : undefined,
      "aria-describedby": ids || undefined,
    } as const;
  };
  const errorText = (field: PartnerField) =>
    errors[field] ? <p id={`partner-${field}-error`} className={f.error}>{errors[field]}</p> : null;

  return (
    <form className={f.card} action={action} noValidate aria-labelledby="partner-card">
      <h2 id="partner-card" className={f.title}>Заявка</h2>

      {state.status === "error" && (
        <div className={f.alert} role="alert">
          <p>{state.message}</p>
          {email && <a className={f.secondary} href={`mailto:${email}`}>Написать на почту</a>}
        </div>
      )}

      <div className={f.field}>
        <label htmlFor="partner-about" className={f.label}>Расскажите о себе и предложении</label>
        <textarea id="partner-about" name="about" rows={6} className={f.textarea} required
          minLength={10} maxLength={2000} placeholder="Компания или вы лично, чем хотите помочь команде"
          defaultValue={values.about} {...err("about")} />
        {errorText("about")}
      </div>

      <div className={f.field}>
        <label htmlFor="partner-contact" className={f.label}>Контакт для связи</label>
        <input id="partner-contact" name="contact" type="text" className={f.input} required minLength={3}
          maxLength={200} placeholder="+7…, почта или @username" defaultValue={values.contact}
          {...err("contact", "partner-contact-hint")} />
        <p id="partner-contact-hint" className={f.hint}>Телефон, почта или Telegram</p>
        {errorText("contact")}
      </div>

      <div className={f.honeypot} aria-hidden="true">
        <label htmlFor="partner-website">Сайт</label>
        <input id="partner-website" name="website" type="text" tabIndex={-1} autoComplete="off" defaultValue="" />
      </div>

      <button type="submit" className={f.submit} disabled={pending} aria-disabled={pending}>
        {pending ? "Отправляем…" : "Отправить заявку"}
      </button>
    </form>
  );
}
