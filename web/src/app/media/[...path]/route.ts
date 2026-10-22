import { readFile, stat } from "node:fs/promises";
import path from "node:path";

// Свои копии картинок и гифок из Telegram: их скачивает воркер (bu_worker/pipeline/media.py)
// в общий том. Файл под именем не меняется — кэшируем надолго.
export const dynamic = "force-dynamic";

const TYPES: Record<string, string> = {
  ".jpg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".mp4": "video/mp4",
};
const SEGMENT = /^[\w-]+(\.[a-z0-9]+)?$/i;

function mediaDir(): string {
  return process.env.BU_MEDIA_DIR ?? path.resolve(process.cwd(), "..", "media");
}

const notFound = () => new Response("Not found", { status: 404 });

export async function GET(request: Request, { params }: { params: Promise<{ path: string[] }> }) {
  const parts = (await params).path;
  const type = TYPES[path.extname(parts.at(-1) ?? "").toLowerCase()];
  if (!type || !parts.every((p) => SEGMENT.test(p))) return notFound();
  const file = path.join(mediaDir(), ...parts);
  const size = await stat(file).then((s) => (s.isFile() ? s.size : null), () => null);
  if (size === null) return notFound();

  const headers: Record<string, string> = {
    "Content-Type": type,
    "Cache-Control": "public, max-age=31536000, immutable",
    "Accept-Ranges": "bytes",
  };
  const data = await readFile(file);
  // Safari проигрывает mp4 только с ответами на Range-запросы.
  const range = /^bytes=(\d*)-(\d*)$/.exec(request.headers.get("range") ?? "");
  if (range && (range[1] || range[2])) {
    const start = range[1] ? Number(range[1]) : Math.max(size - Number(range[2]), 0);
    const end = range[1] && range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
    if (start > end || start >= size) {
      return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
    }
    return new Response(data.subarray(start, end + 1), {
      status: 206,
      headers: { ...headers, "Content-Range": `bytes ${start}-${end}/${size}`, "Content-Length": String(end - start + 1) },
    });
  }
  return new Response(data, { headers: { ...headers, "Content-Length": String(size) } });
}
