/** Заявка «Стать партнёром»: поля, разбор формы и ответа API (общие для формы и server action). */

import {
  type FormSpec, type FormState, type FormValues, emptyValuesOf, fieldErrorsOf, initialStateOf, readForm,
  stateFromResponseOf,
} from "./forms";

export const PARTNER_FIELDS = ["about", "contact"] as const;
export type PartnerField = (typeof PARTNER_FIELDS)[number];
export type PartnerValues = FormValues<PartnerField>;
export type PartnerState = FormState<PartnerField>;

export const PARTNER_FORM: FormSpec<PartnerField> = {
  fields: PARTNER_FIELDS,
  messages: {
    about: "Расскажите о себе и предложении: от 10 до 2000 символов",
    contact: "Оставьте контакт: телефон, почту или Telegram (от 3 до 200 символов)",
  },
  rateLimited: "Слишком много заявок с вашего адреса. Попробуйте позже или напишите нам напрямую.",
  failed: "Не получилось отправить заявку. Попробуйте позже или напишите нам напрямую.",
};

export const emptyPartnerValues: PartnerValues = emptyValuesOf(PARTNER_FORM);
export const initialPartnerState: PartnerState = initialStateOf(PARTNER_FORM);
export const partnerValuesFromForm = (fd: FormData): PartnerValues => readForm(PARTNER_FORM, fd);
export const partnerFieldErrors = (detail: unknown) => fieldErrorsOf(PARTNER_FORM, detail);
export const partnerStateFromResponse = (status: number, body: unknown, values: PartnerValues): PartnerState =>
  stateFromResponseOf(PARTNER_FORM, status, body, values);
