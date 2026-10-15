"use client";

import Link from "next/link";
import { type KeyboardEvent, type ReactNode, useEffect, useRef, useState } from "react";
import { Crest } from "@/components/ui/Crest";
import s from "./MobileMenu.module.css";
import { NavLinks } from "./NavLinks";

const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Бургер и полноэкранное меню для экранов < 1024px. */
export function MobileMenu({ socials }: { socials: ReactNode }) {
  const [open, setOpen] = useState(false);
  const openerRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const close = () => setOpen(false);

  useEffect(() => {
    if (!open) return;
    const opener = openerRef.current;
    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";
    dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      opener?.focus();
    };
  }, [open]);

  // Удерживаем фокус внутри открытого диалога.
  const trapFocus = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "Tab" || !dialogRef.current) return;
    const items = [...dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last?.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first?.focus();
    }
  };

  return (
    <>
      <button
        ref={openerRef}
        type="button"
        className={s.burger}
        aria-label="Открыть меню"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          aria-hidden="true" focusable="false">
          <path d="M3 7h18M3 12h18M3 17h18" />
        </svg>
      </button>
      {open && (
        <div ref={dialogRef} className={s.dialog} role="dialog" aria-modal="true" aria-label="Меню"
          onKeyDown={trapFocus}>
          <div className={s.top}>
            <Link href="/" className={s.brand} onClick={close}>
              <Crest size={30} />
              <span>Бауман Юнайтед</span>
            </Link>
            <button type="button" className={s.burger} aria-label="Закрыть меню" onClick={close}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                aria-hidden="true" focusable="false">
                <path d="M5 5l14 14M19 5 5 19" />
              </svg>
            </button>
          </div>
          <nav aria-label="Разделы сайта" className={s.nav}>
            <NavLinks linkClassName={s.link} onNavigate={close} />
          </nav>
          <div className={s.bottom}>
            {socials}
            <Link href="/join" className={s.join} onClick={close}>Хочу в команду</Link>
          </div>
        </div>
      )}
    </>
  );
}
