# Planetary Prediction Engine / AlphaEarth implementation plan

Registered: 2026-08-29, before any AlphaEarth feature extraction.

## Why this extension exists

The extension tests a narrow predictive question: whether a compact representation of the prior year's surface conditions adds out-of-time ranking information beyond the explicit rainfall, weather, vegetation, forest, and peat variables already used by the research.

It does **not** turn a prediction model into evidence that drought, government action, peat management, or plantations caused a fire. The registered Phase 2 association estimates and Phase 3 land-change analysis remain separate.

## Ordered implementation

1. **Freeze the question and leakage rules.** Register the target, event-year splits, one-year embedding lag, metrics, model family, and stopping rules before extraction.
2. **Audit every feature automatically.** Reject downstream variables, target components, shared target-generation paths, unavailable-at-cutoff variables, and features without source/licence provenance. Same-year AlphaEarth is a deliberate negative control and must fail.
3. **Run a bounded Earth Engine smoke test.** Extract 64 prior-year embedding dimensions for a small set of existing 1-km cells. Confirm year alignment, finite values, dimensionality, and row-wise normalization before creating a larger job.
4. **Extract only the registered cell-years.** Use one row per unique analysis cell and event year, not national raster downloads. Store the row-level file locally and keep it out of Git and the public dashboard.
5. **Fit a conservative ablation.** Compare explicit covariates, embeddings only, and a combined L2-regularized conditional scoring model. Select the penalty on spatially grouped development folds only.
6. **Evaluate once out of time.** Rehearse on 2023, freeze all choices, then evaluate 2024-2025 once. Report conditional log loss, top-1 recall, mean reciprocal rank, bootstrap uncertainty, and spatial-fold stability.
7. **Publish only if the audit passes.** A useful result is either a reproducible incremental gain or a well-supported null result. Both must retain the non-causal claim boundary.

## Data-minimization decision

The implementation will query Google Earth Engine for prior-year summaries over the existing analysis cells. It will not download Indonesia-wide 10-metre embedding rasters. For 20,684 unique cell-years, the expected coordinate-free table is only several megabytes; Earth Engine compute, not local disk, is the main constraint.

## Go/no-go gates

- The machine-readable feature audit must pass and both negative controls must be rejected.
- Every embedding year must equal event year minus one.
- Only documented 2017-2024 embeddings are eligible for the initial analysis. The currently visible 2025 layer stays excluded until separately validated.
- A matched set is removed as a unit if an embedding is incomplete.
- No new public conclusion or risk map is added before the locked-test and reproducibility checks pass.

## Registered artifacts

- `config/ppe_alphaearth_registration.json`
- `config/ppe_feature_manifest.json`
- `outputs/quality/ppe_feature_gate.json`
- AlphaEarth catalogue: https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL
- PPE paper: https://arxiv.org/abs/2608.26088

## Execution outcome

Completed on 29 August 2026. The feature gate passed all required sources and rejected both deliberate leakage controls. Earth Engine returned 20,684 unique cell-year summaries (2017-2024 embeddings for 2018-2025 opportunities) in an approximately 19.8 MB local table; no national embedding raster was downloaded. All 83 chunks completed with restart-safe local parts.

Spatially grouped development selected an L2 penalty of 0.1 for both the embedding-only and combined models. The 2023 rehearsal preserved the improvement. The 2024-2025 locked test was then opened exactly once: explicit log loss 1.4671 versus 1.2708 for embeddings only and 1.2664 combined; combined top-1 recall was 46.7% versus 36.8% explicit. The combined log-loss improvement was 0.2006 (matched-set bootstrap 95% interval 0.1712-0.2310).

This validates added predictive information, not causality or interpretability of individual embedding dimensions. The actor, intent, plantation-beneficiary, and government-performance questions remain outside this extension.
