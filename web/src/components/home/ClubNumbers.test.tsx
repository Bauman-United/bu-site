import { render } from "@testing-library/react";
import { ClubNumbers, clubNumberItems } from "./ClubNumbers";

describe("ClubNumbers", () => {
  it("drops zero and missing values", () => {
    expect(clubNumberItems({ founded: 2019, matches: 0, goals: 7, trophies: undefined }))
      .toEqual([[2019, "основан"], [7, "голов забито"]]);
    expect(clubNumberItems({ founded: null, matches: 3 })).toEqual([[3, "матча сыграно"]]);
  });

  it("renders nothing when every value is zero or missing", () => {
    const { container } = render(<ClubNumbers numbers={{ founded: null, matches: 0, goals: 0, trophies: 0 }} />);
    expect(container).toBeEmptyDOMElement();
  });
});
