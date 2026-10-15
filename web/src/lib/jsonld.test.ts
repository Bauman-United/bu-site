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

  it("breadcrumbs", () => {
    const ld = breadcrumbsLd([{ name: "Команда", path: "/team" }, { name: "Королев", path: "/team/a" }]);
    expect(ld.itemListElement[1]).toMatchObject({ position: 2, item: "https://baumanunited.ru/team/a" });
  });
});
