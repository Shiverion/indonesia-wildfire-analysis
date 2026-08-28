import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kalimantan Fire Evidence Explorer",
  description: "Aggregate-only, evidence-bounded interactive globe for Kalimantan wildfire research.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="stylesheet" href="/cesium/Widgets/widgets.css" />
      </head>
      <body>
        <Script src="/cesium/Cesium.js" strategy="beforeInteractive" />
        {children}
      </body>
    </html>
  );
}
