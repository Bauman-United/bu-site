import { ImageResponse } from "next/og";
import { notFound } from "next/navigation";
import { getPlayer } from "@/lib/api";
import { plural, positionLabel } from "@/lib/format";
import { OG_FONT, OG_INK, OG_MUTED, OG_PAPER, OG_SIZE, ogFonts } from "@/lib/og";
import { SITE_NAME } from "@/lib/seo";

export const alt = "Игрок Бауман Юнайтед";
export const size = OG_SIZE;
export const contentType = "image/png";

const STRIPES = 22; // полосы по 56px, как на форме

/** OG-картинка игрока, 1200×630, ч/б: гигантский номер, позиция, имя, ключевые цифры сезона, полоса-мотив. */
export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const player = await getPlayer(slug);
  if (!player) notFound();

  const { played = 0, goals = 0, assists = 0 } = player.season;
  const figures: [number, string][] = [
    [played, plural(played, ["матч", "матча", "матчей"])],
    [goals, plural(goals, ["гол", "гола", "голов"])],
    [assists, plural(assists, ["передача", "передачи", "передач"])],
  ];
  const longest = Math.max(player.first_name.length, player.last_name.length);
  const nameSize = longest > 16 ? 64 : longest > 11 ? 84 : 104;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%", height: "100%", display: "flex", flexDirection: "column",
          background: OG_INK, color: OG_PAPER, fontFamily: OG_FONT,
        }}
      >
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 56, padding: "0 64px" }}>
          {player.number !== null && (
            <div style={{ display: "flex", fontSize: 320, lineHeight: 1, width: 380, justifyContent: "center" }}>
              {String(player.number)}
            </div>
          )}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", fontSize: 30, letterSpacing: 3, color: OG_MUTED }}>
              {`${positionLabel(player.position)} · ${SITE_NAME}`.toUpperCase()}
            </div>
            <div style={{ display: "flex", flexDirection: "column", fontSize: nameSize, lineHeight: 0.95 }}>
              <div style={{ display: "flex" }}>{player.first_name.toUpperCase()}</div>
              <div style={{ display: "flex" }}>{player.last_name.toUpperCase()}</div>
            </div>
            <div style={{ display: "flex", gap: 40, marginTop: 16 }}>
              {figures.map(([value, label]) => (
                <div key={label} style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
                  <div style={{ display: "flex", fontSize: 64, lineHeight: 1 }}>{String(value)}</div>
                  <div style={{ display: "flex", fontSize: 28, color: OG_MUTED }}>{label.toUpperCase()}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", height: 48 }}>
          {Array.from({ length: STRIPES }, (_, i) => (
            <div key={i} style={{ width: 56, flexShrink: 0, background: i % 2 ? OG_INK : OG_PAPER }} />
          ))}
        </div>
      </div>
    ),
    { ...size, fonts: await ogFonts() },
  );
}
