import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { getClub, getHistory } from "@/lib/api";
import { historyIntro, isWin, placeLabel, sortTrophies, trophySummary, type Trophy } from "@/lib/history";
import { breadcrumbsLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";
import s from "./page.module.css";

export const metadata: Metadata = buildMetadata({
  title: "История",
  description:
    "История Бауман Юнайтед — футбольной команды МГТУ им. Баумана: трофеи Bauman League и IFL, ключевые сезоны с 2016 года.",
  path: "/history",
});

function Cup({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M7 3h10v6a5 5 0 0 1-10 0z" />
      <path d="M7 5H4a3 3 0 0 0 3 4.5M17 5h3a3 3 0 0 1-3 4.5M12 14v4M8 21h8M9 18h6" />
    </svg>
  );
}

function TrophyCard({ trophy }: { trophy: Trophy }) {
  const label = placeLabel(trophy.place);
  return (
    <li className={`${s.trophy} ${trophy.place === 1 ? s.gold : ""}`} data-place={trophy.place}>
      <Cup size={64} />
      <span className={s.place}>{label.place}</span>
      <span className={s.placeNote}>{label.note}</span>
      <h3 className={s.trophyTitle}>{trophy.title}</h3>
      {trophy.season && <span className={s.season}>{trophy.season}</span>}
    </li>
  );
}

export default async function HistoryPage() {
  const [club, history] = await Promise.all([getClub(), getHistory()]);
  const timeline = (history.timeline ?? []).filter((t) => t.year && t.title);
  const trophies = sortTrophies(history.trophies ?? []);
  const legends = (history.legends ?? []).filter((l) => l.name);
  const intro = historyIntro(club, timeline);
  const anchors = [
    timeline.length > 0 && { href: "#timeline", label: "По сезонам" },
    trophies.length > 0 && { href: "#fame", label: "Зал славы" },
    legends.length > 0 && { href: "#legends", label: "Легенды" },
  ].filter((a): a is { href: string; label: string } => Boolean(a));

  return (
    <>
      <JsonLd data={breadcrumbsLd([{ name: "История", path: "/history" }])} />
      <section className={s.top}>
        <div className={`stripes ${s.texture}`} aria-hidden="true" />
        <div className={`container ${s.topInner}`}>
          {club.founded && <span className={s.eyebrow}>С {club.founded} года</span>}
          <h1 className={s.h1}>История клуба</h1>
          {intro && <p className={s.intro}>{intro}</p>}
          {anchors.length > 1 && (
            <nav aria-label="Разделы истории" className={s.anchors}>
              {anchors.map((a, i) => (
                <a key={a.href} href={a.href} className={`${s.anchor} ${i === 0 ? s.anchorPrimary : ""}`}>{a.label}</a>
              ))}
            </nav>
          )}
        </div>
      </section>

      {timeline.length > 0 && (
        <section id="timeline" className={s.timelineSection} aria-labelledby="timeline-title">
          <div className={`container ${s.timelineWrap}`}>
            <h2 id="timeline-title" className="visually-hidden">По сезонам</h2>
            <ol className={s.timeline}>
              {timeline.map((item, i) => {
                const win = isWin(item, history.trophies ?? []);
                return (
                  <li key={i} className={`${s.event} ${item.highlight ? s.highlight : ""}`}
                    data-highlight={item.highlight ? "true" : undefined}>
                    <span className={s.dot} aria-hidden="true" />
                    <span className={s.year}>{item.year}</span>
                    {(item.tag || win) && (
                      <span className={s.tags}>
                        {item.tag && <span className={s.tag}>{item.tag}</span>}
                        {win && <span className={s.win}><Cup size={14} />Победа</span>}
                      </span>
                    )}
                    <h3 className={s.title}>{item.title}</h3>
                    {item.text && <p className={s.text}>{item.text}</p>}
                  </li>
                );
              })}
            </ol>
          </div>
        </section>
      )}

      {trophies.length > 0 && (
        <section id="fame" className="section section--paper" aria-labelledby="fame-title">
          <div className={`container ${s.fame}`}>
            <div className={s.fameHead}>
              <h2 id="fame-title" className={s.fameTitle}>Зал славы</h2>
              <span className={s.fameSummary}>{trophySummary(trophies)}</span>
            </div>
            <ul className={s.trophies}>
              {trophies.map((t, i) => <TrophyCard key={i} trophy={t} />)}
            </ul>
          </div>
        </section>
      )}

      {legends.length > 0 && (
        <section id="legends" className="section" aria-labelledby="legends-title">
          <div className={`container ${s.fame}`}>
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
