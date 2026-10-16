/** Заявка «Хочу в команду»: поля, разбор формы и ответа API (общие для формы и server action). */

import {
  type FormSpec, type FormState, type FormValues, emptyValuesOf, failedStateOf, fieldErrorsOf, initialStateOf,
  readForm, stateFromResponseOf,
} from "./forms";

export const POSITIONS = ["Вратарь", "Защитник", "Полузащитник", "Нападающий", "Пока не знаю"] as const;
export const BAUMAN_OPTIONS = ["Да, учусь", "Выпускник", "Нет"] as const;

export const JOIN_FIELDS = ["name", "position", "experience", "bauman", "age", "contact"] as const;
export type JoinField = (typeof JOIN_FIELDS)[number];
export type JoinValues = FormValues<JoinField>;
export type JoinState = FormState<JoinField>;

export const JOIN_FORM: FormSpec<JoinField> = {
  fields: JOIN_FIELDS,
  messages: {
    name: "Укажи фамилию и имя (от 2 до 100 символов)",
    position: "Выбери позицию",
    experience: "Расскажи об опыте: от 10 до 1500 символов",
    bauman: "Выбери вариант",
    age: "Возраст — число от 14 до 70",
    contact: "Оставь контакт: ссылку на соцсеть или ник в Telegram (от 3 до 200 символов)",
  },
  rateLimited: "Слишком много заявок с твоего адреса. Попробуй позже или напиши капитану напрямую.",
  failed: "Не получилось отправить заявку. Напиши капитану напрямую — он ответит.",
};

export const emptyValues: JoinValues = emptyValuesOf(JOIN_FORM);
export const initialJoinState: JoinState = initialStateOf(JOIN_FORM);
export const valuesFromForm = (fd: FormData): JoinValues => readForm(JOIN_FORM, fd);
export const fieldErrors = (detail: unknown) => fieldErrorsOf(JOIN_FORM, detail);
export const stateFromResponse = (status: number, body: unknown, values: JoinValues): JoinState =>
  stateFromResponseOf(JOIN_FORM, status, body, values);
export const networkError = (values: JoinValues): JoinState => failedStateOf(JOIN_FORM, values);
