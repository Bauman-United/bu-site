import Link from "next/link";
import type { FormItem, LeagueBlock, MatchDetail, Standings, Totals } from "@/lib/types";
import { outcomeLabel, plural } from "@/lib/format";
import { FormBadge } from "@/components/ui/FormBadge";
import { StandingsTable } from "@/components/ui/StandingsTable";
import s from "./ResultFormTable.module.css";

const US = "Бауман Юнайтед";

function LastResult({ match, sub = false }: { match: MatchDetail; sub?: boolean }) {
  const head = [match.tournament.short, match.round].filter(Boolean).join(", ");
  const Label = sub ? "h3" : "h2";
  const hasScore = match.score_us !== null && match.score_them !== null;
  const [left, right] = match.home ? [US, match.opponent_name] : [match.opponent_name, US];
  const [l, r] = match.home ? [match.score_us, match.score_them] : [match.score_them, match.score_us];
  return (
    <article className={s.card}>
      <Label className={s.label}>Последний результат{head && ` · ${head}`}</Label>
      <div className={s.teams}>
        <span className={s.team}>{left}</span>
        <span className={s.score}>
          <span aria-hidden="true">{hasScore ? `${l}:${r}` : "–:–"}</span>
          {hasScore && (
            <span className="visually-hidden">
              {match.outcome ? `${outcomeLabel(match.outcome)} ` : ""}
              {match.score_us}:{match.score_them}
            </span>
          )}
        </span>
        <span className={`${s.team} ${s.right}`}>{right}</span>
      </div>
      {match.scorers_us.length > 0 && (
        <ul className={s.scorers} aria-label="Голы">
          {match.scorers_us.map((line) => <li key={line}>{line}</li>)}
        </ul>
      )}
      <Link className={s.more} href={`/matches/${match.slug}`}>
        Отчёт о матче →<span className="visually-hidden">: {match.opponent_name}</span>
      </Link>
    </article>
  );
}

function Form({ form, totals, mergeTable, wide = false }: {
  form: FormItem[]; totals: Totals; mergeTable: boolean; wide?: boolean;
}) {
  const stats: [number, string][] = totals.played
    ? [
        [totals.gf ?? 0, plural(totals.gf ?? 0, ["гол забит", "гола забито", "голов забито"])],
        [totals.ga ?? 0, "пропущено"],
        [totals.clean_sheets ?? 0, plural(totals.clean_sheets ?? 0, ["сухой матч", "сухих матча", "сухих матчей"])],
      ]
    : [];
  return (
    <article className={`${s.card} ${mergeTable ? s.withTable : ""} ${wide ? s.wide : ""}`}>
      <h2 className={s.label}>
        Форма{form.length > 0 && ` · ${form.length} ${plural(form.length, ["матч", "матча", "матчей"])}`}
      </h2>
      {form.length > 0 && (
        <div className={s.form}>
          {form.map((f) => <FormBadge key={f.slug} outcome={f.outcome} us={f.us} them={f.them} />)}
        </div>
      )}
      {stats.length > 0 && (
        <dl className={s.totals}>
          {stats.map(([v, label]) => (
            <div key={label} className={s.total}>
              <dt className={s.totalLabel}>{label}</dt>
              <dd className={s.totalValue}>{v}</dd>
            </div>
          ))}
        </dl>
      )}
    </article>
  );
}

function MiniTable({ standings, sub = false }: { standings: Standings; sub?: boolean }) {
  const Label = sub ? "h3" : "h2";
  return (
    <article className={`${s.card} ${s.table}`}>
      <Label className={s.label}>Таблица · {standings.tournament.short}</Label>
      <StandingsTable standings={standings} compact mobileRows={3} meta={false} />
      <Link className={s.more} href={`/standings?t=${encodeURIComponent(standings.tournament.slug)}`}>
        Полная таблица →
      </Link>
    </article>
  );
}

/** Блок лиги: заголовок, последний результат и мини-таблица (5 строк вокруг нас). */
function League({ block }: { block: LeagueBlock }) {
  const id = `league-${block.league}`;
  return (
    <section className={s.league} aria-labelledby={id}>
      <h2 id={id} className={s.leagueTitle}>{block.title}</h2>
      {block.last_match && <LastResult match={block.last_match} sub />}
      {block.standings && <MiniTable standings={block.standings} sub />}
    </section>
  );
}

/**
 * Результаты по лигам (БЛ и ЛФЛ — рядом на desktop, друг под другом на mobile) и одна общая карточка формы.
 * Без by_league (старый API) — прежние три карточки: последний результат, форма, таблица.
 */
export function ResultFormTable({ last, form, totals, standings, byLeague = [] }: {
  last: MatchDetail | null; form: FormItem[]; totals: Totals; standings: Standings | null; byLeague?: LeagueBlock[];
}) {
  const hasForm = form.length > 0 || Boolean(totals.played);
  if (byLeague.length > 0) {
    return (
      <section className="section" aria-label="Результаты и таблицы">
        <div className={`container ${s.stack}`}>
          <div className={s.leagues}>
            {byLeague.map((block) => <League key={block.league} block={block} />)}
          </div>
          {hasForm && <Form form={form} totals={totals} mergeTable={false} wide />}
        </div>
      </section>
    );
  }
  if (!last && !hasForm && !standings) return null;
  return (
    <section className="section" aria-label="Результаты и таблица">
      <div className={`container ${s.grid}`}>
        {last && <LastResult match={last} />}
        {hasForm && <Form form={form} totals={totals} mergeTable={Boolean(standings)} />}
        {standings && <MiniTable standings={standings} />}
      </div>
    </section>
  );
}
