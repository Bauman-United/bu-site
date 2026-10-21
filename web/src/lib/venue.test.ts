import { venueMapUrl } from "./venue";

describe("venueMapUrl", () => {
  it.each([
    ["Спартак", "https://yandex.com/maps/-/CXR7FBph"],
    ["  СПАРТАК — поле № 2", "https://yandex.com/maps/-/CXR7FBph"],
    ["Сокольники", "https://yandex.com/maps/org/fc_rinus/209196528921/?ll=37.672904%2C55.805766&z=14"],
    ["Аником 1", "https://yandex.com/maps/-/CXR7FG24"],
  ])("uses the saved map for %s", (name, expected) => {
    expect(venueMapUrl(name, "другой адрес")).toBe(expected);
  });

  it("falls back to the address, then the venue name", () => {
    expect(venueMapUrl("Металлург", "Москва, улица Новая Дорога, 11с1"))
      .toBe("https://yandex.ru/maps/?text=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C%20%D1%83%D0%BB%D0%B8%D1%86%D0%B0%20%D0%9D%D0%BE%D0%B2%D0%B0%D1%8F%20%D0%94%D0%BE%D1%80%D0%BE%D0%B3%D0%B0%2C%2011%D1%811");
    expect(venueMapUrl("Неизвестное поле", null)).toBe(
      "https://yandex.ru/maps/?text=%D0%9D%D0%B5%D0%B8%D0%B7%D0%B2%D0%B5%D1%81%D1%82%D0%BD%D0%BE%D0%B5%20%D0%BF%D0%BE%D0%BB%D0%B5",
    );
    expect(venueMapUrl(null, null)).toBeNull();
  });
});
