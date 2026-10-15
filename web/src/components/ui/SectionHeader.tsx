import Link from "next/link";
import s from "./SectionHeader.module.css";

export function SectionHeader({
  title,
  eyebrow,
  link,
  as: Heading = "h2",
}: {
  title: string;
  eyebrow?: string;
  link?: { href: string; label: string };
  as?: "h1" | "h2";
}) {
  return (
    <div className={s.header}>
      <div className={s.titles}>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <Heading className={Heading === "h1" ? s.h1 : s.h2}>{title}</Heading>
      </div>
      {link && (
        <Link className={s.link} href={link.href}>
          {link.label} →
        </Link>
      )}
    </div>
  );
}
