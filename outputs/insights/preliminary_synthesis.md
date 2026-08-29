# Evidence-Bounded Preliminary Insight -- Kalimantan Fire Research

## Bottom line

**Central human-accessibility / transformation conclusion: NI -- Not identifiable.** The primary matched-overpass analysis has not been substituted with a hotspot-count regression. Consequently, this project currently has no estimate of an accessibility effect, no estimate of a transformation effect, and no causal attribution to people, sectors, companies, or land uses.

**Environmental Phase 2 conclusion: primary interaction inconclusive.** In 14,090 exact 1:4 Kalimantan matched sets, the peat ≥50% × drier 72-hour root-zone-soil interaction OR is **0.866** (95% CI **0.692–1.084**, p=**0.209**). The interval includes 1, so the analysis does not establish that dryness strengthens or weakens the peat-associated fire-detection gradient. This is not evidence about intent, plantations, government performance, absolute ignition probability, or burned area.

**Prior-year Earth AI extension: predictive value validated, mechanism still unidentified.** Google Satellite Embedding / AlphaEarth summaries from year *t−1* improved the once-opened 2024–2025 locked matched-set prediction. The combined model reduced conditional log loss from **1.4671 to 1.2664** and increased top-1 recall from **36.8% to 46.7%** across 1,913 sets. The log-loss improvement was **0.2006** (matched-set bootstrap 95% interval **0.1712–0.2310**). Same-year embeddings and post-fire variables were rejected by the automated leakage gate. This shows additional prior-surface predictive information; it does not reveal a causal mechanism or support actor, plantation, intent, or governance attribution.

**Phase 3 fire-to-land-cover conclusion: positive temporal association in Kalimantan, with material residual-confounding evidence.** Among 7,138 complete exact 1:4 matched sets, fire-positive cells had an adjusted **+5.89 percentage-point** probability of losing at least 10% of their pre-index natural forest within one year (95% CI **+4.52 to +7.25 points**, p=**2.63e-17**). The direction persisted across registered thresholds, follow-up horizons, influence screening, alternative estimators, and coarser spatial clustering. However, 41.4% of primary-eligible sets failed support and the pre-exposure negative control was also positive (**+2.31 points**, 95% CI **+1.13 to +3.50**), indicating a pre-existing conversion trajectory or residual confounding. This establishes a mapped temporal association only in the retained Kalimantan inferential frame; the Indonesia map is descriptive context and the result does not establish deliberate ignition, actor, ownership, legality, economic motive, government failure, or causation.

## What the open evidence does show

The independent GWIS aggregate archive reports its largest July-November Kalimantan burned area in **2015** (423,577 ha). The top three reported seasons are **2015: 423,577 ha; 2019: 381,962 ha; 2023: 237,229 ha**. The NOAA CPC RONI mean for August-November was **1.66 degrees C** in 2015; that year is the strongest RONI condition in the shared GWIS span.

A deliberately countervailing observation is **2019**: RONI was near neutral (**0.01 degrees C**) while GWIS still reported **381,962 ha** in July-November. This supports a limited inference: an oceanic ENSO index alone is not a sufficient description of Kalimantan fire-season burden. It does not identify which local mechanisms account for the difference, and it is not evidence that accessibility caused fire.

The validated SiPongi descriptive archive spans 2015-2025 excluding 2024. It contains **388,435** portal records; its all-platform maximum is **2023** (188,180 records), while the matched NASA-MODIS subtotal is only **19,991**. That disparity is direct evidence of changing sensor composition in the portal series, so all-platform count changes must not be called changes in wildfire occurrence.

## What cannot yet be claimed

- The environmental association cannot be generalized to deliberate burning, road access, plantation expansion, profit, government effort, or global tropical forests.
- The original exact-overpass S-NPP human-access denominator and dated exposure remain incomplete; the completed daily environmental denominator answers a different question.
- Static peat extent is not peat moisture, depth, drainage condition, or current 2026 land cover.
- No validated dated road-opening / settlement accessibility series exists; dated OSM mapping is only a sensitivity, not construction timing.
- ERA5-Land now has a complete, content-validated 2015-2025 monthly window and a provenance receipt. Cell-specific 24/72-hour pre-event linkage is implemented and being finalized behind the complete-frame gate.
- SiPongi is a positive-record portal source and GWIS is an aggregate burned-area archive. Neither can replace the specified primary outcome.

## Data-quality decision

The SiPongi 2024 all-platform requests exposed a provider integrity failure: a Kalimantan Barat request repeatedly returned Alor records. Those responses were quarantined and excluded. The archive therefore leaves 2024 absent rather than using an incorrect response, treating it as zero, or silently filling it from another provider.

## Evidence sources and next gate

- [NOAA CPC RONI](https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt): archived locally with retrieval hash; retrospective climate context only.
- [GWIS country-profile downloads](https://gwis.jrc.ec.europa.eu/apps/country.profile/downloads): aggregate monthly burned-area context through 2024, not event geometries or 2025 data.
- [SiPongi hotspot portal](https://sipongi.gakkum.kehutanan.go.id/sebaran-titik-panas): portal-record context with preserved sensor labels and provider-quality receipts.

Phase 3's zero-budget extraction, registered model, and publication diagnostics are complete. All 38 transition-histogram chunks completed, the coordinate-free 18,664-cell × 307-field table passed validation, and all temporary coordinate-bearing cloud assets were deleted. Of 12,178 candidate primary sets, 7,138 passed complete-set and support rules. The primary +5.89-point association was robust in direction at 5%/20% thresholds, two-/three-year horizons, influence exclusions, conditional logistic and continuous-outcome alternatives, leave-one-year-out checks, and 25/50/100-km spatial clustering. The positive negative control must accompany every public interpretation. Exploratory Holm-corrected mapped destinations included non-forest natural vegetation (+4.68 points), oil palm (+0.34), other agriculture (+0.30), and other non-vegetated land (+0.86); rare destinations without adequate within-set support were not estimated. Historical access remains a separate hard gate before human-access/transformation associations can be estimated.

Shared descriptive years used for cross-source context: 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023.

## Research modules and current phase alignment

The four public claims are being kept as separate modules rather than combined into one causal story:

- **Module 1 — environmental conditions (Phase 2 complete):** the primary peat ≥50% × root-zone dryness test is inconclusive. The required fallback exclusion is materially similar; 25% and locked-test sensitivities trend lower, but cannot replace the frozen primary result. The separate prior-year AlphaEarth ablation improves prediction but remains deliberately non-causal and opaque about mechanism.
- **Module 2A — fire followed by land-cover change (Phase 3 complete):** the registered primary association is +5.89 points (95% CI +4.52 to +7.25; p=2.63e-17), with consistent threshold/horizon direction. A later oil-palm class is a small mapped transition association; it cannot identify deliberate burning, an actor, ownership, legality, or a beneficiary.
- **Module 2B / Module 3 — actor attribution and governance (Phase 4):** blocked until dated permits, ownership, intervention, budget, patrol, response, or restoration records are available. Satellite proximity is not proof of responsibility or motive.
- **Module 4 — global replication (Phase 5; descriptive preparation in Phase 0.5):** the country globe and peat/fire panel are available for context, but inferential comparison still needs a common product, period, area offset, and observation denominator.

Recommended order: archive the completed coordinate-free Phase 3 package with a permanent DOI, register any additional Phase 2 drainage/ENSO sensitivities separately, standardize Module 4 for harmonized global replication, and attempt Modules 2B/3 only after dated actor/intervention data exist. This ordering follows both scientific identifiability and data availability.
