# Supplementary methods and results

## S1. Frozen analysis decisions

The machine-readable registration is `config/phase3_registration.json`. It was frozen before annual outcome extraction. The primary threshold, one-year horizon, support criteria, covariates, clustering dimensions, multiplicity families, and claim boundaries were not selected after inspecting Phase 3 outcomes.

## S2. Analysis flow

| Stage | Matched sets | Rows | Meaning |
|---|---:|---:|---|
| Locked daily 1:4 opportunities, 2015–2025 | 14,091 | 70,455 | Full event frame; later years remain useful for future outcomes |
| Primary-eligible event years, 2015–2023 | 12,178 | 60,890 | MapBiomas one-year follow-up exists |
| Complete forest/observation support | 7,138 | 35,690 | Frozen primary analysis population |

Exclusion reasons are non-exclusive: 5,031 sets had <70% immediately pre-index natural forest; 11 had <95% pre-map observation, 11 had <95% follow-up observation, and one contained a negative CHIRPS missing sentinel. No transition fraction was non-finite or outside its allowed range.

## S3. Selection comparison

`tables/table_s1_included_vs_excluded.csv` contains included and excluded means, medians, and standardized mean differences. Absolute SMDs above 0.10 occurred for baseline forest fraction (0.674), peat extent (0.111), 24-hour wind (0.128), 72-hour root-zone soil water (0.179), and immediately pre-index natural-forest fraction (1.020). These differences make the analysis-population boundary substantive.

## S4. Registered analyses

`tables/table1_primary_and_registered_sensitivities.csv` is the canonical table for the primary, threshold, and horizon results. `tables/table2_exploratory_destinations.csv` records both estimated and support-gated destination classes. Failure to pass support was not recoded as a null finding.

## S5. Publication diagnostics

- Conditional logistic sensitivity: odds ratio 3.465 (model-based 95% CI 3.09–3.89). Matched sets without within-set outcome variation do not contribute to the conditional likelihood.
- Continuous outcome: adjusted +2.934 percentage points of pre-index forest lost.
- Influence: removing the top 0.5% and 1% of matched sets by score norm yielded +5.626 and +5.503 points.
- Leave-one-year-out: +4.130 to +6.959 points.
- Spatial covariance: estimates remained +5.888 points; 95% intervals widened from +4.071–+7.704 points at 25 km to +3.274–+8.502 at 100 km.
- Internal transition accounting: across 447,936 cell–horizon pairs, the maximum absolute loss-minus-destination residual was 1.33×10^-10 and none exceeded 10^-8. This is an accounting check, not external map validation.

## S6. Negative-control design

For an event in year *t*, the negative control used the registered one-year transition field indexed at *t*−2, spanning maps *t*−3 to *t*−1 and ending before the index fire year. Event years 2017–2023 contributed. The adjusted negative-control estimate was +2.313 points (95% CI +1.128 to +3.499; p=0.000131; 3,915 sets).

On 3,453 sets observed in both intervals, the binary post-minus-pre estimate was +3.082 points (95% CI +1.530 to +4.634; p=9.95×10^-5). The continuous version was +1.147 points (95% CI +0.777 to +1.516). Neither is a causal difference-in-differences estimator because parallel trends, no anticipation, and absence of time-varying confounding were not established.

## S7. Year-specific results

`tables/table_s2_year_specific.csv` contains all estimates and uncertainty. Individual intervals included zero in 2017, 2018, 2021, and 2022. These tests are descriptive heterogeneity diagnostics and are not the registered primary family.

## S8. Reproduction

1. Install `requirements-analysis.txt` in a clean Python environment.
2. Extract `phase3-analysis-data-v1.zip` at the repository root, or retain the two local ignored input tables.
3. Run `python scripts/reproduce_publication.py --include-dashboard`.
4. Confirm `outputs/quality/publication_reproduction.json` has `status: passed` and all input hashes match `publication/data/manifest.json`.

No Earth Engine, CDS, or Earthdata credential is required once the compact analysis inputs exist. Re-running raw acquisition is a separate provenance reconstruction, not a prerequisite for verifying the statistical result.
