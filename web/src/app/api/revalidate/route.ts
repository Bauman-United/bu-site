import { revalidateTag } from "next/cache";

export async function POST(request: Request): Promise<Response> {
  const secret = process.env.BU_REVALIDATE_SECRET;
  if (!secret) return Response.json({ error: "not configured" }, { status: 503 });
  if (request.headers.get("authorization") !== `Bearer ${secret}`) {
    return Response.json({ error: "unauthorized" }, { status: 401 });
  }
  const body = (await request.json().catch(() => ({}))) as { tags?: unknown };
  const tags = Array.isArray(body.tags) ? body.tags.filter((t): t is string => typeof t === "string") : [];
  for (const tag of tags) revalidateTag(tag, "max");
  return Response.json({ revalidated: tags });
}
