import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { Stripes } from "@/components/ui/Stripes";
import { getClub } from "@/lib/api";
import { breadcrumbsLd } from "@/lib/jsonld";
import { buildMetadata } from "@/lib/seo";
import { PartnerForm } from "./PartnerForm";
import s from "./page.module.css";

export const metadata: Metadata = buildMetadata({
  title: "Партнёрам",
  description:
    "Как стать партнёром футбольной команды МГТУ им. Н. Э. Баумана «Бауман Юнайтед»: оставьте заявку — мы свяжемся.",
  path: "/partners",
});

export default async function PartnersPage() {
  const club = await getClub();
  const email = club.contacts?.email ?? null;
  return (
    <>
      <JsonLd data={breadcrumbsLd([{ name: "Партнёрам", path: "/partners" }])} />
      <section className={`container ${s.main}`}>
        <div className={s.intro}>
          <h1 className={s.h1}>Стать{" "}<br />партнёром</h1>
          <p className={s.lead}>
            Поддержите футбольную команду МГТУ им. Н. Э. Баумана: форма, турниры, экипировка.
            Оставьте контакты — мы свяжемся.
          </p>
          {email && <p className={s.mail}>Почта клуба: <a href={`mailto:${email}`}>{email}</a></p>}
        </div>
        <PartnerForm email={email} />
      </section>
      <Stripes height={8} />
    </>
  );
}
