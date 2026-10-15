import s from "./Crest.module.css";

/** Герб-заглушка (щит с тремя полосами и «БЮ»). `inverted` — версия для белого фона. */
export function Crest({ size = 40, inverted = false }: { size?: number; inverted?: boolean }) {
  return (
    <svg
      className={`${s.crest} ${inverted ? s.inverted : ""}`}
      width={size}
      height={Math.round((size * 46) / 40)}
      viewBox="0 0 40 46"
      aria-hidden="true"
      focusable="false"
    >
      <path className={s.shield} d="M20 1 L38 6 V22 C38 34 30 41 20 45 C10 41 2 34 2 22 V6 Z" strokeWidth="2" />
      <path className={s.stripes} d="M11 4.5 V40 M20 2 V44 M29 4.5 V40" strokeWidth="4" />
      <rect className={s.plate} x="6" y="15" width="28" height="14" />
      <text className={s.text} x="20" y="26" textAnchor="middle" fontWeight="700" fontSize="11">БЮ</text>
    </svg>
  );
}
