/** Общая логика публичных форм (заявки в команду и партнёрам): разбор FormData и ответа API. */

export interface FormSpec<F extends string> {
  fields: readonly F[];
  /** Сообщения об ошибке по полям (на 422 от API). */
  messages: Record<F, string>;
  rateLimited: string;
  failed: string;
}

/** Значения полей + скрытое поле-ловушка для ботов `website`. */
export type FormValues<F extends string> = Record<F | "website", string>;

export interface FormState<F extends string> {
  status: "idle" | "success" | "invalid" | "error";
  values: FormValues<F>;
  errors: Partial<Record<F, string>>;
  message?: string;
}

export function emptyValuesOf<F extends string>(spec: FormSpec<F>): FormValues<F> {
  return Object.fromEntries([...spec.fields, "website"].map((k) => [k, ""])) as FormValues<F>;
}

export function initialStateOf<F extends string>(spec: FormSpec<F>): FormState<F> {
  return { status: "idle", values: emptyValuesOf(spec), errors: {} };
}

export function readForm<F extends string>(spec: FormSpec<F>, fd: FormData): FormValues<F> {
  const read = (k: string) => {
    const v = fd.get(k);
    return typeof v === "string" ? v.trim() : "";
  };
  return Object.fromEntries([...spec.fields, "website"].map((k) => [k, read(k)])) as FormValues<F>;
}

/** FastAPI 422 `detail` → сообщения по полям формы. */
export function fieldErrorsOf<F extends string>(spec: FormSpec<F>, detail: unknown): Partial<Record<F, string>> {
  const out: Partial<Record<F, string>> = {};
  if (!Array.isArray(detail)) return out;
  const isField = (v: unknown): v is F => typeof v === "string" && (spec.fields as readonly string[]).includes(v);
  for (const err of detail) {
    const loc: unknown = (err as { loc?: unknown })?.loc;
    const field = Array.isArray(loc) && loc.length > 1 ? loc[loc.length - 1] : undefined;
    if (isField(field)) out[field] = spec.messages[field];
  }
  return out;
}

export function failedStateOf<F extends string>(spec: FormSpec<F>, values: FormValues<F>): FormState<F> {
  return { status: "error", values, errors: {}, message: spec.failed };
}

export function stateFromResponseOf<F extends string>(
  spec: FormSpec<F>, status: number, body: unknown, values: FormValues<F>,
): FormState<F> {
  if (status >= 200 && status < 300) return { status: "success", values: emptyValuesOf(spec), errors: {} };
  if (status === 422) {
    const errors = fieldErrorsOf(spec, (body as { detail?: unknown } | null)?.detail);
    if (Object.keys(errors).length > 0) return { status: "invalid", values, errors };
  }
  if (status === 429) return { status: "error", values, errors: {}, message: spec.rateLimited };
  return failedStateOf(spec, values);
}
