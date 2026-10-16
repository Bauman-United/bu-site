export const NAV = [
  { href: "/matches", label: "Матчи" },
  { href: "/standings", label: "Таблицы" },
  { href: "/team", label: "Команда" },
  { href: "/hall-of-fame", label: "Зал славы" },
  { href: "/news", label: "Новости" },
  { href: "/about", label: "О клубе" },
] as const;

export function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
