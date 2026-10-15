import s from "./EmptyState.module.css";

export function EmptyState({ text }: { text: string }) {
  return <p className={s.empty}>{text}</p>;
}
