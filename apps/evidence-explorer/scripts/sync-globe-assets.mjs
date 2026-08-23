import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import polygonClipping from "polygon-clipping";

const publicRoot = fileURLToPath(new URL("../public/", import.meta.url));
const geometryRoot = fileURLToPath(new URL("../public/geo/", import.meta.url));
const textureRoot = fileURLToPath(new URL("../public/globe/", import.meta.url));
const discoveryUrl = "https://www.geoboundaries.org/api/current/gbOpen/IDN/ADM1/";
const boundaryUrl = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IDN/ADM1/geoBoundaries-IDN-ADM1_simplified.geojson";
const expectedBoundarySha256 = "5a6be3d1484166132751fe535dd164e1491e657f2d38dced177f067a7bc00d8f";
const textureUrl = "https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57730/land_ocean_ice_2048.jpg";

const currentMapping = new Map([
  ["ID-KB", "Kalimantan Barat"],
  ["ID-KT", "Kalimantan Tengah"],
  ["ID-KS", "Kalimantan Selatan"],
  ["ID-KI", "Kalimantan Timur"],
  ["ID-KU", "Kalimantan Utara"],
]);

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function collectPositions(value, target) {
  if (!Array.isArray(value)) return;
  if (typeof value[0] === "number" && typeof value[1] === "number") {
    target.push(value);
    return;
  }
  value.forEach((entry) => collectPositions(entry, target));
}

function bboxCentroid(geometry) {
  const positions = [];
  collectPositions(geometry.coordinates, positions);
  if (!positions.length) throw new Error("Boundary geometry has no coordinate positions.");
  const longitudes = positions.map(([longitude]) => longitude);
  const latitudes = positions.map(([, latitude]) => latitude);
  return {
    longitude: (Math.min(...longitudes) + Math.max(...longitudes)) / 2,
    latitude: (Math.min(...latitudes) + Math.max(...latitudes)) / 2,
  };
}

function toMultiPolygon(geometry) {
  if (geometry?.type === "Polygon") return [geometry.coordinates];
  if (geometry?.type === "MultiPolygon") return geometry.coordinates;
  throw new Error(`Unsupported geometry type for legacy union: ${geometry?.type ?? "unknown"}`);
}

function makeFeature(feature, province, boundarySet, extra = {}) {
  return {
    type: "Feature",
    properties: {
      province,
      boundary_set: boundarySet,
      source_shape_iso: feature.properties.shapeISO,
      source_shape_id: feature.properties.shapeID,
      source_shape_name: feature.properties.shapeName,
      centroid: bboxCentroid(feature.geometry),
      geometry_role: "display geometry only; not an event location or analytical exposure boundary",
      ...extra,
    },
    geometry: feature.geometry,
  };
}

async function fetchChecked(url, kind) {
  const response = await fetch(url, { redirect: "follow" });
  if (!response.ok) throw new Error(`${kind} request failed with HTTP ${response.status}.`);
  return Buffer.from(await response.arrayBuffer());
}

const discovery = JSON.parse((await fetchChecked(discoveryUrl, "geoBoundaries discovery")).toString("utf8"));
if (discovery.boundaryID !== "IDN-ADM1-65028918" || discovery.boundaryLicense !== "Open Data Commons Open Database License 1.0") {
  throw new Error("geoBoundaries discovery metadata no longer matches the frozen IDN ADM1 source and license.");
}

const sourceBytes = await fetchChecked(boundaryUrl, "geoBoundaries simplified geometry");
const sourceSha256 = sha256(sourceBytes);
if (sourceSha256 !== expectedBoundarySha256) {
  throw new Error(`Frozen geoBoundaries hash mismatch: expected ${expectedBoundarySha256}, received ${sourceSha256}.`);
}
const source = JSON.parse(sourceBytes.toString("utf8"));
if (source.type !== "FeatureCollection" || !Array.isArray(source.features) || source.features.length !== 34) {
  throw new Error("Unexpected geoBoundaries IDN ADM1 FeatureCollection structure.");
}

const featureByIso = new Map(source.features.map((feature) => [feature?.properties?.shapeISO, feature]));
for (const [shapeIso, province] of currentMapping) {
  const feature = featureByIso.get(shapeIso);
  if (!feature || feature.properties.shapeType !== "ADM1") throw new Error(`Missing expected ${province} (${shapeIso}) ADM1 geometry.`);
}

const currentFeatures = [...currentMapping].map(([shapeIso, province]) => makeFeature(
  featureByIso.get(shapeIso),
  province,
  "sipongi_current_5",
  { display_id: `sipongi-${shapeIso.toLowerCase()}` },
));

const legacyFeatures = currentFeatures
  .filter((feature) => feature.properties.province !== "Kalimantan Utara" && feature.properties.province !== "Kalimantan Timur")
  .map((feature) => ({ ...feature, properties: { ...feature.properties, boundary_set: "gwis_legacy_4", display_id: `gwis-${feature.properties.source_shape_iso.toLowerCase()}` } }));

const indonesiaFeatures = source.features.map((feature) => makeFeature(
  feature,
  feature.properties.shapeName,
  "indonesia_adm1",
  {
    province_id: feature.properties.shapeISO,
    display_id: `indonesia-${String(feature.properties.shapeISO).toLowerCase()}`,
  },
));

const east = featureByIso.get("ID-KI");
const north = featureByIso.get("ID-KU");
const legacyUnionCoordinates = polygonClipping.union(toMultiPolygon(east.geometry), toMultiPolygon(north.geometry));
if (!legacyUnionCoordinates?.length) throw new Error("Topological union of East and North Kalimantan produced no geometry.");
const legacyUnion = {
  type: "Feature",
  properties: {
    province: "Kalimantan Timur",
    boundary_set: "gwis_legacy_4",
    display_id: "gwis-kaltim-legacy-display-union",
    source_shape_iso: ["ID-KI", "ID-KU"],
    source_shape_id: [east.properties.shapeID, north.properties.shapeID],
    source_shape_name: [east.properties.shapeName, north.properties.shapeName],
    centroid: bboxCentroid({ type: "MultiPolygon", coordinates: legacyUnionCoordinates }),
    geometry_role: "display-only topological union of current East and North Kalimantan; not a claim about a historical legal boundary",
    source_feature_shape_isos: ["ID-KI", "ID-KU"],
    operation: "topological union",
    legacy_note: "Legacy Kalimantan Timur display unit includes the current Kalimantan Utara area and receives one GWIS aggregate only.",
  },
  geometry: { type: "MultiPolygon", coordinates: legacyUnionCoordinates },
};
legacyFeatures.push(legacyUnion);

const currentCollection = { type: "FeatureCollection", name: "kalimantan-current-five", features: currentFeatures };
const legacyCollection = { type: "FeatureCollection", name: "kalimantan-legacy-four", features: legacyFeatures };
const indonesiaCollection = { type: "FeatureCollection", name: "indonesia-adm1", features: indonesiaFeatures };
const textureBytes = await fetchChecked(textureUrl, "NASA Blue Marble texture");
if (textureBytes.length < 100_000) throw new Error("NASA Blue Marble texture is unexpectedly small.");

const currentText = `${JSON.stringify(currentCollection)}\n`;
const legacyText = `${JSON.stringify(legacyCollection)}\n`;
const indonesiaText = `${JSON.stringify(indonesiaCollection)}\n`;
const manifest = {
  schema_version: "globe-assets/v1",
  generated_at_utc: new Date().toISOString(),
  geography: {
    source: "geoBoundaries gbOpen IDN ADM1",
    source_metadata_url: discoveryUrl,
    frozen_source_url: boundaryUrl,
    frozen_source_sha256: sourceSha256,
    boundary_id: discovery.boundaryID,
    boundary_year_represented: discovery.boundaryYearRepresented,
    source_credits: discovery.boundarySource,
    license: discovery.boundaryLicense,
    attribution: "Boundaries: geoBoundaries IDN ADM1, source OpenStreetMap / Wambacher; © OpenStreetMap contributors, ODbL 1.0.",
  },
  texture: {
    source: "NASA Blue Marble: Land Surface, Ocean Color and Sea Ice",
    source_url: textureUrl,
    sha256: sha256(textureBytes),
    bytes: textureBytes.length,
  },
  derived: {
    indonesia_adm1: { path: "/geo/indonesia-adm1.geojson", sha256: sha256(indonesiaText), feature_count: indonesiaFeatures.length },
    current_five: { path: "/geo/kalimantan-current-five.geojson", sha256: sha256(currentText), feature_count: currentFeatures.length },
    legacy_four: {
      path: "/geo/kalimantan-legacy-four.geojson",
      sha256: sha256(legacyText),
      feature_count: legacyFeatures.length,
      legacy_kaltim_operation: "topological union of current ID-KI and ID-KU",
    },
  },
};

await mkdir(publicRoot, { recursive: true });
await mkdir(geometryRoot, { recursive: true });
await mkdir(textureRoot, { recursive: true });
await writeFile(`${geometryRoot}kalimantan-current-five.geojson`, currentText);
await writeFile(`${geometryRoot}kalimantan-legacy-four.geojson`, legacyText);
await writeFile(`${geometryRoot}indonesia-adm1.geojson`, indonesiaText);
await writeFile(`${geometryRoot}manifest.json`, `${JSON.stringify(manifest, null, 2)}\n`);
await writeFile(`${textureRoot}earth-blue-marble.jpg`, textureBytes);

console.log(JSON.stringify({
  result: "synchronized",
  source_sha256: sourceSha256,
  current_five_features: currentFeatures.length,
  legacy_four_features: legacyFeatures.length,
  texture_sha256: manifest.texture.sha256,
}, null, 2));
