import type { Metadata } from "next";
import { Records } from "@/components/history/Records";
import { Trophies } from "@/components/history/Trophies";
import { JsonLd } from "@/components/JsonLd";
import { getAllTimeRecords, getClub, getHistory } from "@/lib/api";
import { historyIntro, sortTrophies, trophySummary } from "@/lib/history";
import { breadcrumbsLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";
import s from "./page.module.css";

const BASE_DESCRIPTION = "Зал славы Бауман Юнайтед — футбольной команды МГТУ им. Баумана";

/** Описание из данных: счётчик трофеев и лучший бомбардир за всё время, если они есть. */
export async function generateMetadata(): Promise<Metadata> {
  const [history, records] = await Promise.all([getHistory(), getAllTimeRecords()]);
  const summary = trophySummary(sortTrophies(history.trophies ?? []));
  const scorer = records.goals[0];
  const parts = [
    summary ? `${BASE_DESCRIPTION}: ${summary}.` : `${BASE_DESCRIPTION}: трофеи и рекорды клуба.`,
    scorer ? `Лучший бомбардир за всё время — ${scorer.name} (${scorer.value}).` : "",
    "Рекордсмены по голам, передачам и матчам во всех турнирах с основания.",
  ];
  return buildMetadata({ title: "Зал славы", description: parts.filter(Boolean).join(" "), path: "/hall-of-fame" });
}

export default async function HallOfFamePage() {
  const [club, history, records] = await Promise.all([getClub(), getHistory(), getAllTimeRecords()]);
  const trophies = history.trophies ?? [];
  const legends = (history.legends ?? []).filter((l) => l.name);
  const intro = historyIntro(club, (history.timeline ?? []).filter((t) => t.year && t.title));
  const hasTrophies = sortTrophies(trophies).length > 0;
  const hasRecords = records.goals.length + records.assists.length + records.played.length
    + records.goal_contributions.length + records.goalkeepers.length > 0;
  const anchors = [
    hasTrophies && { href: "#trophies", label: "Трофеи" },
    hasRecords && { href: "#records", label: "Рекордсмены" },
    legends.length > 0 && { href: "#legends", label: "Легенды" },
  ].filter((a): a is { href: string; label: string } => Boolean(a));

  return (
    <>
      <JsonLd data={breadcrumbsLd([{ name: "Зал славы", path: "/hall-of-fame" }])} />
      <section className={s.top}>
        <div className={`stripes ${s.texture}`} aria-hidden="true" />
        <div className={`container ${s.topInner}`}>
          {club.founded && <span className={s.eyebrow}>С {club.founded} года</span>}
          <h1 className={s.h1}>Зал славы</h1>
          {intro && <p className={s.intro}>{intro}</p>}
          {anchors.length > 1 && (
            <nav aria-label="Разделы зала славы" className={s.anchors}>
              {anchors.map((a, i) => (
                <a key={a.href} href={a.href} className={`${s.anchor} ${i === 0 ? s.anchorPrimary : ""}`}>{a.label}</a>
              ))}
            </nav>
          )}
        </div>
      </section>

      <Trophies trophies={trophies} />
      <Records records={records} />

      {!hasTrophies && !hasRecords && (
        <section className="section">
          <p className={`container ${s.empty}`}>Трофеи и рекорды появятся, когда сыграем первые турниры.</p>
        </section>
      )}

      {legends.length > 0 && (
        <section id="legends" className="section" aria-labelledby="legends-title">
          <div className={`container ${s.legendsWrap}`}>
            <h2 id="legends-title" className={s.legendsTitle}>Легенды и выпускники</h2>
            <ul className={s.legends}>
              {legends.map((l, i) => (
                <li key={i} className={s.legend}>
                  <span className={s.legendName}>{l.name}</span>
                  {l.years && <span className={s.legendMeta}>{l.years}</span>}
                  {l.stat && <span className={s.legendMeta}>{l.stat}</span>}
                  {l.note && <p className={s.legendNote}>{l.note}</p>}
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </>
  );
}
