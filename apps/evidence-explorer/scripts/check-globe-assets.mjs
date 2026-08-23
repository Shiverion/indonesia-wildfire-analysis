import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const geometryRoot = fileURLToPath(new URL("../public/geo/", import.meta.url));
const texturePath = fileURLToPath(new URL("../public/globe/earth-blue-marble.jpg", import.meta.url));
const required = [
  ["indonesia", `${geometryRoot}indonesia-adm1.geojson`, 34, "indonesia_adm1"],
  ["current", `${geometryRoot}kalimantan-current-five.geojson`, 5, "sipongi_current_5"],
  ["legacy", `${geometryRoot}kalimantan-legacy-four.geojson`, 4, "gwis_legacy_4"],
];

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

const manifest = JSON.parse(await readFile(`${geometryRoot}manifest.json`, "utf8"));
if (manifest?.geography?.frozen_source_sha256 !== "5a6be3d1484166132751fe535dd164e1491e657f2d38dced177f067a7bc00d8f") {
  throw new Error("Globe geometry manifest does not preserve the frozen geoBoundaries source hash.");
}
if (manifest?.geography?.license !== "Open Data Commons Open Database License 1.0") {
  throw new Error("Globe geometry manifest does not preserve the IDN ADM1 boundary license.");
}
for (const [kind, path, expectedFeatureCount, boundarySet] of required) {
  const text = await readFile(path, "utf8");
  const collection = JSON.parse(text);
  if (collection?.type !== "FeatureCollection" || collection.features?.length !== expectedFeatureCount) {
    throw new Error(`${kind} globe geometry does not have ${expectedFeatureCount} features.`);
  }
  if (collection.features.some((feature) => feature?.properties?.boundary_set !== boundarySet || !feature?.properties?.province || !feature?.geometry)) {
    throw new Error(`${kind} globe geometry has invalid display properties.`);
  }
  const derived = kind === "indonesia" ? manifest.derived.indonesia_adm1 : kind === "current" ? manifest.derived.current_five : manifest.derived.legacy_four;
  if (sha256(text) !== derived.sha256) throw new Error(`${kind} globe geometry hash does not match its manifest.`);
  if (kind === "legacy") {
    const legacyKaltim = collection.features.find((feature) => feature.properties.province === "Kalimantan Timur");
    if (legacyKaltim?.properties?.operation !== "topological union" || legacyKaltim.geometry?.type !== "MultiPolygon") {
      throw new Error("Legacy Kalimantan Timur is not the required explicit topological display union.");
    }
  }
}
const texture = await readFile(texturePath);
if (texture.length < 100_000 || texture[0] !== 0xff || texture[1] !== 0xd8 || sha256(texture) !== manifest.texture.sha256) {
  throw new Error("NASA Blue Marble texture is missing, truncated, or does not match its manifest.");
}
console.log("Verified frozen globe geometry and texture assets.");
