import s from "./LiveBadge.module.css";

export function LiveBadge() {
  return (
    <span className={s.live}>
      <span className={s.dot} aria-hidden="true" />
      LIVE
    </span>
  );
}
