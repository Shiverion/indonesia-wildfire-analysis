import { ImageResponse } from "next/og";

export const alt = "Indonesia Wildfire Evidence Report — evidence-bounded Kalimantan fire and forest-loss research";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          color: "#effff8",
          background: "linear-gradient(135deg, #06151a 0%, #0d2f32 55%, #713c19 100%)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px", color: "#85e8bc", fontSize: 28, letterSpacing: 3 }}>
          EVIDENCE-BOUNDED RESEARCH · KALIMANTAN
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <div style={{ display: "flex", maxWidth: 980, fontSize: 72, fontWeight: 800, lineHeight: 1.04 }}>
            Indonesia Wildfire Evidence Report
          </div>
          <div style={{ display: "flex", maxWidth: 980, color: "#c8ddd5", fontSize: 30, lineHeight: 1.35 }}>
            Registered analysis, uncertainty, methods, and explicit limits on causal or actor-level claims.
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", color: "#f3c38d", fontSize: 24 }}>
          <span>7,138 complete exact matched sets</span>
          <span>fire-research.shiverion.com</span>
        </div>
      </div>
    ),
    size,
  );
}
