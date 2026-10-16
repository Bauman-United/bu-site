import Link from "next/link";
import { telegramUrl } from "@/lib/telegram";
import type { Club } from "@/lib/types";
import s from "./Footer.module.css";
import { NAV } from "./nav";
import { socialLinks } from "./socials";

export function Footer({ club }: { club: Club }) {
  const place = [club.city ?? "Москва", club.university ?? "МГТУ им. Н. Э. Баумана"].join(" · ");
  const { captain_name, email } = club.contacts ?? {};
  const captain_telegram = telegramUrl(club.contacts?.captain_telegram);
  const external = [
    ...socialLinks(club).map(({ label, href }) => ({ label, href })),
    ...(club.socials?.lfl ? [{ label: "Страница в ЛФЛ", href: club.socials.lfl }] : []),
    ...(club.socials?.joinfootball ? [{ label: "Bauman League", href: club.socials.joinfootball }] : []),
  ];
  return (
    <footer className={s.footer}>
      <div className={s.inner}>
        <div className={s.about}>
          <span className={s.name}>{club.name}</span>
          <span>{place}</span>
          {captain_name &&
            (captain_telegram ? (
              <a className={s.link} href={captain_telegram} target="_blank" rel="noopener">
                Капитан: {captain_name}
              </a>
            ) : (
              <span>Капитан: {captain_name}</span>
            ))}
          {email && <a className={s.link} href={`mailto:${email}`}>{email}</a>}
        </div>
        <nav aria-label="Ссылки в подвале" className={s.columns}>
          <div className={s.column}>
            {NAV.slice(0, 3).map((item) => (
              <Link key={item.href} className={s.link} href={item.href}>{item.label}</Link>
            ))}
          </div>
          <div className={s.column}>
            {NAV.slice(3).map((item) => (
              <Link key={item.href} className={s.link} href={item.href}>{item.label}</Link>
            ))}
            <Link className={s.link} href="/join">Хочу в команду</Link>
            <Link className={s.link} href="/partners">Стать партнёром</Link>
          </div>
          {external.length > 0 && (
            <div className={s.column}>
              {external.map((l) => (
                <a key={l.href} className={s.link} href={l.href} target="_blank" rel="noopener">{l.label}</a>
              ))}
            </div>
          )}
        </nav>
      </div>
      <div className={`stripes ${s.stripes}`} aria-hidden="true" />
    </footer>
  );
}
