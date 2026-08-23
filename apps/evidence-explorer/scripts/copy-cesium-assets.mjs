import { access, cp, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const appRoot = fileURLToPath(new URL("../", import.meta.url));
const source = fileURLToPath(new URL("../node_modules/cesium/Build/Cesium/", import.meta.url));
const destination = fileURLToPath(new URL("../public/cesium/", import.meta.url));

try {
  await access(source);
} catch {
  throw new Error("Cesium assets are missing. Run `npm install` before starting or building the explorer.");
}

await mkdir(destination, { recursive: true });
for (const directory of ["Assets", "ThirdParty", "Widgets", "Workers"]) {
  await cp(`${source}${directory}`, `${destination}${directory}`, { recursive: true, force: true });
}

console.log(`Copied Cesium runtime assets into ${destination} for static export.`);
