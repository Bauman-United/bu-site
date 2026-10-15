import type { Outcome } from "@/lib/types";
import { outcomeLabel, outcomeLetter } from "@/lib/format";
import s from "./FormBadge.module.css";

export function FormBadge({ outcome, us, them, opponent, size = "m" }: {
  outcome: Outcome; us?: number; them?: number; opponent?: string; size?: "m" | "s";
}) {
  const score = us !== undefined && them !== undefined ? ` ${us}:${them}` : "";
  const vs = opponent ? ` vs ${opponent}` : "";
  const label = `${outcomeLabel(outcome)}${score}${vs}`;
  return (
    <span className={`${s.badge} ${s[outcome]} ${s[size]}`} role="img" aria-label={label} title={label}>
      {outcomeLetter(outcome)}
    </span>
  );
}
