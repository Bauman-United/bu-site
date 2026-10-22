// Ключ IndexNow: поисковик сверяет его с ключом в запросе воркера (keyLocation).
// Без BU_INDEXNOW_KEY (dev, сайт закрыт от индексации) — 404.
export const dynamic = "force-dynamic";

export function GET() {
  const key = process.env.BU_INDEXNOW_KEY;
  if (!key) return new Response("Not found", { status: 404 });
  return new Response(key, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
