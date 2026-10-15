import type { SocialLink } from "./socials";

function Glyph({ k }: { k: SocialLink["key"] }) {
  if (k === "vk") return <span aria-hidden="true">VK</span>;
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinejoin="round" aria-hidden="true" focusable="false">
      {k === "telegram" ? (
        <>
          <path d="M22 3 2 11l7 2 2 7 4-5 5 4z" />
          <path d="m9 13 8-6" />
        </>
      ) : (
        <>
          <rect x="2" y="5" width="20" height="14" rx="3" />
          <path d="m10 9 5 3-5 3z" />
        </>
      )}
    </svg>
  );
}

/** Иконки соцсетей 44×44 в рамке (шапка и мобильное меню). */
export function SocialIcons({ links, className, itemClassName }: {
  links: SocialLink[]; className?: string; itemClassName?: string;
}) {
  if (links.length === 0) return null;
  return (
    <div className={className}>
      {links.map((l) => (
        <a key={l.key} className={itemClassName} href={l.href} aria-label={l.label} target="_blank" rel="noopener">
          <Glyph k={l.key} />
        </a>
      ))}
    </div>
  );
}
