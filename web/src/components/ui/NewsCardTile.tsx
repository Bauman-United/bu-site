import Link from "next/link";
import type { NewsCard } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { NewsTag } from "./NewsTag";
import { Photo } from "./Photo";
import s from "./NewsCardTile.module.css";

/** Карточка новости: обычная (обложка 4:3, тег, дата, заголовок) или пост из соцсети (рамка, «Открыть оригинал ↗»). */
export function NewsCardTile({ item, onPaper = false }: { item: NewsCard; onPaper?: boolean }) {
  const href = `/news/${item.slug}`;
  const meta = (
    <div className={s.meta}>
      <NewsTag tag={item.tag} platform={item.source_platform} />
      <time className={s.date} dateTime={item.date}>{formatDate(item.date)}</time>
    </div>
  );

  if (item.tag === "social") {
    return (
      <article className={`${s.social} ${onPaper ? s.socialPaper : ""}`}>
        {item.cover && <Photo src={item.cover} alt="" ratio="16 / 9" light={onPaper} sizes="(max-width: 640px) 100vw, 400px" />}
        {meta}
        <h3 className={s.socialTitle}>
          <Link className={s.titleLink} href={href}>{item.title}</Link>
        </h3>
        {item.lead && <p className={s.lead}>{item.lead}</p>}
        {item.source_url && (
          <a className={s.original} href={item.source_url} target="_blank" rel="noopener">
            Открыть оригинал ↗
          </a>
        )}
      </article>
    );
  }

  return (
    <article className={`${s.card} ${onPaper ? s.paper : s.boxed}`}>
      <Photo src={item.cover} alt="" ratio="4 / 3" light sizes="(max-width: 640px) 100vw, 400px" />
      {meta}
      <h3 className={s.title}>
        <Link className={`${s.titleLink} ${s.stretched}`} href={href}>{item.title}</Link>
      </h3>
    </article>
  );
}
