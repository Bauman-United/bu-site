import type { MatchSummary } from "@/lib/types";
import { LiveBadge } from "@/components/ui/LiveBadge";
import { Stripes } from "@/components/ui/Stripes";
import s from "./Hero.module.css";

/** Первый экран: фон-заглушка под командное фото, название, подзаголовок; плашка LIVE — если идёт матч. */
export function Hero({ live }: { live: MatchSummary | null }) {
  const streamText = live ? `Смотреть трансляцию: Бауман Юнайтед — ${live.opponent_name}` : "";
  return (
    <>
      <section className={`ph ${s.hero}`}>
        <div className={s.shade} aria-hidden="true" />
        <div className={s.inner}>
          {live && (
            <div className={s.live}>
              <LiveBadge />
              {live.stream_url ? (
                <a className={s.stream} href={live.stream_url} target="_blank" rel="noopener">{streamText}</a>
              ) : (
                <span className={s.stream}>Идёт матч: Бауман Юнайтед — {live.opponent_name}</span>
              )}
            </div>
          )}
          <h1 className={s.title}>Бауман<br />Юнайтед</h1>
          <p className={s.lead}>Футбольная команда МГТУ им. Н. Э. Баумана. Играем в ЛФЛ и Bauman League, 8×8.</p>
        </div>
      </section>
      <Stripes height={12} />
    </>
  );
}
