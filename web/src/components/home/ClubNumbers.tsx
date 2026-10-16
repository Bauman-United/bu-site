import Link from "next/link";
import type { Home } from "@/lib/types";
import { plural } from "@/lib/format";
import s from "./ClubNumbers.module.css";

const trophiesLabel = (n: number) => plural(n, ["трофей", "трофея", "трофеев"]);

/** Пункты «Цифр клуба»: нулевые и отсутствующие значения не показываем («0 трофеев» — не цифра клуба). */
export function clubNumberItems(numbers: Home["numbers"]): [number, string][] {
  const items: [number, string][] = [];
  const { founded, matches, goals, trophies } = numbers;
  if (founded) items.push([founded, "основан"]);
  if (matches) items.push([matches, plural(matches, ["матч сыгран", "матча сыграно", "матчей сыграно"])]);
  if (goals) items.push([goals, plural(goals, ["гол забит", "гола забито", "голов забито"])]);
  if (trophies) items.push([trophies, trophiesLabel(trophies)]);
  return items;
}

/** «Цифры клуба» на полосе-текстуре: год основания, матчи, голы, трофеи; без единой цифры блока нет. */
export function ClubNumbers({ numbers }: { numbers: Home["numbers"] }) {
  const items = clubNumberItems(numbers);
  if (items.length === 0) return null;
  return (
    <section className={s.section} aria-label="Цифры клуба">
      <div className={`stripes ${s.texture}`} aria-hidden="true" />
      <dl className={`container ${s.grid}`}>
        {items.map(([value, label]) => (
          <div key={label} className={s.item}>
            <dt className={s.label}>
              {/* трофеи — в «Зале славы» */}
              {numbers.trophies && label === trophiesLabel(numbers.trophies) ? (
                <Link className={s.link} href="/hall-of-fame">{label}</Link>
              ) : (
                label
              )}
            </dt>
            <dd className={s.value}>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
