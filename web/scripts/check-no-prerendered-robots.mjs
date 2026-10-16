// После `next build`: robots.txt зависит от BU_NOINDEX/BU_SITE_URL рантайма и не должен
// пререндериться на сборке (иначе переключение окружения его не меняет). Запуск: `pnpm check:robots`.
import { existsSync, readFileSync } from "node:fs";

const MANIFEST = new URL("../.next/prerender-manifest.json", import.meta.url);
const RUNTIME_ONLY = ["/robots.txt"];

if (!existsSync(MANIFEST)) {
  console.error("check:robots: нет .next/prerender-manifest.json — сначала `pnpm build`.");
  process.exit(1);
}
const { routes = {} } = JSON.parse(readFileSync(MANIFEST, "utf8"));
const baked = RUNTIME_ONLY.filter((r) => r in routes);
if (baked.length) {
  console.error(`check:robots: пререндерены на сборке: ${baked.join(", ")} — нужен \`export const dynamic = "force-dynamic"\`.`);
  process.exit(1);
}
console.log(`check:robots: ok (${RUNTIME_ONLY.join(", ")} рендерятся в рантайме)`);
