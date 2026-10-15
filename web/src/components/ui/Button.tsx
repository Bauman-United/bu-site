import Link from "next/link";
import type { ReactNode } from "react";
import s from "./Button.module.css";

export function ButtonLink({
  href,
  children,
  variant = "primary",
  onPaper = false,
  external = false,
}: {
  href: string;
  children: ReactNode;
  variant?: "primary" | "secondary";
  onPaper?: boolean;
  external?: boolean;
}) {
  const className = `${s.button} ${s[variant]} ${onPaper ? s.onPaper : ""}`;
  if (external) {
    return (
      <a className={className} href={href} target="_blank" rel="noopener">
        {children}
      </a>
    );
  }
  return (
    <Link className={className} href={href}>
      {children}
    </Link>
  );
}
