import Link from "next/link";
import type { Home } from "@/lib/types";
import { plural } from "@/lib/format";
import { Photo } from "@/components/ui/Photo";
import s from "./Leaders.module.css";

interface LeaderCard {
  key: string;
  role: string;
  name: string;
  slug: string;
  value: string | null;
  caption: string;
  photo?: string | null;
  inverted?: boolean;
}

/** «3 гола» → ["3", "гола"]; без числа — всё в подпись. */
function splitStat(stat?: string): [string | null, string] {
  const m = stat?.trim().match(/^(\d+)\s*(.*)$/);
  return m ? [m[1], m[2]] : [null, stat?.trim() ?? ""];
}

function cards(leaders: Home["leaders"]): LeaderCard[] {
  const out: LeaderCard[] = [];
  const { goals, assists, player_of_month: pom } = leaders;
  if (goals) {
    out.push({ key: "goals", role: "Бомбардир", name: goals.name, slug: goals.slug, value: String(goals.value), caption: plural(goals.value, ["гол", "гола", "голов"]), photo: goals.photo });
  }
  if (assists) {
    out.push({ key: "assists", role: "Ассистент", name: assists.name, slug: assists.slug, value: String(assists.value), caption: plural(assists.value, ["передача", "передачи", "передач"]), photo: assists.photo });
  }
  if (pom) {
    const [value, caption] = splitStat(pom.stat);
    out.push({ key: "pom", role: "Игрок месяца", name: pom.name, slug: pom.slug, value, caption, photo: pom.photo, inverted: true });
  }
  return out;
}

/** Лидеры сезона: бомбардир, ассистент, игрок месяца (инвертирован). На mobile — карусель со scroll-snap. */
export function Leaders({ leaders }: { leaders: Home["leaders"] }) {
  const list = cards(leaders);
  if (list.length === 0) return null;
  return (
    <section className="section" aria-labelledby="leaders">
      <div className={`container ${s.wrap}`}>
        <h2 id="leaders" className={s.h2}>Лидеры сезона</h2>
        <div className={s.grid}>
          {list.map((c) => (
            <article key={c.key} className={`${s.card} ${c.inverted ? s.inverted : ""}`}>
              <Photo src={c.photo} alt="" ratio="3 / 2" light={c.inverted} sizes="(max-width: 640px) 260px, 400px" />
              <div className={s.info}>
                <div className={s.who}>
                  <span className={s.role}>{c.role}</span>
                  <h3 className={s.name}>
                    <Link className={s.link} href={`/team/${c.slug}`}>{c.name}</Link>
                  </h3>
                </div>
                {(c.value || c.caption) && (
                  <div className={s.stat}>
                    {c.value && <span className={s.value}>{c.value}</span>}
                    {c.caption && <span className={s.caption}>{c.caption}</span>}
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
