import { render } from "@testing-library/react";
import { Markdown } from "./Markdown";

describe("Markdown", () => {
  it("renders markdown and escapes raw HTML", () => {
    const { container } = render(<Markdown source={"## Заголовок\n\n**жирный** <script>alert(1)</script><b>x</b>"} />);
    expect(container.querySelector("h2")).toHaveTextContent("Заголовок");
    expect(container.querySelector("strong")).toHaveTextContent("жирный");
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
  });

  it("opens external links in a new tab, keeps internal ones", () => {
    const { getByText } = render(<Markdown source={"[вне](https://t.me/x) и [внутри](/news/a)"} />);
    expect(getByText("вне")).toHaveAttribute("target", "_blank");
    expect(getByText("вне")).toHaveAttribute("rel", "noopener");
    expect(getByText("внутри")).toHaveAttribute("href", "/news/a");
    expect(getByText("внутри")).not.toHaveAttribute("target");
  });

  it("drops javascript: urls", () => {
    const { getByText } = render(<Markdown source={"[x](javascript:alert(1))"} />);
    expect(getByText("x").getAttribute("href") ?? "").not.toContain("javascript");
  });
});
