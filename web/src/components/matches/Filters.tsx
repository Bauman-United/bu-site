import Link from "next/link";
import type { Season, Tournament } from "@/lib/types";
import { filterHref } from "@/lib/filters";
import s from "./Filters.module.css";

type Query = { season?: string; t?: string; where?: string };

function Toggle({ href, active, children }: { href: string; active: boolean; children: React.ReactNode }) {
  return (
    <Link className={active ? s.active : s.toggle} href={href} aria-current={active ? "true" : undefined} scroll={false}>
      {children}
    </Link>
  );
}

function Group({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div className={s.group} role="group" aria-labelledby={id}>
      <span id={id} className={s.label}>{label}</span>
      <div className={s.toggles}>{children}</div>
    </div>
  );
}

/**
 * Фильтры календаря — ссылки на тот же URL с изменённым query (работают без JS).
 * Текущий сезон (первый в списке) — адрес без `season`, чтобы у страницы по умолчанию был один URL.
 */
export function Filters({ query, seasons, tournaments, season }: {
  query: Query; seasons: Season[]; tournaments: Tournament[]; season?: string;
}) {
  const current = seasons[0]?.slug;
  return (
    <div className={s.filters}>
      {seasons.length > 0 && (
        <Group id="filter-season" label="Сезон">
          {seasons.map((x) => (
            <Toggle
              key={x.slug}
              href={filterHref(query, { season: x.slug === current ? undefined : x.slug, t: undefined })}
              active={x.slug === season}
            >
              {x.label}
            </Toggle>
          ))}
        </Group>
      )}
      <Group id="filter-tournament" label="Турнир">
        <Toggle href={filterHref(query, { t: undefined })} active={!query.t}>Все</Toggle>
        {tournaments.map((t) => (
          <Toggle key={t.slug} href={filterHref(query, { t: t.slug })} active={query.t === t.slug}>
            {t.short}
          </Toggle>
        ))}
      </Group>
      <Group id="filter-where" label="Где">
        <Toggle href={filterHref(query, { where: undefined })} active={!query.where}>Все</Toggle>
        <Toggle href={filterHref(query, { where: "home" })} active={query.where === "home"}>Дома</Toggle>
        <Toggle href={filterHref(query, { where: "away" })} active={query.where === "away"}>В гостях</Toggle>
      </Group>
    </div>
  );
}
