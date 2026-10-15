import Image from "next/image";
import s from "./Photo.module.css";

/** Фото с фиксированной пропорцией; без `src` — штриховка-плейсхолдер (`light` — для белого фона). */
export function Photo({
  src,
  alt,
  ratio = "4 / 3",
  light = false,
  sizes = "100vw",
  priority = false,
}: {
  src?: string | null;
  alt: string;
  ratio?: string;
  light?: boolean;
  sizes?: string;
  priority?: boolean;
}) {
  if (!src) {
    return <div className={`${light ? "phl" : "ph"} ${s.photo}`} style={{ aspectRatio: ratio }} {...(alt ? { role: "img", "aria-label": alt } : { "aria-hidden": true })} />;
  }
  return (
    <div className={`${light ? "phl" : "ph"} ${s.photo}`} style={{ aspectRatio: ratio }}>
      <Image className={s.img} src={src} alt={alt} fill sizes={sizes} priority={priority} />
    </div>
  );
}
