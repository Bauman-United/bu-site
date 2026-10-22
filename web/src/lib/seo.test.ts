import { absUrl, buildMetadata, pageTitle, siteUrl } from "./seo";

describe("seo", () => {
  beforeEach(() => {
    process.env.BU_SITE_URL = "https://baumanunited.ru/";
    process.env.BU_NOINDEX = "1";
  });

  it("titles", () => {
    expect(pageTitle()).toBe("Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана");
    expect(pageTitle("Матчи")).toBe("Матчи — Бауман Юнайтед | футбольная команда МГТУ им. Баумана");
    expect(pageTitle("Наиль Мукминов", true)).toBe("Наиль Мукминов — Бауман Юнайтед");
  });

  it("sections get the full suffix, nested pages the short one", () => {
    const title = (path: string) => (buildMetadata({ title: "X", description: "x", path }).title as { absolute: string }).absolute;
    expect(title("/matches")).toBe("X — Бауман Юнайтед | футбольная команда МГТУ им. Баумана");
    expect(title("/matches/2016-10-30-berezovaya-shtanga")).toBe("X — Бауман Юнайтед");
  });

  it("absUrl keeps absolute urls and prefixes own paths", () => {
    expect(absUrl("https://cdn/x.jpg")).toBe("https://cdn/x.jpg");
    expect(absUrl("/media/tg/tg-1.jpg")).toBe("https://baumanunited.ru/media/tg/tg-1.jpg");
  });

  it("canonical, og and noindex", () => {
    expect(siteUrl()).toBe("https://baumanunited.ru");
    const m = buildMetadata({ title: "Матчи", description: "Календарь", path: "/matches" });
    expect(m.alternates?.canonical).toBe("https://baumanunited.ru/matches");
    expect(m.openGraph).toMatchObject({ locale: "ru_RU", url: "https://baumanunited.ru/matches" });
    expect(m.robots).toMatchObject({ index: false, follow: false });
  });

  it("indexable when BU_NOINDEX=0 unless page asks noindex", () => {
    process.env.BU_NOINDEX = "0";
    expect(buildMetadata({ description: "x", path: "/" }).robots).toMatchObject({ index: true });
    expect(buildMetadata({ description: "x", path: "/m", noindex: true }).robots).toMatchObject({ index: false, follow: true });
  });

  it("og:image: default club card, explicit image, or the page's own opengraph-image file", () => {
    const images = (m: ReturnType<typeof buildMetadata>) => (m.openGraph as { images?: unknown }).images;
    expect(images(buildMetadata({ description: "x", path: "/news" })))
      .toEqual([{ url: "https://baumanunited.ru/opengraph-image", width: 1200, height: 630, alt: "Бауман Юнайтед" }]);
    expect(images(buildMetadata({ description: "x", path: "/news/a", image: "https://cdn/x.jpg" })))
      .toEqual([{ url: "https://cdn/x.jpg", width: 1200, height: 630 }]);
    const own = buildMetadata({ description: "x", path: "/matches/a", ownOgImage: true });
    expect(own.openGraph).not.toHaveProperty("images");
  });
});
