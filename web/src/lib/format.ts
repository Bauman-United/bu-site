const TZ = "Europe/Moscow";

export type Outcome = "W" | "D" | "L";
export type Position = "GK" | "DF" | "MF" | "FW";

export function plural(n: number, forms: [string, string, string]): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return forms[0];
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return forms[1];
  return forms[2];
}

function parts(iso: string, opts: Intl.DateTimeFormatOptions): Record<string, string> {
  const out: Record<string, string> = {};
  for (const p of new Intl.DateTimeFormat("ru-RU", { timeZone: TZ, ...opts }).formatToParts(new Date(iso))) {
    out[p.type] = p.value;
  }
  return out;
}

export function formatDate(iso: string): string {
  const p = parts(iso, { day: "numeric", month: "long", year: "numeric" });
  return `${p.day} ${p.month} ${p.year}`;
}

export function formatDateShort(iso: string): string {
  const p = parts(iso, { day: "2-digit", month: "2-digit" });
  return `${p.day}.${p.month}`;
}

export function formatTime(iso: string): string {
  const p = parts(iso, { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  return `${p.hour}:${p.minute}`;
}

export function formatWeekday(iso: string): string {
  return parts(iso, { weekday: "short" }).weekday;
}

export function outcomeLabel(o: Outcome): string {
  return { W: "Победа", D: "Ничья", L: "Поражение" }[o];
}

export function outcomeLetter(o: Outcome): string {
  return { W: "В", D: "Н", L: "П" }[o];
}

export function countdownParts(targetIso: string, nowMs: number) {
  const target = Date.parse(targetIso);
  const diff = target - nowMs;
  const started = diff <= 0;
  const over = nowMs > target + 2 * 3600_000;
  const left = Math.max(0, diff);
  const totalMinutes = Math.floor(left / 60_000);
  return {
    days: Math.floor(totalMinutes / 1440),
    hours: Math.floor((totalMinutes % 1440) / 60),
    minutes: totalMinutes % 60,
    started,
    over,
  };
}

const POSITION: Record<Position, [string, string]> = {
  GK: ["Вратарь", "Вратари"],
  DF: ["Защитник", "Защитники"],
  MF: ["Полузащитник", "Полузащитники"],
  FW: ["Нападающий", "Нападающие"],
};

export function positionLabel(pos: string | null | undefined): string {
  return pos && pos in POSITION ? POSITION[pos as Position][0] : "Игрок";
}

export function positionGroup(pos: string | null | undefined): string {
  return pos && pos in POSITION ? POSITION[pos as Position][1] : "Без позиции";
}
