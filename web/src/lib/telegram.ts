const HANDLE = /^@?([A-Za-z0-9_]+)$/;
const T_ME = /^(?:https?:\/\/)?t\.me\/(.+)$/i;

/** Ссылка на Telegram из значения контента: «@handle», «handle», «t.me/handle» или полный URL. Пустое — null. */
export function telegramUrl(value: string | null | undefined): string | null {
  const v = value?.trim();
  if (!v) return null;
  const handle = HANDLE.exec(v);
  if (handle) return `https://t.me/${handle[1]}`;
  const tme = T_ME.exec(v);
  if (tme) return `https://t.me/${tme[1]}`;
  return /^https?:\/\//i.test(v) ? v : null;
}

/** «@handle» для подписи; для инвайт-ссылок и прочего — null. */
export function telegramHandle(value: string | null | undefined): string | null {
  const url = telegramUrl(value);
  const m = url ? /^https:\/\/t\.me\/([A-Za-z0-9_]+)\/?$/.exec(url) : null;
  return m ? `@${m[1]}` : null;
}
