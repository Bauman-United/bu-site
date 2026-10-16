import Link from "next/link";
import { Crest } from "@/components/ui/Crest";
import type { Club } from "@/lib/types";
import s from "./Header.module.css";
import { MobileMenu } from "./MobileMenu";
import { NavLinks } from "./NavLinks";
import { SocialIcons } from "./SocialIcons";
import { socialLinks } from "./socials";

export function Header({ club }: { club: Club }) {
  const socials = socialLinks(club);
  return (
    <header className={s.header}>
      <div className={s.inner}>
        <Link href="/" className={s.brand}>
          <Crest size={40} />
          <span className={s.brandName}>
            Бауман{" "}<br />Юнайтед
          </span>
        </Link>
        <nav aria-label="Основное меню" className={s.nav}>
          <NavLinks linkClassName={s.navLink} />
        </nav>
        <div className={s.actions}>
          <SocialIcons links={socials} className={s.socials} itemClassName={s.social} />
          <Link href="/partners" className={`${s.cta} ${s.partner}`}>Стать партнёром</Link>
          <Link href="/join" className={`${s.cta} ${s.join}`}>Хочу в команду</Link>
        </div>
        <MobileMenu
          socials={<SocialIcons links={socials} className={s.socials} itemClassName={s.social} />}
        />
      </div>
    </header>
  );
}
