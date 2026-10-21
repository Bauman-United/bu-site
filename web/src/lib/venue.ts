const VENUE_MAPS: ReadonlyArray<[prefix: string, url: string]> = [
  ["спартак", "https://yandex.com/maps/-/CXR7FBph"],
  ["сокольники", "https://yandex.com/maps/org/fc_rinus/209196528921/?ll=37.672904%2C55.805766&z=14"],
  ["аником", "https://yandex.com/maps/-/CXR7FG24"],
];

/** Точная карточка известного поля или поиск Яндекс Карт по доступному адресу/названию. */
export function venueMapUrl(name: string | null, address: string | null): string | null {
  const normalizedName = name?.trim().toLocaleLowerCase("ru-RU") ?? "";
  const known = VENUE_MAPS.find(([prefix]) => normalizedName.startsWith(prefix));
  if (known) return known[1];

  const query = address?.trim() || name?.trim();
  return query ? `https://yandex.ru/maps/?text=${encodeURIComponent(query)}` : null;
}
