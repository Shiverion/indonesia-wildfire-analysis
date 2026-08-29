# Indonesia Wildfire Evidence Report (Next.js)

Production: https://fire-research.shiverion.com

This App Router implementation presents one research report through a hybrid page structure. The introduction at `/` contains only the research purpose, questions, scope, and reading paths—no result cards, maps, or research data imports. Related evidence is grouped into `/findings` for fitted statistical and predictive results, `/explore` for Indonesia/global maps and Kalimantan detail, and `/methods` for sources, validation, provenance, and claim boundaries. Anchors are reserved for subsections within each page.

The exploration page hosts two interactive, aggregate-only **real WGS84 globes** using CesiumJS with a locally served NASA Blue Marble Earth surface and frozen boundary geometry; the browser clicks actual aggregate reporting polygons, not illustrative dots.

The report also includes a server-side, evidence-bounded Kimi explanation layer. It is deliberately not a general chatbot: every request receives only one compact public evidence pack, answers require fact-ID citations, and the server rejects unknown citations or numbers before they reach the browser. Raw questions are not stored by the application and Kimi reasoning content is never exposed.

The report interface and suggested questions use English consistently. Kimi follows the language of the reader's question, so an Indonesian question can still receive an Indonesian explanation without changing the report UI language.

## Run locally

From this folder:

```powershell
npm install
npm run sync-globe-assets
npm run dev
```

For the optional research assistant, put `KIMI_API_KEY` in this app's `.env.local` or in the repository-root `.env`. The repository-root fallback is development-only; production reads the server environment. Never use `NEXT_PUBLIC_KIMI_API_KEY`. `KIMI_MODEL` defaults to `kimi-k2.5`.

`npm run sync-globe-assets` downloads and freezes the approved source assets locally: the commit-pinned geoBoundaries IDN ADM1 simplified GeoJSON and NASA Blue Marble texture. It verifies the upstream boundary SHA-256, creates current-five and legacy-four geometry files, and records the source/license/transformation hashes in `public/geo/manifest.json`. The legacy Kalimantan Timur display feature is a topological union of current East and North Kalimantan and is never shown as two GWIS measurements.

`npm run dev` and `npm run build` synchronize `../../outputs/evidence-explorer/evidence-explorer.json` first. The synchronization check refuses a bundle if it contains prohibited raw-location fields, raw SiPongi records, 2024 SiPongi records, a Phase 1-ready flag, or a conclusion other than `NI - Not identifiable`. It also writes an ignored local receipt with the source SHA-256. `npm run build` additionally verifies the frozen globe asset manifest and copies Cesium runtime assets into `public/`.

Generate the aggregate bundle with `python scripts/research.py build-explorer` at the repository root whenever the research snapshot changes. Use `npm run build` to create the production Next.js application, then `npm run start` for a local production preview. Opening generated files with `file://` is not supported.

The globes do not call a live data API, expose raw SiPongi locations, or convert a descriptive layer into a causal/risk result. The Kimi route receives only compact coordinate-free statements from `lib/research-corpus.ts`; it has no retrieval path to local raw data. The app has no Cesium Ion token, default Ion imagery, terrain stream, or external tile feed at runtime.

### Assistant accountability contract

- The API key remains server-only. The browser calls `/api/research-chat`, never Moonshot directly.
- A deterministic preflight rejects unrelated questions and requests for prompts, secrets, reasoning, raw records, or private coordinates before Kimi is called.
- Kimi runs in thinking mode but only structured final JSON is processed; `reasoning_content` is discarded on the server.
- A post-model validator checks status, citation IDs, and every displayed numeric token against the selected evidence pack. Invalid output becomes the bounded fallback: “This research has not conducted enough analysis to answer that question.”
- Each displayed answer includes a receipt with the model, prompt and corpus versions, cited evidence IDs, validator result, latency, and a statement that this application did not store the raw question. The question and selected evidence pack are still processed by Moonshot's API and remain subject to the provider's applicable data terms.
- The route applies same-origin and browser fetch-metadata checks, an 8 KiB request-body ceiling, Unicode/control-character normalization, bounded model streaming, approved-host-only credential forwarding, a privacy-preserving per-instance rate limit, and a concurrency cap. Prompt-injection patterns are refused before model invocation; post-model checks also reject markup, unknown citations, unsupported numbers, and unsupported sensitive attribution claims.
- The complete control inventory and the required cross-instance Vercel Firewall rule are documented in [SECURITY.md](SECURITY.md). The in-code limit is intentionally described as a fallback because serverless instances do not share memory.

## Deploy to Vercel

Create a Vercel project from the GitHub repository and set **Root Directory** to `apps/evidence-explorer`. Keep the detected Next.js framework or use the checked-in `vercel.json` (`npm ci`, `npm run build`). Add `KIMI_API_KEY` as a server-side Vercel environment variable for Production and Preview; optionally add `KIMI_MODEL=kimi-k2.5`. Do not configure a custom output directory—the assistant requires the Next.js serverless route. The checked-in browser bundle is aggregate-only and is used when the Vercel build cannot read repository-level `outputs/`. Refresh it locally with `python scripts/research.py build-explorer` followed by `npm run build` before pushing a new evidence snapshot.

The deployed app includes the compact report bundle, Cesium runtime assets, a local Earth texture, and frozen country geometry. Raw FIRMS/VIIRS files, credentials, private coordinates, and source archives are not included. Static assets are served through Vercel's CDN while only the bounded chat request uses a serverless function.

## Attribution

- Boundaries: geoBoundaries `IDN-ADM1-65028918`, source OpenStreetMap / Wambacher; © OpenStreetMap contributors, ODbL 1.0.
- Earth texture: NASA Blue Marble, *Land Surface, Ocean Color and Sea Ice*.

The machine-readable attribution, frozen URLs, and hashes are in [public/geo/manifest.json](public/geo/manifest.json). See [public/globe/NOTICE.md](public/globe/NOTICE.md) for the display-geometry boundary.
