# Security policy

## Supported surface

Security fixes are applied to the current `main` branch. The public research
dashboard is served from <https://fire-research.shiverion.com> and its only
server endpoint is `POST /api/research-chat`.

## Reporting a vulnerability

Do not open a public issue for a suspected credential leak, private-coordinate
exposure, prompt-injection bypass, unrestricted model-cost path, or other
security weakness. Use the repository's **Security → Report a vulnerability**
flow to create a private GitHub Security Advisory. Include the affected path,
impact, reproduction conditions, and a safe proof that does not contain real
credentials or private coordinates.

If private reporting is unavailable, disable or redact the proof and contact
the repository owner through the GitHub profile. Please allow reasonable time
for validation and remediation before public disclosure.

## Public-data boundary

The repository intentionally publishes aggregate research outputs, public
administrative geometry, and coordinate-free analysis artifacts. It must not
contain raw SiPongi records, private analysis-cell coordinates, Earthdata/CDS
credentials, Google service-account keys, or `KIMI_API_KEY`. Source licences
and redistribution boundaries are documented in `DATA_LICENSE.md`.

Application-specific chatbot controls and the required Vercel edge rate limit
are documented in `apps/evidence-explorer/SECURITY.md`.
