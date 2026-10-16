import type { Metadata } from "next";
import { ClubLinks } from "@/components/club/ClubLinks";
import { JsonLd } from "@/components/JsonLd";
import { Stripes } from "@/components/ui/Stripes";
import { getClub } from "@/lib/api";
import { breadcrumbsLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";
import type { Club } from "@/lib/types";
import s from "./page.module.css";

export const metadata: Metadata = buildMetadata({
  title: "Хочу в команду",
  description:
    "Как попасть в футбольную команду МГТУ им. Баумана: тренировки, кого ищем, контакты капитана Бауман Юнайтед.",
  path: "/join",
});

interface Fact { term: string; value: string; note?: string; href?: string }

/** «@handle» из ссылки вида https://t.me/handle. */
function telegramHandle(url: string): string | null {
  const m = /t\.me\/([A-Za-z0-9_]+)/.exec(url);
  return m ? `@${m[1]}` : null;
}

/** Ячейки сетки «Тренировки / Матчи / Капитан / Почта» — только из заданных полей. */
function facts(club: Club): Fact[] {
  const out: Fact[] = [];
  const t = club.training ?? {};
  const when = [t.days, t.time].filter(Boolean).join(", ");
  if (when) out.push({ term: "Тренировки", value: when, note: t.place ?? undefined });
  else if (t.place) out.push({ term: "Тренировки", value: t.place });
  if (club.format) out.push({ term: "Матчи", value: club.format.replace(/x/i, "×"), note: "ЛФЛ и Bauman League" });
  const { captain_name, captain_telegram, email } = club.contacts ?? {};
  const handle = captain_telegram ? telegramHandle(captain_telegram) : null;
  if (captain_name) out.push({ term: "Капитан", value: captain_name, note: handle ?? undefined });
  else if (handle) out.push({ term: "Капитан", value: handle });
  if (email) out.push({ term: "Почта", value: email, note: "для партнёров и СМИ", href: `mailto:${email}` });
  return out;
}

/** Куда ведёт «Написать капитану»: Telegram капитана → Telegram клуба → почта. */
function captainContact(club: Club): { href: string; external: boolean } | null {
  const tg = club.contacts?.captain_telegram || club.socials?.telegram;
  if (tg) return { href: tg, external: true };
  if (club.contacts?.email) return { href: `mailto:${club.contacts.email}`, external: false };
  return null;
}

export default async function JoinPage() {
  const club = await getClub();
  const lookingFor = club.looking_for ?? [];
  const grid = facts(club);
  const mapUrl = club.training?.map_url;
  const contact = captainContact(club);

  return (
    <>
      <JsonLd data={breadcrumbsLd([{ name: "Хочу в команду", path: "/join" }])} />
      <section className={`container ${s.main}`}>
        <div className={s.info}>
          <div className={s.intro}>
            <h1 className={s.h1}>Хочешь{" "}<br />в команду?</h1>
            <p className={s.lead}>
              Мы играем 8 на 8 в ЛФЛ и в Лиге Инженеров Bauman League. Берём студентов и выпускников Бауманки,
              уровень — от любителя до КМС. Главное — приходить и не сливать игры.
            </p>
          </div>

          {lookingFor.length > 0 && (
            <div className={s.looking}>
              <h2 className={s.label}>Сейчас ищем</h2>
              <ul className={s.badges}>
                {lookingFor.map((item) => (
                  <li key={item} className={s.badge}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {grid.length > 0 && (
            <dl className={s.facts}>
              {grid.map((f) => (
                <div key={f.term} className={s.fact}>
                  <dt className={s.term}>{f.term}</dt>
                  <dd className={s.value}>{f.href ? <a href={f.href}>{f.value}</a> : f.value}</dd>
                  {f.note && <dd className={s.note}>{f.note}</dd>}
                </div>
              ))}
            </dl>
          )}

          {mapUrl && (
            <div className={s.map} role="img" aria-label="Карта: место тренировок">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
                <path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z" />
              </svg>
              <a className={s.mapLink} href={mapUrl} target="_blank" rel="noopener">Открыть в Яндекс Картах</a>
            </div>
          )}
        </div>

        {contact && (
          <aside className={s.card} aria-labelledby="join-card">
            <h2 id="join-card" className={s.cardTitle}>Заявка</h2>
            <p className={s.cardText}>
              {contact.external ? "Напиши капитану в Telegram" : "Напиши капитану на почту"} — расскажи, на какой позиции
              играешь, с какого ты факультета и где играл раньше.
            </p>
            <a
              className={s.cardButton}
              href={contact.href}
              {...(contact.external ? { target: "_blank", rel: "noopener" } : {})}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                strokeLinejoin="round" aria-hidden="true" focusable="false">
                <path d="M22 3 2 11l7 2 2 7 4-5 5 4z" />
                <path d="m9 13 8-6" />
              </svg>
              Написать капитану
            </a>
          </aside>
        )}
      </section>
      <ClubLinks club={club} title="Следи за командой" />
      <Stripes height={8} />
    </>
  );
}
