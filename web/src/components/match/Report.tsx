import Link from "next/link";
import type { MatchDetail, NewsCard } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { Markdown } from "@/components/Markdown";
import { NewsTag } from "@/components/ui/NewsTag";
import s from "./Report.module.css";

type Mvp = NonNullable<MatchDetail["mvp"]>;

function ReportArticle({ report }: { report: NewsCard }) {
  return (
    <article className={s.article}>
      <div className={s.meta}>
        <NewsTag tag={report.tag} platform={report.source_platform} />
        <time className={s.date} dateTime={report.date}>{formatDate(report.date)}</time>
      </div>
      <h2 className={s.title}>{report.title}</h2>
      {report.lead && <Markdown className={s.lead} source={report.lead} />}
      <Link className={s.more} href={`/news/${report.slug}`}>Читать полностью →</Link>
    </article>
  );
}

function MvpBox({ mvp }: { mvp: Mvp }) {
  return (
    <aside className={s.mvp} aria-labelledby="mvp-title">
      <h2 id="mvp-title" className={s.mvpTitle}>Лучший игрок матча</h2>
      <Link className={s.mvpPlayer} href={`/team/${mvp.slug}`}>
        {mvp.number != null && <span className={s.mvpNumber}>№{mvp.number}</span>}
        <span>{mvp.name}</span>
      </Link>
    </aside>
  );
}

/** Белая секция «Отчёт + MVP». Ничего не рендерит, если нет ни отчёта, ни лучшего игрока. */
export function Report({ report, mvp }: { report: NewsCard | null; mvp: Mvp | null }) {
  if (!report && !mvp) return null;
  return (
    <section id="report" className="section--paper" aria-label={report ? "Отчёт о матче" : "Лучший игрок матча"}>
      <div className={`container ${s.inner}`}>
        {report && <ReportArticle report={report} />}
        {mvp && <MvpBox mvp={mvp} />}
      </div>
    </section>
  );
}
