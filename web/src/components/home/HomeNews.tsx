import type { NewsCard } from "@/lib/types";
import { NewsCardTile } from "@/components/ui/NewsCardTile";
import { SectionHeader } from "@/components/ui/SectionHeader";
import s from "./HomeNews.module.css";

/** Белая секция с 4 последними новостями; на mobile — одна большая и остальные строкой с миниатюрой. */
export function HomeNews({ news }: { news: NewsCard[] }) {
  if (news.length === 0) return null;
  return (
    <section className="section section--paper">
      <div className={`container ${s.wrap}`}>
        <SectionHeader title="Новости" link={{ href: "/news", label: "Все новости" }} />
        <div className={s.grid}>
          {news.slice(0, 4).map((item) => <NewsCardTile key={item.slug} item={item} onPaper />)}
        </div>
      </div>
    </section>
  );
}
