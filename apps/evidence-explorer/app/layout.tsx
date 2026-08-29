import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  title: "Indonesia Wildfire Evidence Report",
  description: "An integrated, evidence-bounded report on fire, peat conditions, and subsequent forest loss in Indonesia with global comparison.",
  icons: {
    icon: "/brands/wildfire-evidence-logo.svg",
    shortcut: "/brands/wildfire-evidence-logo.svg",
  },
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
