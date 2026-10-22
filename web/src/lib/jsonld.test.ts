import { breadcrumbsLd, newsArticleLd, sportsEventLd, sportsTeamLd, webSiteLd } from "./jsonld";

describe("json-ld", () => {
  beforeEach(() => { process.env.BU_SITE_URL = "https://baumanunited.ru"; });

  it("SportsTeam with university and sameAs", () => {
    const ld = sportsTeamLd({
      name: "Бауман Юнайтед", name_en: "Bauman United", university: "МГТУ им. Н. Э. Баумана",
      city: "Москва", socials: { telegram: "https://t.me/x", vk: null, lfl: "https://lfl.ru/club14270" },
    });
    expect(ld).toMatchObject({
      "@context": "https://schema.org", "@type": "SportsTeam", sport: "Football",
      alternateName: expect.arrayContaining(["Bauman United", "Футбольная команда МГТУ им. Баумана"]),
      memberOf: { "@type": "CollegeOrUniversity", name: "МГТУ им. Н. Э. Баумана" },
      sameAs: ["https://t.me/x", "https://lfl.ru/club14270"],
    });
  });

  it("WebSite names the site and its alternate names without repeating the main one", () => {
    const ld = webSiteLd({ name: "Бауман Юнайтед", name_en: "Bauman United" } as never);
    expect(ld).toMatchObject({ "@type": "WebSite", name: "Бауман Юнайтед", url: "https://baumanunited.ru/" });
    expect(ld.alternateName).toContain("Bauman United");
    expect(ld.alternateName).not.toContain("Бауман Юнайтед");
    expect(new Set(ld.alternateName).size).toBe(ld.alternateName.length);
  });

  it("NewsArticle image is absolute for own media", () => {
    const ld = newsArticleLd({ slug: "tg-1", title: "t", date: "2026-10-01", cover: "/media/tg/tg-1.jpg" } as never);
    expect(ld.image).toEqual(["https://baumanunited.ru/media/tg/tg-1.jpg"]);
  });

  it("SportsTeam sameAs keeps only http(s) URLs", () => {
    const ld = sportsTeamLd({
      name: "Бауман Юнайтед",
      socials: { telegram: "@baumanunited", vk: "https://vk.com/x", lfl: "javascript:alert(1)", youtube: "http://y.tube/x", joinfootball: "" },
    } as never);
    expect(ld.sameAs).toEqual(["https://vk.com/x", "http://y.tube/x"]);
  });

  it("SportsEvent for away match", () => {
    const ld = sportsEventLd({
      slug: "2026-10-24-messiya", kickoff: "2026-10-24T21:30:00+03:00", home: false,
      opponent_name: "Мессия", status: "scheduled", venue_name: "Металлург", venue_address: "Москва",
      tournament: { name: "Лига Инженеров · Осень 2026" }, round: "6 тур",
    } as never);
    expect(ld).toMatchObject({
      "@type": "SportsEvent", startDate: "2026-10-24T21:30:00+03:00",
      homeTeam: { name: "Мессия" }, awayTeam: { name: "Бауман Юнайтед" },
      eventStatus: "https://schema.org/EventScheduled",
      url: "https://baumanunited.ru/matches/2026-10-24-messiya",
      endDate: "2026-10-24T20:00:00.000Z",
      performer: [{ name: "Мессия" }, { name: "Бауман Юнайтед" }],
      organizer: { "@type": "SportsOrganization", name: "Лига Инженеров · Осень 2026" },
      image: ["https://baumanunited.ru/matches/2026-10-24-messiya/opengraph-image"],
      location: {
        "@type": "Place", name: "Металлург",
        address: { "@type": "PostalAddress", streetAddress: "Москва", addressLocality: "Москва", addressCountry: "RU" },
      },
    });
    // вложенный SportsEvent Google проверяет как отдельное мероприятие без даты и места
    expect(ld).not.toHaveProperty("superEvent");
  });

  it("SportsEvent without a known date is not emitted", () => {
    const ld = sportsEventLd({
      slug: "kvazar-5877228", kickoff: null, home: false,
      opponent_name: "Квазар", status: "scheduled", venue_name: null, venue_address: null,
      tournament: { name: "Кубок Специалистов · Осень 2026" }, round: "Четвертьфинал",
    } as never);
    expect(ld).toBeNull();
  });

  it("breadcrumbs", () => {
    const ld = breadcrumbsLd([{ name: "Команда", path: "/team" }, { name: "Королев", path: "/team/a" }]);
    expect(ld.itemListElement[1]).toMatchObject({ position: 2, item: "https://baumanunited.ru/team/a" });
  });
});
