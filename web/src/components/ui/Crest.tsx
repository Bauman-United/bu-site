import Image from "next/image";
import s from "./Crest.module.css";

/**
 * Эмблема клуба (BMSTU FC, исходник — профиль команды в Бауманской лиге).
 * По умолчанию белая для чёрного фона; `inverted` — чёрная для белого.
 * Блок прежнего размера (size × size·46/40), эмблема вписывается внутрь.
 */
export function Crest({ size = 40, inverted = false }: { size?: number; inverted?: boolean }) {
  const height = Math.round((size * 46) / 40);
  return (
    <Image
      className={s.crest}
      src={inverted ? "/crest-black.png" : "/crest-white.png"}
      alt=""
      aria-hidden="true"
      width={size}
      height={height}
      unoptimized
    />
  );
}
