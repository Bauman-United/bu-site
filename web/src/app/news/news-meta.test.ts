import { newsDescription, newsHref, parseNewsQuery, sourceLinkLabel, stripMarkdown } from "./news-meta";

describe("parseNewsQuery", () => {
  it("keeps known tag and valid page", () => {
    expect(parseNewsQuery({ tag: "transfer", page: "2" })).toEqual({ tag: "transfer", page: 2 });
  });
  it("ignores unknown tag and bad page", () => {
    expect(parseNewsQuery({ tag: "xxx", page: "0" })).toEqual({ tag: undefined, page: 1 });
    expect(parseNewsQuery({ page: "-3" }).page).toBe(1);
    expect(parseNewsQuery({ page: "abc" }).page).toBe(1);
    expect(parseNewsQuery({ tag: ["club", "match"], page: ["3"] })).toEqual({ tag: "club", page: 3 });
  });
});

describe("newsHref", () => {
  it("omits defaults", () => {
    expect(newsHref({})).toBe("/news");
    expect(newsHref({ page: 1 })).toBe("/news");
    expect(newsHref({ page: 2 })).toBe("/news?page=2");
    expect(newsHref({ tag: "club", page: 3 })).toBe("/news?tag=club&page=3");
  });
});

describe("newsDescription", () => {
  it("prefers lead, short text gets club context", () => {
    expect(newsDescription({ lead: "3:1 в **первом** туре.", body_md: "x" }))
      .toBe("3:1 в первом туре. Новости Бауман Юнайтед — футбольной команды МГТУ им. Баумана.");
    const lead = "Длинный лид новости, которого достаточно для сниппета в поисковой выдаче.";
    expect(newsDescription({ lead, body_md: "x" })).toBe(lead);
  });
  it("falls back to stripped body, max 160 chars", () => {
    expect(newsDescription({ lead: null, body_md: "## Как это было\n\nСчёт на **12-й** [минуте](/x)." }))
      .toBe("Как это было Счёт на 12-й минуте. Новости Бауман Юнайтед — футбольной команды МГТУ им. Баумана.");
    const long = newsDescription({ lead: null, body_md: "а".repeat(300) });
    expect(long.length).toBe(160);
    expect(long.endsWith("…")).toBe(true);
  });
  it("strips lists and quotes", () => {
    expect(stripMarkdown("- один\n> два\n1. три")).toBe("один два три");
  });
});

describe("sourceLinkLabel", () => {
  it("names the platform", () => {
    expect(sourceLinkLabel("telegram")).toBe("Оригинал в Telegram ↗");
    expect(sourceLinkLabel("vk")).toBe("Оригинал в VK ↗");
    expect(sourceLinkLabel(null)).toBe("Оригинал ↗");
  });
});
