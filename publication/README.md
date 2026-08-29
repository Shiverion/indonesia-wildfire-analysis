# Publication package

This directory contains the technical manuscript, supplement, final figures and tables, and the manifest for the compact coordinate-free analysis-data archive.

## Current readiness

The statistical analysis and publication diagnostics are complete. The remaining human/editorial fields before journal submission are verified author names, affiliations, contribution roles, acknowledgements/funding, conflict-of-interest statement, ethics statement if required by the target journal, target-journal formatting, and a permanent repository DOI.

## Build and reproduce

```powershell
python scripts\build_publication_bundle.py
python scripts\reproduce_publication.py --include-dashboard
python scripts\sanitize_public_receipts.py
```

The first command creates ignored local file `publication/release/phase3-analysis-data-v1.zip` and a tracked hash manifest. The second verifies every input, reruns Phase 3 and publication diagnostics, executes all tests, and builds the Next.js dashboard.
The final command removes workstation-specific path prefixes from tracked quality receipts before a public commit; the test suite rejects their reintroduction.

## Claim boundary

The manuscript reports a Kalimantan association. It does not claim an Indonesia-wide or global estimate, deliberate ignition, actor or beneficiary attribution, government-performance effects, legality, or profit.
