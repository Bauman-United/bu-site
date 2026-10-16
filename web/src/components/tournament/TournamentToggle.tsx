import Link from "next/link";
import type { Tournament } from "@/lib/types";
import s from "./TournamentToggle.module.css";

type Option = Pick<Tournament, "slug" | "short">;

export function TournamentToggle({
  tournaments,
  selected,
  pathname,
  includeAll = false,
}: {
  tournaments: Option[];
  selected?: string;
  pathname: string;
  includeAll?: boolean;
}) {
  const options: Array<Option | { slug: ""; short: string }> = includeAll
    ? [{ slug: "", short: "Весь состав" }, ...tournaments]
    : tournaments;

  if (options.length < 2) return null;

  return (
    <nav className={s.group} aria-label="Турнир">
      {options.map((option) => {
        const active = (selected ?? "") === option.slug;
        const href = option.slug ? `${pathname}?t=${encodeURIComponent(option.slug)}` : pathname;
        return (
          <Link
            key={option.slug || "all"}
            className={s.button}
            data-active={active || undefined}
            aria-current={active ? "page" : undefined}
            href={href}
            scroll={false}
          >
            {option.short}
          </Link>
        );
      })}
    </nav>
  );
}
