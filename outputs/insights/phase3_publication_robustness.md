# Phase 3 publication robustness audit

**Generated:** 2026-08-28T06:43:37.366334+00:00
**Scope:** Kalimantan baseline-natural-forest cells only; all analyses are associations.

## Technical summary

The frozen primary estimate remains **5.89 percentage points** (95% CI 4.52 to 7.25). Threshold, horizon, influence-screening, spatial-cluster, and alternative-estimator checks retain a positive fire-to-later-forest-loss association. However, the pre-exposure negative control is also reported below and must constrain causal interpretation.

## Attrition is material and now quantified

Of 12,178 temporally eligible sets, 5,040 (41.4%) failed complete forest/observation support and 7,138 were analyzed. The maximum absolute included-versus-excluded standardized mean difference across audited case-row variables is 1.020. Variables above |0.10|: forest_fraction, peat_extent_percent, era5_wind_max_24h_ms, era5_rootzone_soil_water_mean_72h, pre_natural_fraction.

The exclusion percentage is not hidden or treated as missing-at-random proof. Table S1 contains mean, median, and standardized differences, and the machine-readable receipt records non-exclusive exclusion reasons by year.

## Influence and alternative estimators retain the direction

After excluding the top 0.5% and 1% of matched sets by model score norm, adjusted estimates were 5.63 and 5.50 points. Conditional logistic regression produced an odds ratio of 3.46 (model-based 95% CI 3.09–3.89); it is a scale sensitivity, not a replacement for the registered risk difference. The adjusted continuous loss-share difference was 2.93 points.

## Coarser spatial clustering does not erase statistical support

| Spatial cluster | Estimate | 95% CI | p-value |
|---|---:|---:|---:|
| 25 km block + date | 5.89 pp | 4.07 to 7.70 pp | 2.12e-10 |
| 50 km block + date | 5.89 pp | 3.74 to 8.04 pp | 8.17e-08 |
| 100 km block + date | 5.89 pp | 3.27 to 8.50 pp | 1.01e-05 |

These sandwich-covariance checks address residual dependence at coarser scales, but they do not remove unmeasured spatial confounding.

## The pre-exposure negative control limits causal interpretation

The diagnostic outcome ending before the index fire produced an adjusted difference of **2.31 points** (95% CI 1.13 to 3.50; p=0.000131) across 3,915 complete sets. A positive result would indicate that fire-positive cells were already on a different land-change trajectory; a null result would reduce, but not eliminate, that concern.

On 3,453 sets with both intervals observed, the post-minus-pre diagnostic contrast was **3.08 points** (95% CI 1.53 to 4.63; p=9.95e-05). This asks whether the later difference exceeds the pre-existing difference, but it is not causal because parallel trends are not established.

## MapBiomas accounting passes internally, not against ground truth

Across 447,936 cell–horizon records, the maximum absolute difference between total forest loss and the sum of registered destination masses was 1.33e-10; 0 exceeded 1e-8. This verifies accounting consistency only. Independent classification-accuracy validation remains a limitation for the manuscript.

## Publication decision

The result is suitable for a Kalimantan association manuscript after the negative-control result, attrition comparison, and measurement limitation are carried into the abstract, results, and discussion. It is not suitable for an Indonesia-wide, global, deliberate-burning, actor-attribution, or government-performance claim.
