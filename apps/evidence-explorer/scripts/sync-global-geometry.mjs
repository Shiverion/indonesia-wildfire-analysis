import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

// Natural Earth is kept in the research data area as the frozen country-level
// display source. The browser receives only the geometry and the join fields;
// the large source property table never travels into the UI bundle.
const sourcePath = fileURLToPath(new URL("../../../data/raw/peat/global/ne_50m_admin_0_countries.geojson", import.meta.url));
const publicRoot = fileURLToPath(new URL("../public/geo/", import.meta.url));
const destinationPath = `${publicRoot}global-countries.geojson`;
const manifestPath = `${publicRoot}manifest.json`;

let sourceText;
let usingCheckedInGeometry = false;
try {
  sourceText = await readFile(sourcePath, "utf8");
} catch {
  // Vercel receives the already stripped, checked-in public geometry rather
  // than the repository-level raw Natural Earth property table.
  sourceText = await readFile(destinationPath, "utf8");
  usingCheckedInGeometry = true;
}
const source = JSON.parse(sourceText);
if (source?.type !== "FeatureCollection" || !Array.isArray(source.features) || source.features.length < 200) {
  throw new Error("Frozen Natural Earth country geometry is missing or unexpectedly small.");
}

const features = source.features.map((feature) => {
  const properties = feature?.properties ?? {};
  if (usingCheckedInGeometry) {
    if (!properties.country_id || !properties.country_name || !feature.geometry) {
      throw new Error("Checked-in country display geometry has invalid public properties.");
    }
    return feature;
  }
  const rawId = String(properties.ISO_A3 ?? "-99") === "-99"
    ? String(properties.ADM0_A3 ?? properties.WB_A3 ?? "")
    : String(properties.ISO_A3 ?? "");
  // The frozen country aggregate table uses the stable IDs used by its source
  // metadata for Palestine and South Sudan; Natural Earth uses ISO display IDs.
  const id = ({ PSE: "PSX", SSD: "SDS" })[rawId] ?? rawId;
  const name = String(properties.NAME_EN ?? properties.NAME_LONG ?? properties.NAME ?? id);
  if (!id || id === "-99" || !feature.geometry) throw new Error(`Country geometry has no stable ISO join: ${name}`);
  return {
    type: "Feature",
    properties: {
      country_id: id,
      country_name: name,
      geometry_role: "country display geometry only; not a fire location or risk surface",
    },
    geometry: feature.geometry,
  };
});

const collection = {
  type: "FeatureCollection",
  name: "natural-earth-admin-0-country-display",
  features,
};
const text = `${JSON.stringify(collection)}\n`;
const sha256 = createHash("sha256").update(text).digest("hex");

const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
manifest.global_country_display = {
  path: "/geo/global-countries.geojson",
  source: "Natural Earth 5.0m Admin-0 countries",
  source_url: "https://www.naturalearthdata.com/downloads/50m-cultural-vectors/",
  license: "Public domain",
  geometry_role: "Country-level context display only; values are matched country aggregates, never individual fire locations.",
  sha256,
  feature_count: features.length,
};

await mkdir(publicRoot, { recursive: true });
await writeFile(destinationPath, text);
await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
console.log(JSON.stringify({ destination: destinationPath, feature_count: features.length, sha256 }, null, 2));
