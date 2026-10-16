import s from "./TournamentToggle.module.css";

export type League = "bl" | "lfl";

const TABS: { league?: League; label: string }[] = [
  { label: "Общий" },
  { league: "bl", label: "БЛ" },
  { league: "lfl", label: "ЛФЛ" },
];

/** `?league=` → лига; неизвестные значения — «Общий» (undefined). */
export function parseLeague(value: string | string[] | undefined): League | undefined {
  const v = Array.isArray(value) ? value[0] : value;
  return v === "bl" || v === "lfl" ? v : undefined;
}

/**
 * Три вкладки: «Общий», «БЛ» (Бауманская лига с кубками), «ЛФЛ».
 * Обычные <a>, не next/link: в Next 16.3.8 soft-навигация по тому же маршруту
 * с другим query оставляет устаревший <head> (title, canonical).
 */
export function LeagueTabs({ pathname, selected }: { pathname: string; selected?: League }) {
  return (
    <nav className={`${s.group} ${s.row}`} aria-label="Лига">
      {TABS.map(({ league, label }) => {
        const active = selected === league;
        return (
          <a
            key={label}
            className={s.button}
            data-active={active || undefined}
            aria-current={active ? "page" : undefined}
            href={league ? `${pathname}?league=${league}` : pathname}
          >
            {label}
          </a>
        );
      })}
    </nav>
  );
}
