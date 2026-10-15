"use client";

import { useEffect, useState } from "react";
import { countdownParts, plural } from "@/lib/format";
import s from "./Countdown.module.css";

const UNITS: [keyof ReturnType<typeof countdownParts>, [string, string, string]][] = [
  ["days", ["день", "дня", "дней"]],
  ["hours", ["час", "часа", "часов"]],
  ["minutes", ["минута", "минуты", "минут"]],
];

export function Countdown({ kickoff }: { kickoff: string }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);
  const p = countdownParts(kickoff, now);
  if (p.over) return null;
  if (p.started) return <p className={s.live}>Матч идёт</p>;
  const label = UNITS.map(([k, forms]) => `${p[k]} ${plural(p[k] as number, forms)}`).join(" ");
  return (
    <div className={s.timer} role="timer" aria-label={`До матча ${label}`}>
      {UNITS.map(([k, forms]) => (
        <div key={k} className={s.unit} aria-hidden="true">
          <span className={s.value} suppressHydrationWarning>{String(p[k]).padStart(2, "0")}</span>
          <span className={s.caption} suppressHydrationWarning>{plural(p[k] as number, forms)}</span>
        </div>
      ))}
    </div>
  );
}
