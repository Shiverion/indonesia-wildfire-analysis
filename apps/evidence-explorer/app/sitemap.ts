import type { MetadataRoute } from "next";
import { SITE_URL } from "./site-metadata";

const lastModified = new Date("2026-09-01T00:00:00.000Z");

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: `${SITE_URL}/`, lastModified, changeFrequency: "monthly", priority: 1 },
    { url: `${SITE_URL}/findings/`, lastModified, changeFrequency: "monthly", priority: 0.95 },
    { url: `${SITE_URL}/methods/`, lastModified, changeFrequency: "monthly", priority: 0.9 },
    { url: `${SITE_URL}/explore/`, lastModified, changeFrequency: "monthly", priority: 0.85 },
    { url: `${SITE_URL}/privacy/`, lastModified, changeFrequency: "yearly", priority: 0.4 },
  ];
}
