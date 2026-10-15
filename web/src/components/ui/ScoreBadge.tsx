import type { Outcome } from "@/lib/types";
import { outcomeLabel } from "@/lib/format";
import s from "./ScoreBadge.module.css";

export function ScoreBadge({ outcome, us, them }: { outcome: Outcome; us: number; them: number }) {
  const label = `${outcomeLabel(outcome)} ${us}:${them}`;
  return (
    <span className={`${s.badge} ${s[outcome]}`} role="img" aria-label={label} title={label}>
      {us}:{them}
    </span>
  );
}
