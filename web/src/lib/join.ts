/** Заявка «Хочу в команду»: поля, разбор формы и ответа API (общие для формы и server action). */

export const POSITIONS = ["Вратарь", "Защитник", "Полузащитник", "Нападающий", "Пока не знаю"] as const;
export const BAUMAN_OPTIONS = ["Да, учусь", "Выпускник", "Нет"] as const;

export const JOIN_FIELDS = ["name", "position", "experience", "bauman", "age", "contact"] as const;
export type JoinField = (typeof JOIN_FIELDS)[number];
export type JoinValues = Record<JoinField | "website", string>;

export const emptyValues: JoinValues = {
  name: "", position: "", experience: "", bauman: "", age: "", contact: "", website: "",
};

const MESSAGES: Record<JoinField, string> = {
  name: "Укажи фамилию и имя (от 2 до 100 символов)",
  position: "Выбери позицию",
  experience: "Расскажи об опыте: от 10 до 1500 символов",
  bauman: "Выбери вариант",
  age: "Возраст — число от 14 до 70",
  contact: "Оставь контакт: ссылку на соцсеть или ник в Telegram (от 3 до 200 символов)",
};

export interface JoinState {
  status: "idle" | "success" | "invalid" | "error";
  values: JoinValues;
  errors: Partial<Record<JoinField, string>>;
  message?: string;
}

export const initialJoinState: JoinState = { status: "idle", values: emptyValues, errors: {} };

export function valuesFromForm(fd: FormData): JoinValues {
  const read = (k: string) => {
    const v = fd.get(k);
    return typeof v === "string" ? v.trim() : "";
  };
  return {
    name: read("name"), position: read("position"), experience: read("experience"),
    bauman: read("bauman"), age: read("age"), contact: read("contact"), website: read("website"),
  };
}

function isField(v: unknown): v is JoinField {
  return typeof v === "string" && (JOIN_FIELDS as readonly string[]).includes(v);
}

/** FastAPI 422 `detail` → русские сообщения по полям формы. */
export function fieldErrors(detail: unknown): Partial<Record<JoinField, string>> {
  const out: Partial<Record<JoinField, string>> = {};
  if (!Array.isArray(detail)) return out;
  for (const err of detail) {
    const loc: unknown = (err as { loc?: unknown })?.loc;
    const field = Array.isArray(loc) && loc.length > 1 ? loc[loc.length - 1] : undefined;
    if (isField(field)) out[field] = MESSAGES[field];
  }
  return out;
}

export function stateFromResponse(status: number, body: unknown, values: JoinValues): JoinState {
  if (status >= 200 && status < 300) return { status: "success", values: emptyValues, errors: {} };
  if (status === 422) {
    const errors = fieldErrors((body as { detail?: unknown } | null)?.detail);
    if (Object.keys(errors).length > 0) return { status: "invalid", values, errors };
  }
  if (status === 429) {
    return {
      status: "error", values, errors: {},
      message: "Слишком много заявок с твоего адреса. Попробуй позже или напиши капитану напрямую.",
    };
  }
  return networkError(values);
}

export function networkError(values: JoinValues): JoinState {
  return {
    status: "error", values, errors: {},
    message: "Не получилось отправить заявку. Напиши капитану напрямую — он ответит.",
  };
}
