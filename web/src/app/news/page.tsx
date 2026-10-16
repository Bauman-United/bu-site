import type { Metadata } from "next";
import Image from "next/image";
import { JsonLd } from "@/components/JsonLd";
import { EmptyState } from "@/components/ui/EmptyState";
import { NewsCardTile } from "@/components/ui/NewsCardTile";
import { NewsTag } from "@/components/ui/NewsTag";
import { Stripes } from "@/components/ui/Stripes";
import { getNews } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { breadcrumbsLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";
import type { NewsCard } from "@/lib/types";
import { isPageOutOfRange, NEWS_FILTERS, newsHref, parseNewsQuery, stripMarkdown } from "./news-meta";
import s from "./page.module.css";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export async function generateMetadata({ searchParams }: { searchParams: SearchParams }): Promise<Metadata> {
  const { tag, page } = parseNewsQuery(await searchParams);
  // Тот же запрос, что в странице, — fetch мемоизируется в рамках рендера.
  const data = page > 1 ? await getNews({ tag, page }) : undefined;
  return buildMetadata({
    title: "Новости",
    description: "Новости Бауман Юнайтед — футбольной команды МГТУ им. Баумана: отчёты о матчах, жизнь клуба, трансферы.",
    path: newsHref({ page }),
    noindex: Boolean(tag) || (data !== undefined && isPageOutOfRange(page, data.total, data.per_page)),
  });
}

function Featured({ item }: { item: NewsCard }) {
  return (
    <section className={s.featuredSection} aria-label="Главная новость">
      <div className="container">
        <a className={s.featured} href={`/news/${item.slug}`}>
          <div className={`ph ${s.featuredPhoto}`}>
            {item.cover && (
              <Image className={s.featuredImg} src={item.cover} alt="" fill priority sizes="(max-width: 900px) 100vw, 760px" />
            )}
          </div>
          <div className={s.featuredText}>
            <div className={s.featuredMeta}>
              <NewsTag tag={item.tag} platform={item.source_platform} />
              <time className={s.featuredDate} dateTime={item.date}>{formatDate(item.date)}</time>
            </div>
            <h2 className={s.featuredTitle}>{item.title}</h2>
            {item.lead && <p className={s.featuredLead}>{stripMarkdown(item.lead)}</p>}
            <span className={s.featuredMore} aria-hidden="true">Читать →</span>
          </div>
        </a>
      </div>
    </section>
  );
}

/**
 * Фильтр и пагинация — обычные `<a>`, не `next/link`: мягкая навигация Next 16 на тот же маршрут
 * с другим query оставляет в <head> robots/canonical прошлого URL. Полная загрузка — всегда верные.
 */
function TagFilter({ active }: { active?: string }) {
  return (
    <div className={s.filter} role="group" aria-label="Фильтр по тегу">
      {NEWS_FILTERS.map((f) => {
        const current = f.tag === active;
        return (
          <a key={f.label} className={current ? s.tagActive : s.tagLink} href={newsHref({ tag: f.tag })}
            aria-current={current ? "true" : undefined}>
            {f.label}
          </a>
        );
      })}
    </div>
  );
}

function Pagination({ tag, page, pages }: { tag?: string; page: number; pages: number }) {
  const newer = page > 1 ? Math.min(page - 1, Math.max(pages, 1)) : null;
  const older = page < pages ? page + 1 : null;
  if (!newer && !older) return null;
  return (
    <nav className={s.pager} aria-label="Страницы">
      {newer ? <a className={s.pageLink} href={newsHref({ tag, page: newer })}>← Новее</a> : <span />}
      {older && <a className={s.pageLink} href={newsHref({ tag, page: older })}>Старее →</a>}
    </nav>
  );
}

export default async function NewsListPage({ searchParams }: { searchParams: SearchParams }) {
  const { tag, page } = parseNewsQuery(await searchParams);
  const data = await getNews({ tag, page });
  const pages = Math.ceil(data.total / data.per_page);

  // Главная новость — только на первой странице без фильтра: первая с `featured`, иначе самая свежая.
  const featured = !tag && page === 1 ? (data.items.find((n) => n.featured) ?? data.items[0]) : undefined;
  const feed = featured ? data.items.filter((n) => n !== featured) : data.items;

  return (
    <div className={`section--paper ${s.page}`}>
      <JsonLd data={breadcrumbsLd([{ name: "Новости", path: "/news" }])} />
      <section>
        <div className={`container ${s.top}`}>
          <h1 className={s.h1}>Новости</h1>
          <TagFilter active={tag} />
        </div>
      </section>
      {featured && <Featured item={featured} />}
      <section aria-label="Лента новостей">
        <div className={`container ${s.feedInner}`}>
          {data.items.length === 0 && isPageOutOfRange(page, data.total, data.per_page) ? (
            <div className={s.outOfRange}>
              <EmptyState text="На этой странице новостей нет" />
              <a className={s.pageLink} href={newsHref({ tag })}>К свежим новостям</a>
            </div>
          ) : data.items.length === 0 ? (
            <EmptyState text="Новостей пока нет" />
          ) : (
            feed.length > 0 && (
              <div className={s.grid}>
                {feed.map((n) => <NewsCardTile key={n.slug} item={n} onPaper />)}
              </div>
            )
          )}
          <Pagination tag={tag} page={page} pages={pages} />
        </div>
      </section>
      <Stripes height={8} />
    </div>
  );
}
