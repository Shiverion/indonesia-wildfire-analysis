import type { Metadata } from "next";

export const SITE_URL = "https://fire-research.shiverion.com";
export const SITE_NAME = "Indonesia Wildfire Evidence Report";
export const SITE_DESCRIPTION = "An integrated, evidence-bounded report on fire, peat conditions, and subsequent forest loss in Indonesia with global comparison.";
export const REPOSITORY_URL = "https://github.com/Shiverion/indonesia-wildfire-analysis";
export const PORTFOLIO_URL = "https://shiverion.com/projects/indonesia-wildfire-analysis";

export function createPageMetadata({
  title,
  description,
  path,
}: {
  title: string;
  description: string;
  path: string;
}): Metadata {
  const canonical = new URL(path, SITE_URL).toString();
  return {
    title,
    description,
    alternates: { canonical },
    openGraph: {
      type: "website",
      url: canonical,
      siteName: SITE_NAME,
      title,
      description,
      locale: "en_US",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
  };
}
