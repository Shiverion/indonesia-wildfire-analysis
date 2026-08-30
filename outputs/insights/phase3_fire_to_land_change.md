# Phase 3 — Fire followed by land-cover change

**Status:** completed phase3 association
**Updated:** 2026-08-29T22:12:45.528830+00:00
**Inferential geography:** Kalimantan. The Indonesia-wide map is descriptive context only.
**Registered claim:** association only; not actor, intent, profit, legality, or government-performance attribution.

## What is already complete

- The locked fire-opportunity input contains **70,455 rows**, **14,091 exact 1:4 matched sets**, and **18,664 unique 1 km cells**.
- A private coordinate index resolves **18,664 cells** for cloud extraction; it is excluded from Git and the dashboard.
- The outcome definition, follow-up windows, class crosswalk, exclusion rules, estimator, uncertainty, sensitivities, and claim boundaries were frozen before extracting the annual outcome.
- Official MapBiomas Indonesia Collection 4.1 support is annual **1990–2024**. Therefore one-year follow-up is eligible through fire year 2023; 2024–2025 fires are not silently treated as having no land-cover change.

## Current gate

The primary Phase 3 model was estimated.

- Adjusted risk difference: **0.0589** (95% CI 0.0452 to 0.0725; p=2.629e-17).
- Complete matched sets: **7,138**.
- Unadjusted probability of losing at least 10% of pre-index natural forest by the one-year map: **13.74%** in fire-positive cells versus **4.40%** in matched fire-negative cells (risk ratio 3.12).
- The continuous loss-share distribution is strongly right-skewed: fire-positive mean **6.00%**, median **1.85%**, IQR 0.22%–5.69%; negative mean **1.92%**, median **0.00%**, IQR 0.00%–1.07%.
- Of **12,178** temporally eligible candidate sets, **7,138** passed the complete-set forest and observed-support gates; **5,040** were excluded rather than imputed.
- This estimate is an association between index-day fire detection and later mapped land-cover change.

## Registered robustness checks

| Analysis | Adjusted risk difference | 95% CI | Raw p | Holm p (4 secondary checks) |
|---|---:|---:|---:|---:|
| 5% loss threshold, one year | 10.78 pp | 9.07 to 12.49 pp | 4.56e-35 | 1.83e-34 |
| 20% loss threshold, one year | 2.76 pp | 1.74 to 3.77 pp | 1.02e-07 | 1.02e-07 |
| 10% loss threshold, two years | 5.93 pp | 4.26 to 7.59 pp | 3.13e-12 | 6.25e-12 |
| 10% loss threshold, three years | 6.10 pp | 4.42 to 7.78 pp | 1.19e-12 | 3.58e-12 |

All four registered threshold/horizon checks remain positive after a conservative Holm correction across the four secondary checks. The single registered primary test remains unadjusted, as frozen before outcome extraction. This reporting amendment was added after the multiplicity audit; it changes no estimate or model and does not make the association causal.

## Exploratory destination classes

Each estimable destination tests whether at least 10% of pre-index natural forest is mapped as that class one year later. Holm p-values correct across the estimable destination family.

| Destination | Status / adjusted risk difference | 95% CI | Holm p-value |
|---|---:|---:|---:|
| Non-forest natural vegetation | 4.683 pp | 3.384 to 5.982 pp | 6.4e-12 |
| Rice paddy | Not estimated: only 1 varying sets | — | — |
| Oil palm | 0.336 pp | 0.087 to 0.584 pp | 0.0164 |
| Pulpwood plantation | Not estimated: only 6 varying sets | — | — |
| Other agriculture | 0.304 pp | 0.007 to 0.601 pp | 0.0449 |
| Mining | Not estimated: only 12 varying sets | — | — |
| Urban | Not estimated: only 0 varying sets | — | — |
| Other non-vegetated | 0.862 pp | 0.468 to 1.256 pp | 5.41e-05 |
| Aquaculture | Not estimated: only 5 varying sets | — | — |
| Water | Not estimated: only 6 varying sets | — | — |

The oil-palm destination is a small but statistically supported exploratory association (+0.336 percentage points; Holm p=0.016). It does **not** establish that a fire was deliberately set for oil palm, who acted, when planting occurred, ownership, legality, or profit.

## Exact next execution

The registered Phase 3 association is complete. The next work is robustness validation and cautious cross-region replication; do not reinterpret this association as proof of actor or intent.

## Sources

- [MapBiomas Indonesia FAQ](https://landy.mapbiomas.id/en/faq) — annual maps 1990–2024, public/non-commercial access, GEE processing, and citation guidance.
- [Collection 4.1 legend](https://landy.mapbiomas.id/en/legendcode) — official class codes.
- [Collection 4.1 class descriptions](https://landy.mapbiomas.id/assets/files/Col%204.1%20-%20Legend%20Description%20EN.pdf) — forest, sawit, kebun kayu, agriculture, mining, and other definitions.

## Interpretation boundary

Even if a fire-positive cell is later mapped as oil palm, the sequence alone does not identify who burned it or why. A causal claim about deliberate conversion requires dated ownership/concession, planting, permits, enforcement, and independent validation.
