import { render, screen } from "@testing-library/react";
import { Photo } from "./Photo";

describe("Photo placeholder", () => {
  it("is a named image when alt is given", () => {
    render(<Photo alt="Иван Смирнов" />);
    expect(screen.getByRole("img", { name: "Иван Смирнов" })).toBeInTheDocument();
  });

  it("is hidden from assistive tech when alt is empty", () => {
    const { container } = render(<Photo alt="" />);
    const ph = container.firstElementChild!;
    expect(ph).toHaveAttribute("aria-hidden", "true");
    expect(ph).not.toHaveAttribute("role");
    expect(ph).not.toHaveAttribute("aria-label");
    expect(screen.queryByRole("img")).toBeNull();
  });
});
