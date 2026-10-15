import type { Home } from "@/lib/types";
import { plural } from "@/lib/format";
import s from "./ClubNumbers.module.css";

/** «Цифры клуба» на полосе-текстуре: год основания, матчи, голы, трофеи. */
export function ClubNumbers({ numbers }: { numbers: Home["numbers"] }) {
  const items: [number, string][] = [];
  if (numbers.founded) items.push([numbers.founded, "основан"]);
  if (numbers.matches !== undefined) items.push([numbers.matches, plural(numbers.matches, ["матч сыгран", "матча сыграно", "матчей сыграно"])]);
  if (numbers.goals !== undefined) items.push([numbers.goals, plural(numbers.goals, ["гол забит", "гола забито", "голов забито"])]);
  if (numbers.trophies !== undefined) items.push([numbers.trophies, plural(numbers.trophies, ["трофей", "трофея", "трофеев"])]);
  if (items.length === 0) return null;
  return (
    <section className={s.section} aria-label="Цифры клуба">
      <div className={`stripes ${s.texture}`} aria-hidden="true" />
      <dl className={`container ${s.grid}`}>
        {items.map(([value, label]) => (
          <div key={label} className={s.item}>
            <dt className={s.label}>{label}</dt>
            <dd className={s.value}>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
