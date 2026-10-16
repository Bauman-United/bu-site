import "server-only";

import { headers } from "next/headers";
import { apiUrl } from "./api";
import { type FormSpec, type FormState, type FormValues, failedStateOf, stateFromResponseOf } from "./forms";

/**
 * IP посетителя для rate limit в API. X-Real-IP ставит наш nginx ($remote_addr) — его не подделать;
 * без nginx (dev, e2e) — первый адрес из X-Forwarded-For.
 */
async function clientIp(): Promise<string | null> {
  const h = await headers();
  return h.get("x-real-ip")?.trim() || h.get("x-forwarded-for")?.split(",")[0]?.trim() || null;
}

/** POST значений формы в API (из server action) → состояние формы. */
export async function postForm<F extends string>(
  path: string, spec: FormSpec<F>, values: FormValues<F>,
): Promise<FormState<F>> {
  const ip = await clientIp();
  try {
    const res = await fetch(apiUrl(path), {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(ip ? { "X-Forwarded-For": ip } : {}) },
      body: JSON.stringify(values),
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
    const body: unknown = await res.json().catch(() => null);
    return stateFromResponseOf(spec, res.status, body, values);
  } catch {
    return failedStateOf(spec, values);
  }
}
