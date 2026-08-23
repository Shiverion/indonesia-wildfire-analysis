# Kalimantan Fire Evidence Explorer (Next.js)

This App Router implementation hosts an interactive, aggregate-only **real WGS84 globe** as a maintainable Next.js application. It uses CesiumJS with a locally served NASA Blue Marble Earth surface and frozen geoBoundaries ADM1 geometry; the browser clicks actual aggregate reporting polygons, not illustrative dots.

It uses `output: "export"`, so `npm run build` produces a deployable static site in `out/`; the WebGL globe remains interactive in the browser.

## Run locally

From this folder:

```powershell
npm install
npm run sync-globe-assets
npm run dev
```

`npm run sync-globe-assets` downloads and freezes the approved source assets locally: the commit-pinned geoBoundaries IDN ADM1 simplified GeoJSON and NASA Blue Marble texture. It verifies the upstream boundary SHA-256, creates current-five and legacy-four geometry files, and records the source/license/transformation hashes in `public/geo/manifest.json`. The legacy Kalimantan Timur display feature is a topological union of current East and North Kalimantan and is never shown as two GWIS measurements.

`npm run dev` and `npm run build` synchronize `../../outputs/evidence-explorer/evidence-explorer.json` first. The synchronization check refuses a bundle if it contains prohibited raw-location fields, raw SiPongi records, 2024 SiPongi records, a Phase 1-ready flag, or a conclusion other than `NI - Not identifiable`. It also writes an ignored local receipt with the source SHA-256. `npm run build` additionally verifies the frozen globe asset manifest and copies Cesium runtime assets for static hosting.

Generate the aggregate bundle with `python scripts/research.py build-explorer` at the repository root whenever the research snapshot changes. Use `npm run build` to export the app into `out/`, then serve that directory over HTTP; opening it with `file://` is not a supported preview.

The app does not call a live data API, expose raw SiPongi locations, or convert the blocked primary analysis into a causal/risk result. It has no Cesium Ion token, default Ion imagery, terrain stream, or external tile feed at runtime.

## Deploy to Vercel

Create a Vercel project from the GitHub repository and set **Root Directory** to `apps/evidence-explorer`. Keep the detected Next.js framework, or use the checked-in `vercel.json` (`npm ci`, `npm run build`, output `out`). The app is a static export with a client-side WebGL globe; it does not need a server runtime or API route. The checked-in browser bundle is aggregate-only and is used when the Vercel build cannot read the repository-level `outputs/` directory. Refresh it locally with `python scripts/research.py build-explorer` followed by `npm run build` before pushing a new evidence snapshot.

The current export is about 19 MB, including Cesium runtime assets, a local Earth texture, and frozen country geometry. Raw FIRMS/VIIRS files, credentials, and source archives are not included. Vercel serves static output through its CDN; the globe still loads and interacts in the browser.

## Attribution

- Boundaries: geoBoundaries `IDN-ADM1-65028918`, source OpenStreetMap / Wambacher; © OpenStreetMap contributors, ODbL 1.0.
- Earth texture: NASA Blue Marble, *Land Surface, Ocean Color and Sea Ice*.

The machine-readable attribution, frozen URLs, and hashes are in [public/geo/manifest.json](public/geo/manifest.json). See [public/globe/NOTICE.md](public/globe/NOTICE.md) for the display-geometry boundary.
