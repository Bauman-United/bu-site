import s from "./TournamentToggle.module.css";

export type League = "bl" | "lfl" | "ifl" | "urban";

const TABS: { league?: League; label: string }[] = [
  { label: "Общий" },
  { league: "bl", label: "БЛ" },
  { league: "lfl", label: "ЛФЛ" },
];
const IFL_TAB = { league: "ifl" as const, label: "IFL" };
const URBAN_TAB = { league: "urban" as const, label: "Urban Cup" };

/** `?league=` → лига; неизвестные значения — «Общий» (undefined). */
export function parseLeague(value: string | string[] | undefined): League | undefined {
  const v = Array.isArray(value) ? value[0] : value;
  return v === "bl" || v === "lfl" || v === "ifl" || v === "urban" ? v : undefined;
}

/**
 * Вкладки: «Общий», «БЛ» (Бауманская лига с кубками), «ЛФЛ»; «IFL» и «Urban Cup» — только
 * если команда играет там в текущем сезоне (`withIfl`, `withUrban`).
 * Обычные <a>, не next/link: в Next 16.3.8 soft-навигация по тому же маршруту
 * с другим query оставляет устаревший <head> (title, canonical).
 */
export function LeagueTabs({
  pathname,
  selected,
  withIfl = false,
  withUrban = false,
}: {
  pathname: string;
  selected?: League;
  withIfl?: boolean;
  withUrban?: boolean;
}) {
  const tabs = [...TABS, ...(withIfl ? [IFL_TAB] : []), ...(withUrban ? [URBAN_TAB] : [])];
  return (
    <nav className={`${s.group} ${s.row}`} aria-label="Лига">
      {tabs.map(({ league, label }) => {
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
