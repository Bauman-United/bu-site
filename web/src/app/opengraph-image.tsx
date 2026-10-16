import { ImageResponse } from "next/og";
import { OG_FONT, OG_INK, OG_MUTED, OG_PAPER, OG_SIZE, ogFonts } from "@/lib/og";
import { SITE_NAME } from "@/lib/seo";

export const alt = "Бауман Юнайтед — футбольная команда МГТУ им. Н. Э. Баумана";
export const size = OG_SIZE;
export const contentType = "image/png";

const STRIPES = 22; // полосы по 56px, как на форме и в OG матча

/** OG-картинка по умолчанию (страницы без своей): карточка клуба, 1200×630, ч/б, полоса-мотив. */
export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%", height: "100%", display: "flex", flexDirection: "column",
          background: OG_INK, color: OG_PAPER, fontFamily: OG_FONT,
        }}
      >
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 64px" }}>
          <div style={{ display: "flex", fontSize: 120, lineHeight: 1, letterSpacing: 2 }}>
            {SITE_NAME.toUpperCase()}
          </div>
          <div style={{ display: "flex", fontSize: 40, color: OG_MUTED, marginTop: 28, letterSpacing: 1 }}>
            Футбольная команда МГТУ им. Н. Э. Баумана
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
