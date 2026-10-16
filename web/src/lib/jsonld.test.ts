import { breadcrumbsLd, sportsEventLd, sportsTeamLd } from "./jsonld";

describe("json-ld", () => {
  beforeEach(() => { process.env.BU_SITE_URL = "https://baumanunited.ru"; });

  it("SportsTeam with university and sameAs", () => {
    const ld = sportsTeamLd({
      name: "Бауман Юнайтед", name_en: "Bauman United", university: "МГТУ им. Н. Э. Баумана",
      city: "Москва", socials: { telegram: "https://t.me/x", vk: null, lfl: "https://lfl.ru/club14270" },
    });
    expect(ld).toMatchObject({
      "@context": "https://schema.org", "@type": "SportsTeam", sport: "Football",
      alternateName: "Bauman United",
      memberOf: { "@type": "CollegeOrUniversity", name: "МГТУ им. Н. Э. Баумана" },
      sameAs: ["https://t.me/x", "https://lfl.ru/club14270"],
    });
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
    });
  });

  it("SportsEvent without a known date omits startDate", () => {
    const ld = sportsEventLd({
      slug: "kvazar-5877228", kickoff: null, home: false,
      opponent_name: "Квазар", status: "scheduled", venue_name: null, venue_address: null,
      tournament: { name: "Кубок Специалистов · Осень 2026" }, round: "Четвертьфинал",
    } as never);
    expect(ld).not.toHaveProperty("startDate");
    expect(ld).toMatchObject({ "@type": "SportsEvent", name: "Квазар — Бауман Юнайтед" });
  });

  it("breadcrumbs", () => {
    const ld = breadcrumbsLd([{ name: "Команда", path: "/team" }, { name: "Королев", path: "/team/a" }]);
    expect(ld.itemListElement[1]).toMatchObject({ position: 2, item: "https://baumanunited.ru/team/a" });
  });
});
