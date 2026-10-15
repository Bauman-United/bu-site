import s from "./Stripes.module.css";

/** Мотив формы — вертикальные чёрно-белые полосы. Декоративный. */
export function Stripes({ height = 110, opacity = 1 }: { height?: number; opacity?: number }) {
  return <div className={`stripes ${s.stripes}`} style={{ height, opacity }} aria-hidden="true" />;
}
