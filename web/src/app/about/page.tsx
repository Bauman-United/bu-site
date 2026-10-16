import type { Metadata } from "next";
import { ClubLinks } from "@/components/club/ClubLinks";
import { Timeline } from "@/components/history/Timeline";
import { ClubNumbers } from "@/components/home/ClubNumbers";
import { JsonLd } from "@/components/JsonLd";
import { Markdown } from "@/components/Markdown";
import { ButtonLink } from "@/components/ui/Button";
import { getClub, getHistory, getHome } from "@/lib/api";
import { breadcrumbsLd, sportsTeamLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";
import s from "./page.module.css";

export const metadata: Metadata = buildMetadata({
  title: "О клубе",
  description:
    "Бауман Юнайтед — любительская футбольная команда МГТУ им. Н. Э. Баумана (бауманка): история по сезонам, формат 8×8, ЛФЛ и Лига Инженеров Bauman League.",
  path: "/about",
});

export default async function AboutPage() {
  const [club, home, history] = await Promise.all([getClub(), getHome(), getHistory()]);
  const about = club.about?.trim();

  return (
    <>
      <JsonLd data={sportsTeamLd(club)} />
      <JsonLd data={breadcrumbsLd([{ name: "О клубе", path: "/about" }])} />
      <section className={s.top}>
        <div className={`stripes ${s.texture}`} aria-hidden="true" />
        <div className={`container ${s.topInner}`}>
          {club.university && <span className={s.eyebrow}>{club.university}</span>}
          <h1 className={s.h1}>О клубе</h1>
        </div>
      </section>
      {about && (
        <section className={s.body} aria-label="История клуба">
          <div className="container">
            <Markdown source={about} className={s.text} />
          </div>
        </section>
      )}
      <Timeline items={history.timeline ?? []} trophies={history.trophies ?? []} />
      <ClubNumbers numbers={home.numbers} />
      <ClubLinks club={club} title="Команда в сети" />
      <section className="section section--paper" aria-labelledby="about-cta">
        <div className={`container ${s.cta}`}>
          <div className={s.ctaText}>
            <h2 id="about-cta" className={s.ctaTitle}>Хочешь играть с нами?</h2>
            <p className={s.ctaLead}>Тренировки, кого ищем и контакты капитана — на странице для новичков.</p>
          </div>
          <ButtonLink href="/join" onPaper>Хочу в команду</ButtonLink>
        </div>
      </section>
    </>
  );
}
