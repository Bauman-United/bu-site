import { externalLinks } from "@/components/layout/socials";
import type { Club } from "@/lib/types";
import s from "./ClubLinks.module.css";

/** Ряд ссылок на профили клуба: соцсети, «Страница в ЛФЛ», «Страница в БЛ», «Страница в IFL». Пустой — не рендерится. */
export function ClubLinks({ club, title }: { club: Club; title: string }) {
  const links = externalLinks(club);
  if (links.length === 0) return null;
  return (
    <section className={s.section} aria-labelledby="club-links">
      <div className={`container ${s.inner}`}>
        <h2 id="club-links" className={s.title}>{title}</h2>
        <div className={s.links}>
          {links.map((l) => (
            <a key={l.href} className={s.link} href={l.href} target="_blank" rel="noopener">{l.label}</a>
          ))}
        </div>
      </div>
    </section>
  );
}
