import "server-only";

import { readFile } from "node:fs/promises";
import { join } from "node:path";

const FONT_DIR = join(process.cwd(), "node_modules/@fontsource/oswald/files");

let fonts: ReturnType<typeof loadFonts> | undefined;

/**
 * Oswald 700 для `next/og`. Кириллический сабсет fontsource не содержит цифр и латиницы,
 * поэтому грузим и латинский отдельным семейством; в разметке — `fontFamily: OG_FONT` (цепочка фолбэка).
 * Файлы включены в standalone-сборку через `outputFileTracingIncludes` в next.config.
 */
export function ogFonts() {
  fonts ??= loadFonts().catch((e) => {
    fonts = undefined; // не кэшируем ошибку чтения — следующий рендер попробует снова
    throw e;
  });
  return fonts;
}

/** Читает файлы один раз на процесс; буферы переиспользуются всеми рендерами. */
async function loadFonts() {
  const [cyrillic, latin] = await Promise.all(
    ["oswald-cyrillic-700-normal.woff", "oswald-latin-700-normal.woff"].map((f) => readFile(join(FONT_DIR, f))),
  );
  return [
    { name: "Oswald", data: cyrillic, weight: 700 as const, style: "normal" as const },
    { name: "Oswald Latin", data: latin, weight: 700 as const, style: "normal" as const },
  ];
}

export const OG_FONT = "Oswald, Oswald Latin";
export const OG_SIZE = { width: 1200, height: 630 };
export const OG_INK = "#0A0A0A";
export const OG_PAPER = "#FFFFFF";
export const OG_MUTED = "#A3A3A3";
