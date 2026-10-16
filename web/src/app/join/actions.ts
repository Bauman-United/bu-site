"use server";

import { headers } from "next/headers";
import { apiUrl } from "@/lib/api";
import { type JoinState, networkError, stateFromResponse, valuesFromForm } from "@/lib/join";

/**
 * IP посетителя для rate limit в API. X-Real-IP ставит наш nginx ($remote_addr) — его не подделать;
 * без nginx (dev, e2e) — первый адрес из X-Forwarded-For.
 */
async function clientIp(): Promise<string | null> {
  const h = await headers();
  return h.get("x-real-ip")?.trim() || h.get("x-forwarded-for")?.split(",")[0]?.trim() || null;
}

export async function submitJoin(_prev: JoinState, formData: FormData): Promise<JoinState> {
  const values = valuesFromForm(formData);
  const ip = await clientIp();
  try {
    const res = await fetch(apiUrl("/join"), {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(ip ? { "X-Forwarded-For": ip } : {}) },
      body: JSON.stringify(values),
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
    const body: unknown = await res.json().catch(() => null);
    return stateFromResponse(res.status, body, values);
  } catch {
    return networkError(values);
  }
}
