import { isWin, type TimelineItem, type Trophy } from "@/lib/history";
import { Cup } from "./Cup";
import s from "./Timeline.module.css";

/** История по сезонам: ключевые события выделены, победы (1 место в этом сезоне) — с плашкой. */
export function Timeline({ items, trophies }: { items: TimelineItem[]; trophies: Trophy[] }) {
  const timeline = items.filter((t) => t.year && t.title);
  if (timeline.length === 0) return null;
  return (
    <section id="timeline" className={s.section} aria-labelledby="timeline-title">
      <div className={`container ${s.wrap}`}>
        <h2 id="timeline-title" className={s.h2}>История по сезонам</h2>
        <ol className={s.timeline}>
          {timeline.map((item, i) => {
            const win = isWin(item, trophies);
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
  );
}
