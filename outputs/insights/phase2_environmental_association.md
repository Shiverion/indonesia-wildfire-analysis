# Phase 2 environmental association

**Status:** complete for the registered environmental daily-grid track. **Human-access/intent/governance status:** still not identifiable.

## Question answered

Within exact daily 1:4 matched sets of baseline-natural-forest cells in Kalimantan, does the peat-associated fire-detection gradient change when pre-event environmental conditions are more adverse? The primary test is peat extent ≥50% interacted with drier ERA5-Land root-zone soil over the prior 72 hours.

This is a within-matched-set association for detectable first-observed fire, not absolute ignition probability, burned area, peat condition, deliberate burning, plantation expansion, or government performance.

## Primary result

- Interaction odds ratio: **0.866** per one development-period SD increase in dryness.
- 95% CI: **0.692–1.084**; two-sided p = **0.209**.
- Interpretation: The interval includes no interaction, so this analysis does not establish that drier root-zone soil changes the peat-associated detection-odds gradient.
- Support: 14,090 matched sets; 2,572 contain both ≥50% and <50% peat cells.

The interaction odds ratio compares how the odds change with dryness in cells above versus below the peat threshold. It is not the overall odds ratio for all peatland and does not show that every mapped peat cell burned.

## Mandatory robustness checks

| Check | Interaction OR | 95% CI | p | Matched sets |
|---|---:|---:|---:|---:|
| Primary, all registered days | 0.866 | 0.692–1.084 | 0.209 | 14,090 |
| Exclude fallback-history dates | 0.864 | 0.690–1.081 | 0.201 | 13,907 |
| Peat threshold ≥25% | 0.801 | 0.650–0.987 | 0.038 | 14,090 |
| Peat threshold ≥75% | 1.040 | 0.846–1.278 | 0.711 | 14,090 |
| Locked 2024–2025 only | 0.654 | 0.443–0.965 | 0.033 | 1,913 |

Threshold and fallback runs are robustness checks. They cannot be selected after the fact to replace the registered ≥50% primary result.

## Other peat-condition interactions

| Condition (one adverse SD) | Interaction OR | 95% CI | raw p | Holm p |
|---|---:|---:|---:|---:|
| higher VPD over the prior 72 h | 1.051 | 0.830–1.332 | 0.679 | 1.000 |
| higher maximum wind over the prior 24 h | 0.832 | 0.651–1.063 | 0.142 | 0.425 |
| lower pre-fire EVI | 0.967 | 0.841–1.112 | 0.637 | 1.000 |

## Held-out prediction check

The frozen model was fitted only on 2018–2022, rehearsed on 2023, then evaluated on the locked 2024–2025 sets.

| Split | Conditional log loss | Uniform log loss | Improvement | Top-1 recall | MRR |
|---|---:|---:|---:|---:|---:|
| 2023 rehearsal | 1.422 | 1.609 | 0.188 | 0.414 | 0.638 |
| 2024–2025 locked test | 1.468 | 1.609 | 0.141 | 0.370 | 0.605 |

Top-5 recall is exactly 1 by construction because the stored design contains one case among five sampled cells; it is therefore not used as evidence of predictive skill.

## Data and uncertainty

The analysis contains 70,450 rows: 14,090 cases and 56,360 controls in 14,090 exact matched sets. Uncertainty is clustered by recurring cell and acquisition date. The Phase 1B input lock was valid at fit time.

## Boundaries

- Odds ratios are within matched sets and describe detectable fire association, not absolute fire probability or burned area.
- A non-significant result is inconclusive, not proof of no effect.
- Static peat extent is not peat moisture, drainage state, peat depth, or current land cover.
- No result from this track identifies deliberate burning, plantation expansion, profit, government effort, or human-access causality.
- Global generalization requires a separately harmonized observation-denominator analysis.

## Next work

Phase 3 may prepare the fire-to-land-change association, while Phase 2 can add separately registered drainage and ENSO interaction sensitivities.
