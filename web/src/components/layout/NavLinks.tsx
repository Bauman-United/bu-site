"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { isActive, NAV } from "./nav";

/** Пункты основного меню; активный получает `aria-current="page"`. */
export function NavLinks({ linkClassName, onNavigate }: { linkClassName?: string; onNavigate?: () => void }) {
  const pathname = usePathname() ?? "/";
  return NAV.map((item) => (
    <Link
      key={item.href}
      href={item.href}
      className={linkClassName}
      aria-current={isActive(pathname, item.href) ? "page" : undefined}
      onClick={onNavigate}
    >
      {item.label}
    </Link>
  ));
}
