import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/JsonLd";
import { Markdown } from "@/components/Markdown";
import { NewsTag } from "@/components/ui/NewsTag";
import { Photo } from "@/components/ui/Photo";
import { Stripes } from "@/components/ui/Stripes";
import { getNewsItem } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { breadcrumbsLd, newsArticleLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";
import { newsDescription, sourceLinkLabel } from "../news-meta";
import s from "./page.module.css";

type Params = Promise<{ slug: string }>;

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const item = await getNewsItem(slug);
  if (!item) return {};
  return buildMetadata({
    title: item.title,
    description: newsDescription(item),
    path: `/news/${item.slug}`,
    type: "article",
    ...(item.cover ? { image: item.cover } : {}),
  });
}

/** Новость — в стилистике блока «Отчёт» со страницы матча, колонка 720px на белом. */
export default async function NewsArticlePage({ params }: { params: Params }) {
  const { slug } = await params;
  const item = await getNewsItem(slug);
  if (!item) notFound();

  return (
    <div className={`section--paper ${s.page}`}>
      <JsonLd data={newsArticleLd(item)} />
      <JsonLd
        data={breadcrumbsLd([
          { name: "Новости", path: "/news" },
          { name: item.title, path: `/news/${item.slug}` },
        ])}
      />
      <div className="container">
        <article className={s.article}>
          <div className={s.meta}>
            <NewsTag tag={item.tag} platform={item.source_platform} />
            <time className={s.date} dateTime={item.date}>{formatDate(item.date)}</time>
          </div>
          <h1 className={s.title}>{item.title}</h1>
          {item.lead && <Markdown className={s.lead} source={item.lead} />}
          {item.cover && (
            <Photo src={item.cover} alt="" ratio="16 / 9" light priority sizes="(max-width: 760px) 100vw, 720px" />
          )}
          {item.body_md && <Markdown source={item.body_md} />}
          {(item.source_url || item.match_slug) && (
            <div className={s.actions}>
              {item.source_url && (
                <a className={s.button} href={item.source_url} target="_blank" rel="noopener">
                  {sourceLinkLabel(item.source_platform)}
                </a>
              )}
              {item.match_slug && (
                <Link className={s.matchLink} href={`/matches/${item.match_slug}`}>К матчу →</Link>
              )}
            </div>
          )}
        </article>
      </div>
      <Stripes height={8} />
    </div>
  );
}
