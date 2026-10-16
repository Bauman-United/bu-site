import { ImageResponse } from "next/og";
import { notFound } from "next/navigation";
import { getMatch } from "@/lib/api";
import { DATE_TBD, formatDate, formatTime } from "@/lib/format";
import { OG_FONT, OG_INK, OG_MUTED, OG_PAPER, OG_SIZE, ogFonts } from "@/lib/og";
import { SITE_NAME } from "@/lib/seo";
import { isPlayed } from "./match-meta";

export const alt = "Матч Бауман Юнайтед";
export const size = OG_SIZE;
export const contentType = "image/png";

const STRIPES = 22; // 1200 / 56 ≈ 21.4 — полосы по 56px, как на форме

/** OG-картинка матча, 1200×630, ч/б: турнир · тур, «БАУМАН ЮНАЙТЕД 3:1 СОПЕРНИК» (или VS + дата), полоса-мотив. */
export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const match = await getMatch(slug);
  if (!match) notFound();

  const played = isPlayed(match);
  const head = [match.tournament.short, match.round].filter(Boolean).join(" · ");
  const opponent = match.opponent_name.toUpperCase();
  const nameSize = opponent.length > 28 ? 44 : opponent.length > 16 ? 56 : 68;
  const name = { flex: 1, display: "flex", fontSize: nameSize, lineHeight: 1.05 } as const;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%", height: "100%", display: "flex", flexDirection: "column",
          background: OG_INK, color: OG_PAPER, fontFamily: OG_FONT,
        }}
      >
        <div style={{ display: "flex", padding: "56px 64px 0", fontSize: 32, letterSpacing: 3, color: OG_MUTED }}>
          {head.toUpperCase()}
        </div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 40, padding: "0 64px" }}>
          <div style={{ ...name, justifyContent: "flex-end", textAlign: "right" }}>
            {SITE_NAME.toUpperCase()}
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{ display: "flex", fontSize: played ? 180 : 120, lineHeight: 1 }}>
              {played ? `${match.score_us}:${match.score_them}` : "VS"}
            </div>
            {!played && (
              <div style={{ display: "flex", fontSize: 32, color: OG_MUTED, marginTop: 12 }}>
                {(match.kickoff ? `${formatDate(match.kickoff)} · ${formatTime(match.kickoff)}` : DATE_TBD).toUpperCase()}
              </div>
            )}
          </div>
          <div style={{ ...name, justifyContent: "flex-start" }}>{opponent}</div>
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
