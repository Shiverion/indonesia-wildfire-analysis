import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import {
  PORTFOLIO_URL,
  REPOSITORY_URL,
  SITE_DESCRIPTION,
  SITE_NAME,
  SITE_URL,
  createPageMetadata,
} from "./site-metadata";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  ...createPageMetadata({ title: SITE_NAME, description: SITE_DESCRIPTION, path: "/" }),
  authors: [{ name: "Muhammad Iqbal Hilmy Izzulhaq", url: "https://shiverion.com/" }],
  creator: "Muhammad Iqbal Hilmy Izzulhaq",
  keywords: ["Indonesia wildfire", "Kalimantan", "forest loss", "peat", "geospatial research", "matched sets", "evidence-bounded research"],
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large", "max-snippet": -1 },
  },
  icons: {
    icon: "/brands/wildfire-evidence-logo.svg",
    shortcut: "/brands/wildfire-evidence-logo.svg",
  },
};

const reportStructuredData = {
  "@context": "https://schema.org",
  "@type": "Report",
  "@id": `${SITE_URL}/#report`,
  name: SITE_NAME,
  headline: "Indonesia Wildfire Analysis: Evidence-Bounded Kalimantan Fire & Land-Cover Research",
  description: SITE_DESCRIPTION,
  url: `${SITE_URL}/`,
  mainEntityOfPage: `${SITE_URL}/`,
  datePublished: "2026-08-31",
  dateModified: "2026-09-01",
  isAccessibleForFree: true,
  author: {
    "@type": "Person",
    name: "Muhammad Iqbal Hilmy Izzulhaq",
    url: "https://shiverion.com/",
  },
  sameAs: [REPOSITORY_URL, PORTFOLIO_URL],
  keywords: ["Indonesia wildfire", "Kalimantan", "forest loss", "peat", "exact matched sets", "AlphaEarth"],
  about: [
    { "@type": "Place", name: "Kalimantan, Indonesia" },
    { "@type": "Thing", name: "Wildfire detection and subsequent forest loss" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="stylesheet" href="/cesium/Widgets/widgets.css" />
        <link rel="alternate" type="text/plain" title="LLMs.txt" href={`${SITE_URL}/llms.txt`} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(reportStructuredData) }}
        />
      </head>
      <body>
        <Script src="/cesium/Cesium.js" strategy="beforeInteractive" />
        {children}
      </body>
    </html>
  );
}
