# Enhanced Research Method: Human Accessibility, Land Transformation, and Tropical Fire

**Status:** methodological redesign; no outcome has been analyzed here. This is not registration-ready until the dataset manifest, exact MapBiomas class crosswalk, historical-access and peat asset IDs, final calibrated event-linker values, complete covariate/product/temporal-support table, model formulas, grid and bootstrap definitions, random seeds, validation samples, selection gates, and power code are attached and hashed.  
**Prepared:** 20 August 2026  
**Primary study area:** Kalimantan  
**Primary study period:** complete years only; 2015-2025 for measurement development, with confirmatory association estimation beginning after the frozen calibration period

## Executive assessment

The central question is scientifically strong and deliberately avoids starting from an accusation. The original plan also gets several important choices right: a regular grid rather than administrative averages, separation of occurrence from burned area, antecedent climate controls, peat and drought interactions, spatial validation, temporal ordering of tree-cover loss, and explicit falsification.

The present plan is nevertheless too broad to function as a confirmatory research protocol. It currently combines:

1. **association**: where satellite-detectable fires occur;
2. **prediction**: whether human variables improve forecasts; and
3. **causation**: whether a change in access or land use causes fire risk to change.

Those are different questions and require different estimands, models, assumptions, and claims. Proximity to a road or plantation does not identify who lit a fire, matching does not remove unmeasured confounding, and a satellite hotspot is not proof of a wildfire or an ignition.

The defensible primary conclusion is therefore:

> **Pre-existing accessibility and antecedent land transformation are, or are not, meaningfully associated with the rate of surveillance-bounded first-observed landscape-fire onset per processed S-NPP observation opportunity in baseline forest landscapes, after prespecified adjustment for environmental conditions measured before first observation.**

A causal conclusion should be reserved for a separate analysis of a defined, dated intervention, such as a verified road opening, that passes pre-trend, overlap, spillover, measurement, and placebo tests.

## What should be retained

- Use gridded spatial units rather than regency-level averages.
- Keep fire occurrence separate from burned area and other event characteristics.
- Use antecedent rainfall, drought, soil moisture, wind, peat, vegetation, and terrain.
- Test accessibility-by-drought and accessibility-by-drained-peat interactions.
- Use spatially blocked and temporally held-out validation.
- Treat Sumatra and Papua as external transportability tests, not as interchangeable controls.
- Predefine findings that would weaken or contradict the hypothesis.
- Keep machine learning as a predictive benchmark, not the evidentiary core.

## The most important corrections

| Problem in the original plan | Why it matters | Required correction |
|---|---|---|
| “Human influence” is one broad concept | Roads, settlements, canals, conversion, plantations, mines, and concessions are different exposures and mechanisms | Use two co-primary exposure domains—baseline accessibility and antecedent transformation—and treat industries as secondary mechanism analyses |
| Raw FIRMS points are treated as fires and first detections as ignitions | A satellite sees thermal anomalies at overpass times; it can miss, split, or merge events | Use science-quality fire masks, model valid observation opportunities, and call the location/time **first observed**, not ignition |
| Current OSM or land-cover data can be applied backward to 2015 | This leaks future information and can make new access look older than it was | Use dated snapshots or explicitly limit the interpretation to present-day cross-sectional accessibility |
| Climate rasters are upsampled to 1 km | ERA5-Land and CHIRPS do not acquire 1 km climate information; interpolation creates false precision | Preserve native climate support, propagate it to cells, and cluster uncertainty at the native weather-grid scale |
| All vegetation and transformation variables are called controls | Some are consequences or mediators of access; controlling for them changes the estimand | Draw a causal diagram and report a baseline-adjusted model separately from a mediator-adjusted model |
| Fire severity is compared only among observed fires | Conditioning on fire occurrence can create selection/collider bias | Report event-conditional comparisons as descriptive and also model unconditional fire burden, including zeros |
| 50-100 km border matching is treated as quasi-causal | Borders may follow rivers or ridges and bundle many policy, economic, and mapping differences | Use a narrow, harmonized geographic-discontinuity design only if continuity tests pass |
| Many thresholds, models, regions, and outcomes are optional | Researcher degrees of freedom can manufacture a favorable narrative | Freeze one primary analysis and place all alternatives in a published robustness ladder |
| 2026 is a complete holdout | As of 20 August 2026 it is incomplete, and some burned-area products have months of latency | Use 2026 only as date-matched year-to-date monitoring; use it as a full test only after completion and data stabilization |

## 1. Research questions and estimands

### 1.1 Confirmatory association question

Among cells that were natural forest landscapes before follow-up, how does the rate of **surveillance-bounded first-observed satellite-detectable landscape-fire event onset** vary with:

- pre-existing human accessibility; and
- land transformation during the preceding complete years,

after adjustment for prespecified environmental conditions measured before first observation and satellite observation history?

The primary estimands are standardized incidence-density ratios for detected event onset at a processed S-NPP overpass for:

- accessibility at its 90th versus 10th percentile within common support; and
- 20% versus 0% of a cell transformed during the preceding three complete years.

These are adjusted associations, not a generic causal “human effect.”

### 1.2 Prediction question

Does adding the frozen human-exposure block improve spatially and temporally held-out prediction beyond an environmental-only model?

Prediction will be assessed with conditional log loss and top-5 recall within held-out overpass risk sets. A separate complete 5 km cell-week model may report absolute calibration and Brier score, but it cannot change the association conclusion. Feature importance or SHAP values will not be treated as causal evidence.

### 1.3 Causal questions

Run these only if the necessary exposure dates and design checks are available:

- What is the effect of a verified new road opening on subsequent fire incidence within a specified distance?
- What is the effect of a clearly dated, prior-fire-free forest conversion on subsequent unconditional fire burden?
- What is the local effect of the jurisdictional and management package at the Kalimantan-Malaysia border?

Each intervention gets its own estimand. None identifies a particular company, industry, or individual ignition actor.

### 1.4 Event-characteristics question

Among detected events, do burned area, satellite-observed persistence, and overpass-level FRP differ between more and less human-modified landscapes?

This question is two-sided. The plausible pattern is more onsets near access but smaller conditional burned patches because of fuel fragmentation or faster suppression; the opposite is also possible, particularly on drained peat.

## 2. Scope, target population, and time split

### Primary geography

Use **Kalimantan only** for the confirmatory model. This keeps the first study within one national data regime and permits use of annual Indonesian land-cover products.

Use Sabah, Sarawak, and Brunei as a predeclared external replication with harmonized cross-border datasets. Use Sumatra and Papua as later transportability tests. Do not call them “controls.” South Papua should be analyzed separately only with an ecological rationale because savanna, wetland, customary burning, and frontier dynamics differ from humid Borneo forest.

Amazon and Congo analyses would be new ecological studies. Siberia is outside the tropical-forest hypothesis and should be removed from this protocol.

### Target population

Create the grid in **EPSG:6933**. Anchor every primary 1 km cell, 25 km matching supercell, and 50 km bootstrap block at integer multiples of its resolution from projected coordinate origin `(0, 0)` so the lattices nest and cannot be shifted after seeing results. Assign a boundary cell to Kalimantan by its centroid, retain its actual land and fixed-forest areas, and publish fractional-boundary assignment as a sensitivity analysis. Retain cells with at least **70% natural-forest cover in 2014** for the primary analysis. Once admitted, cells remain in the cohort even after transformation; otherwise transformed cells disappear from the sample and bias the study.

Predeclare sensitivity cohorts at 50% and 30% baseline forest, plus a secondary full-landscape analysis. Use 0.5, 2, and 5 km grids and half-cell origin shifts to test the modifiable-areal-unit problem. Use real land/forest area in every cell rather than assuming all coastal cells contain 1 km² of eligible land.

### Time split

- **2015-2017:** measurement calibration only—event linking, observation masks, exposure-map validation, and effect-size/power simulation. Do not use these years to select a favorable human-fire coefficient.
- **2018-2022:** model development.
- **2023:** tuning and analysis-pipeline rehearsal.
- **2024-2025:** the sole locked retrospective test for the two central occurrence contrasts **and all eight confirmatory secondary burden/event contrasts**.
- **2026:** occurrence-only monitoring unless a validated 2025 land-cover source is frozen. MapBiomas 4.1 ends in 2024, so the same three-complete-year transformation exposure is not yet available for 2026. Year-to-date estimates are descriptive unless one cutoff and a sequential-inference rule are registered in advance. NASA has also announced that Suomi-NPP product delivery will cease on **1 November 2026**; therefore, truncate any S-NPP-only monitoring at the last verified complete delivery or begin a separately calibrated NOAA-20/NOAA-21 bridge. Never splice platforms without an overlap calibration. A full burned-area analysis must also wait for product completion and latency ([NASA transition notice](https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026)).

Before unlocking the test, record file hashes, code commit, data-manifest versions, and an access log. If any outcome-dependent 2024-2025 fire map, event-linker check, missingness summary, convergence result, exposure-outcome map, coefficient, or diagnostic has informed an analytical choice, those years are not untouched. In that case, label the work a registered analysis plan and reserve 2027 for genuine prospective confirmation. After unlocking, pooled 2018-2025 estimates may be reported only as secondary estimates; they cannot replace the frozen 2024-2025 classification. The 2026 result is not required for that classification.

Where a later module uses the term **fire season**, freeze it as 1 July through 30 November UTC. Calendar-year and June-through-December estimates are sensitivity analyses; they cannot replace the registered seasonal estimate.

## 3. Unit of analysis and data architecture

Use a **1 km matched case-overpass risk-set design** for the central association and conditional prediction, plus a complete coarser cell-week panel for descriptive rates and absolute prediction.

Maintain four linked products:

1. **Weekly observation summary:** stream paired VNP14IMG.002 fire-mask and VNP03IMG.002 geolocation swaths into cell-week summaries; do not store the billions of possible cell × overpass rows. Retain processed baseline-forest area by unique orbit, view geometry, day/night, and quality counts for surveillance audits and descriptive rates.
2. **Sparse detection/event table:** retain fire-positive overpass records, group them within an overpass, and link them across overpasses.
3. **Primary risk-set table:** before reading outcomes, tile the study area into fixed 25 km × 25 km equal-area supercells with a frozen origin. For every cell-overpass, find its most recent earlier S-NPP overpass with no fire pixel and at least 50% of its fixed forest footprint processed. Require that qualifying negative look to be no more than 72 hours old and assign it to a frozen interval band: 0-24, >24-48, or >48-72 hours. For each unique current orbit/overpass × supercell × prior-negative band containing at least one eligible new onset, create one matched set. Collapse two onsets allocated to the same 1 km cell-overpass to one binary case and retain their multiplicity separately. Include every distinct case cell and **every eligible noncase cell** from that frame and interval band; the 25 km supercell bounds the computational size, so no outcome-triggered control subsampling is needed. Store the complete frame and case count.
4. **Burned-patch table:** burned-area patches linked probabilistically to one or more active-fire events.

Case and noncase eligibility must be identical immediately before the current overpass: membership in the frozen baseline-forest cohort, positive current processed area, a qualifying prior negative look within 72 hours, and no active cell-level refractory state. A case additionally has a qualifying in-forest newly allocated onset; a noncase has no current fire pixel. Track refractory state sequentially: a cell enters it when a linked event is first observed in that cell and remains in it through seven complete days after that cell's latest fire-positive detection. A later detection extends the state prospectively; the event's eventual union footprint must never retroactively disqualify an earlier control. A newly allocated event whose onset cell was already refractory immediately before detection is not a primary case and is retained for recurrence sensitivity analysis. Calibrate the seven-day rule using event-linking accuracy only and report frozen 3- and 14-day sensitivities.

A noncase may reappear in later overpasses and may later become a case, but appears only once within a matched set; recurrent risk-set analyses require cell-clustered uncertainty ([recurrent-event methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC7394959/)). Treat simultaneous case cells as tied failures in the one set and use an exact tied conditional likelihood. This design conditions cases and noncases on the identical observable opportunity and avoids outcome-dependent weekly look thresholds. The primary conditional association does not estimate absolute population risk; absolute descriptive rates and calibration require the separate complete 5 km surveillance panel.

Process ordinary rasters in Earth Engine or another tiled raster engine, export grid summaries to partitioned Parquet, and query with DuckDB or Polars. Standard science-quality VIIRS swaths require an explicit LP DAAC/LAADS processing path because they are not a native Earth Engine collection. Use GeoPandas for bounded vector operations, not the complete panel.

## 4. Fire measurement

### Primary occurrence source

Use the **standard/science-quality S-NPP VIIRS 375 m active-fire product**, not near-real-time point downloads, for the primary historical series. NASA advises latency-insensitive scientific studies to favor the non-NRT archive because NRT can have coverage and geolocation limitations ([VIIRS Collection 2 user guide](https://www.earthdata.nasa.gov/s3fs-public/2024-07/VIIRS_C2_AF-375m_User_Guide_1.0.pdf)).

Use S-NPP alone in the locked 2012-2025 primary series so that the number of platforms does not step upward over time. NASA's scheduled end of S-NPP product delivery on 1 November 2026 does not threaten the retrospective 2024-2025 test, but it rules out an unqualified S-NPP-only operational series beyond that point. A multi-platform S-NPP/NOAA-20/NOAA-21 bridge requires an outcome-blind overlap calibration with platform, local time, observation opportunity, detection sensitivity, and duplicate handling explicitly represented; it is a separately frozen monitoring extension, not a silent continuation of the primary series.

### Observation opportunity

FIRMS fire points alone cannot distinguish “no fire” from “not observable.” Pair VNP14IMG.002 with VNP03IMG.002 so non-fire, cloud, water, missing, and fire pixels can all be geolocated. In the primary observation summary, count mask class 5 and classes 7-9 as processed land/fire; handle classes 0-4 and 6 explicitly; remove residual bow-tie duplicates using the relevant QA flag; and aggregate the processed fraction of **fixed 2014 baseline-forest area** by unique orbit. Canopy attenuation is not a fire-mask class and belongs in the separate detectability analysis.

For the central association, each matched set contains only cells with positive processed fixed-forest area at the exact S-NPP overpass, the same prior-negative interval band, and the identical pre-overpass eligibility rules. Include a frozen spline of the number of qualifying negative looks during the preceding seven days. Report 48-hour, 96-hour, and no-prior-negative-bound sensitivities; they cannot replace the 72-hour primary. Its estimand is the relative rate of a **detected, surveillance-bounded first-observed onset per processed S-NPP opportunity**, not latent fire incidence or true ignition. Because the earlier negative look need only process 50% of the fixed forest footprint, this is a cell-level surveillance bound, not proof that the eventual fire pixel was fire-free or that ignition occurred within 72 hours.

As a surveillance audit, model the probability that fixed baseline forest is processed in scheduled S-NPP overpasses, using no-onset periods so fire-generated smoke is not treated as a cause of surveillance. If the standardized P90-versus-P10 accessibility ratio is outside [0.95, 1.05], report observation weighting and a tipping analysis in the complete-panel/descriptive model. Same-overpass matching controls opportunity in the central model, but it cannot correct canopy-dependent sensitivity to an actual fire; that requires the independent burn-scar validation and bias bounds.

### Detection filtering

- Primary: nominal- and high-confidence land active-fire pixels.
- Sensitivities: high only; all confidence classes.
- Remove active volcanoes, gas flares, industrial thermal sources, and persistent stationary anomalies with a frozen mask.
- Analyze day and night separately as a sensitivity check.
- Classify event land cover using imagery whose complete temporal support ends before the qualifying prior negative look, not a composite that overlaps or follows first detection.

Use the term **satellite-detectable landscape fire** unless a fire type is independently classified. Agricultural burning is not automatically wildfire.

### Event construction

Do not set 1 km and 24 hours as an unvalidated universal rule. Use this deterministic calibration protocol:

1. after bow-tie removal, group fire pixels within an overpass by 8-neighbor adjacency in the native swath array;
2. across overpasses, evaluate the 12 frozen combinations of nearest-edge link radius `{0.75, 1.5, 3 km}` and maximum gap `{12, 24, 48, 72 h}`. Terminate a candidate link when an intervening S-NPP overpass validly processes at least 50% of the preceding cluster footprint and observes no fire there; allow a gap when that support is not observable;
3. create 2015-2017 reference labels from a stratified random sample across accessibility, canopy, peat, region, apparent size, and cloud conditions, with two blinded reviewers and adjudication;
4. choose the combination with the largest macro-averaged event-pair F1 across the accessibility × canopy × peat strata, subject to precision and recall of at least 0.70 in every principal canopy × peat group. For candidates within 0.01 F1, choose the smaller radius and then the shorter gap;
5. insert the selected numeric values, labeled sample hash, adjudication log, and linker-code hash into the registration before any 2024-2025 access. Until that is done, the protocol is exploratory; and
6. report all 12 combinations as the complete specification ensemble, never a favorable subset.

Call the initial record the **first-observed event location and time**, never the true ignition. An event enters the primary forest-landscape outcome only when at least one first-overpass fire-pixel center falls inside the fixed 2014 natural-forest footprint; later conversion does not remove that footprint. Its allocated case cell must also satisfy every pre-overpass cohort, prior-negative, processed-area, and refractory rule applied to controls. Allocate each event once: assign the onset to the 1 km cell containing the geometric medoid of its in-footprint first-overpass fire-pixel centers, break exact ties by the lowest stable cell ID, and retain the complete event footprint and positional uncertainty. A sensitivity analysis fractionally allocates the onset across in-footprint first-overpass cells with weights summing to one and jitters positions within geolocation uncertainty. Use active-fire-presence cell-week as a robustness outcome; it measures presence, not onset, because spread can populate later cells and weeks.

### Burned area

Use burned area as a separate outcome, not as interchangeable evidence with active-fire detections.

- MCD64A1 Collection 6.1: use Burn Date, Uncertainty, QA, and FirstDay/LastDay. Derive unmapped status from Burn Date and QA rather than inventing a separate unmapped layer ([official user guide](https://lpdaac.usgs.gov/documents/1006/MCD64_User_Guide_V61.pdf)).
- VNP64A1: a standard nominal-500 m output derived from 750 m VIIRS inputs and available from 2012. The expected FIRMS latency is approximately five months, but the manifest must record the actual latest available month ([NASA description](https://wiki.earthdata.nasa.gov/spaces/FIRMS/blog/2025/09/08/461800781/New%2BVIIRS%2BGlobal%2BBurned%2BArea%2BProduct%2BAdded%2Bto%2BFIRMS)).
- MapBiomas Fire: an Indonesia-specific alternative with monthly and annual burned-area maps through 2024.
- Sentinel-2/Landsat: a **stratified random validation sample**, not visually selected showcase cases.

Moderate-resolution burned-area products omit some small or obscured burns and should not be treated as ground truth. A Global Fire Atlas-style method can characterize patches, but its published performance is strongest for larger fires and its minimum size is inherited from the underlying product ([Andela et al., 2019](https://essd.copernicus.org/articles/11/529/2019/)).

## 5. Event characteristics and terminology

Do not use one word—“severity”—for several different constructs.

| Construct | Primary measure | Interpretation and limitation |
|---|---|---|
| Fire burden | burned area/fraction, including zero when no fire occurs | Most policy-relevant unconditional outcome |
| Radiative output | peak and median event-overpass FRP | Instantaneous satellite-observed radiant power, not ecological severity |
| Persistence | number of distinct valid overpasses with fire; interval-censored duration | First-to-last detection is only a lower bound |
| Ecological burn severity | Sentinel/Landsat dNBR or RBR in validation sample | Vegetation impact, distinct from FRP and burned area |
| Recurrence | number of fire-positive seasons within a fixed cell | Must account for observation opportunity and changing land cover |

VIIRS 375 m pixels can share an FRP retrieval based on coarser retrieval support, and FRP can be null in difficult cases. Aggregate at event-overpass level according to the product guide; do not treat each row-level FRP as an independent measurement. Do not call a raw sum “cumulative FRP.” Estimating fire-radiative energy requires explicit temporal interpolation and uncertainty bounds.

Duration is interval-censored by overpasses, cloud, smoke, and study boundaries. A single detection does not imply a zero-duration fire.

## 6. Human-exposure construction

### Co-primary exposure A: baseline accessibility

Freeze an outcome-blind, interpretable accessibility score based on data dated no later than the start of follow-up:

- road proximity and road class;
- settlement proximity;
- navigable-river access;
- slope-adjusted travel time.

The proposed primary score is fixed as:

\[
A_i=\tfrac{1}{2}z[-\log(1+d_{road,i})]+\tfrac{1}{2}z[-\log(1+d_{settlement,i})],
\]

where distances are kilometres from the 1 km cell centroid to features verified as present by 31 December 2014. Standardize both components using the 2018-2022 eligible development cohort; higher values mean greater accessibility. A missing component makes the cell ineligible for the primary accessibility analysis rather than changing the weights. Freeze the P10/P90 contrast from this development distribution. Report road and settlement components separately as secondary estimates. A slope-adjusted travel-time surface including navigable rivers is a predeclared sensitivity analysis, not an interchangeable primary exposure.

Do not learn weights from fire outcomes, SHAP, an autoencoder, or post-outcome data.

Because this score is fixed at baseline, its estimand is the long-run association with **2014 accessibility**. It must not be described as current accessibility in later years. If reliable dated network snapshots exist, annual accessibility and verified openings belong in secondary longitudinal analyses.

Current OSM data must not be projected backward. Use dated OSM snapshots, verified imagery-derived opening dates, or official historical road data. Missing mapped roads/canals are **unknown**, not confirmed absence. Audit completeness in a stratified imagery sample and propagate positional uncertainty.

### Co-primary exposure B: antecedent transformation

Define transformation as the fraction of fixed 2014 baseline natural forest converted during the previous three complete years to a frozen MapBiomas anthropogenic-class crosswalk. The crosswalk must list exact collection-4.1 class codes before the test archive is opened. Use annual MapBiomas Indonesia transitions as the primary source and alternative products as sensitivity checks. Same-year conversion is excluded from the confirmatory exposure because its temporal order relative to first observation is ambiguous. Also retain the cumulative fraction converted from **2015 through `t−4` using the identical crosswalk**; set this older-history fraction to zero when the interval is empty, but never when an annual map is missing. Enter it as a frozen hurdle—any older transformation plus a linear fraction among cells with any. If any required annual class is unavailable, that cell-year is ineligible for the transformation model rather than imputed. A cell with 0% **recent** transformation may already be historically transformed and must not be described as intact.

Separate:

- conversion to oil palm;
- conversion to pulpwood plantation;
- mining footprint;
- other cropland or built land;
- canopy loss without a verified destination class.

Hansen Global Forest Change is a sensitivity source. Its `loss` variable is stand-replacement tree-cover loss, which can include fire, harvest, or rotation; it is not automatically deforestation or human conversion ([current catalog](https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2025_v1_13)). Flag prior burn overlap and repeat analyses after excluding transformations that may be fire-induced.

### Secondary mechanism variables

- canal proximity and density;
- observed oil-palm, pulpwood, logging, and mining footprints;
- protected status and enforcement proxies;
- concessions, stored separately from observed operations;
- population and built-up area;
- previous fire history.

A concession boundary is an administrative designation, not proof that the concession holder operated at the location or caused a fire.

### “Remote forest”

Do not make a single remote label that mixes access, intactness, and lack of recent loss. Those are separate dimensions and may lie on the same causal pathway.

Use continuous access measures in the primary model. For communication, predeclare one remote category, such as the lowest accessibility decile among baseline-forest cells with common-support matches. Treat 5/10/20 km definitions as sensitivity analyses, not three opportunities to select a favorable result.

## 7. Environmental variables and temporal ordering

For exogenous meteorology, use the case overpass's UTC acquisition time as one common cutoff for every member of its matched set. A source interval must **finish** before the cutoff; a nominal timestamp alone is insufficient. For vegetation, fuel, and soil-moisture variables that an already-burning but not-yet-detected fire could alter, use the earliest qualifying prior-negative timestamp among tied cases as the common cutoff. Apply the same cutoffs to all controls. As an onset-uncertainty sensitivity, end every weather and fuel window at that earlier prior-negative cutoff.

Freeze this compact covariate-and-sensitivity dictionary; exact asset IDs and code hashes remain required in the manifest:

| Construct | Frozen primary definition | Model role |
|---|---|---|
| Short rainfall | ERA5-Land hourly total precipitation summed over the 168 complete hours before current-overpass cutoff | Accessibility, transformation, environmental, joint |
| Antecedent rainfall | CHIRPS v3 pentadal precipitation anomaly over complete pentads in the preceding 30 days, relative to a 1991-2020 calendar-pentad climatology | Accessibility, transformation, environmental, joint |
| Drought severity | Negative standardized CHIRPS v3 90-day precipitation anomaly; higher values mean drier conditions | Accessibility, transformation, environmental, joint; registered interaction index |
| Long-term climate | Separate 1991-2020 mean annual CHIRPS v3 precipitation and mean annual ERA5-Land vapor-pressure-deficit normals, each entered with the frozen P10/P50/P90 natural spline | All models |
| Atmospheric dryness | Seven-day mean of daily maximum vapor-pressure deficit derived from ERA5-Land 2 m temperature and dew point | Accessibility, transformation, environmental, joint |
| Wind | Seven-day mean of daily maximum 10 m wind magnitude derived from ERA5-Land u/v components | Accessibility, transformation, environmental, joint |
| Root-zone moisture | Depth-weighted ERA5-Land soil-water layers 1-3, converted to a 1991-2020 day-of-year percentile and ending before the prior-negative cutoff | Environmental and joint only; excluded from total-accessibility and transformation models |
| Prefire live vegetation (possible mediator) | Most recent QA-accepted **MOD13Q1.061 EVI** 250 m 16-day composite whose complete composite interval ends before the prior-negative cutoff; freeze the DetailedQA/SummaryQA acceptance mask | Environmental, predictive, and joint mediator-adjusted models; excluded from total-accessibility and current transformation models |
| Live-fuel-moisture sensitivity | HLSL30.002 and HLSS30.002 surface-reflectance NDMI, summarized over QA-clear observations in the preceding 30 complete days and ending before the prior-negative cutoff | Sensitivity/prediction only; enforce coverage gates and retain sensor indicator |
| Baseline forest | Frozen MapBiomas Indonesia 2014 natural-forest class and fraction | All models |
| Baseline canopy/detectability | MOD44B.061 2014 percent tree cover and its uncertainty | Detection validation, stratification, and bias bounds; not automatically a substantive risk adjustment |
| Peat | Binary presence from one frozen national peat-soil extent map; depth and alternate maps are sensitivity analyses | All models; drainage remains separate |
| Terrain/ecology | Copernicus DEM GLO-30 elevation and slope plus one frozen terrestrial-ecoregion layer | All models |
| Lightning | NASA LIS/OTD Reprocessed Flash Climatology annual mean flash rate at its native 0.1° scale | Baseline adjustment only; it does not identify event-time lightning ignition |
| ENSO state | NOAA CPC ERSSTv6 Relative Oceanic Niño Index (RONI), continuous °C; latest complete three-month season ending before the cutoff; freeze raw file, retrieval time, version, and hash | Main effect is not estimable in exact-overpass matched sets; complete 5 km panel sensitivity and exploratory exposure × RONI interaction |
| Prior fire | For accessibility, processed-opportunity-standardized 2012-2014 S-NPP onset history; for transformation in year `t`, the common `t−6` through `t−4` history preceding the `t−3` through `t−1` exposure window | Estimand-specific confounding adjustment |
| Observation history | View geometry, current processed-area spline, prior-negative interval band, prior-seven-day qualifying-look count, and day/night | All occurrence models |

### Vegetation and fuel are explicit, but their model role depends on the estimand

Vegetation is not one interchangeable control. The study now separates four quantities:

1. **Baseline vegetation identity:** MapBiomas Indonesia Collection 4.1 class and within-cell fraction in 2014 define the cohort and baseline forest type. Freeze the candidate natural-forest codes—forest formation `3`, mangrove `5`, and peat-swamp forest `76`—against the exact exported asset legend before registration.
2. **Prefire greenness:** MOD13Q1.061 EVI is the primary dynamic vegetation proxy. EVI is a greenness proxy, not a direct measurement of combustible fuel mass or fuel moisture. Use only pixels passing the frozen QA rule and only a composite whose entire support predates the qualifying prior-negative look ([MOD13Q1.061](https://doi.org/10.5067/MODIS/MOD13Q1.061)).
3. **Prefire moisture sensitivity:** derive NDMI from open Harmonized Landsat-Sentinel surface reflectance over the prior 30 complete days. This provides finer spatial information but more cloud-dependent missingness, so it remains a gated sensitivity/prediction feature rather than a co-primary adjustment ([HLS Landsat](https://doi.org/10.5067/HLS/HLSL30.002); [HLS Sentinel-2](https://doi.org/10.5067/HLS/HLSS30.002)).
4. **Canopy and ecological response:** use 2014 MOD44B percent tree cover chiefly to quantify canopy-dependent VIIRS detection. Post-fire dNBR/RBR is an outcome and must never be used as a prefire predictor ([MOD44B.061](https://doi.org/10.5067/MODIS/MOD44B.061)).

Include lagged current EVI in the environmental/predictive model and in the joint mediator-adjusted model. Exclude post-2014 EVI/NDMI from the co-primary total-accessibility model because accessibility may affect degradation, vegetation condition, and then fire. For the transformation estimand, add only a frozen **pre-exposure** vegetation history—dry-season median EVI during `t−6` through `t−4`—as a sensitivity adjustment; exclude vegetation measured during or after the `t−3` through `t−1` transformation window. This separation is deliberate causal discipline, not an omission.

### ENSO / El Niño placement

Use **ENSO state or intensity**, not “El Niño wave”; an oceanic Kelvin wave is a different phenomenon and would require a different dataset. Freeze NOAA CPC's openly downloadable ERSSTv6 **Relative Oceanic Niño Index (RONI)** as the primary retrospective index, with legacy ONI as a named sensitivity. RONI is a three-month Niño-3.4 anomaly relative to tropical-mean SST; CPC warns that recent values may revise for up to two months ([RONI definition and table](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/); [machine-readable series](https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt)).

An ENSO main effect is mathematically non-identifiable in the exact-overpass conditional model: every case and control in a matched risk set has the same acquisition time and therefore the same RONI value, so it cancels with the matched-set intercept. This is why it was not an ordinary row in the co-primary formula. Local rainfall, drought, VPD, and wind remain useful because they vary spatially within a risk set. Predeclare only these secondary ENSO analyses:

- In a separate complete 5 km cell-month climate panel, assign the latest RONI season whose full three-month interval ended before the month. Use cell effects, month-of-year seasonal terms, and one frozen long-run trend; do not use exact year-month effects, which would absorb RONI. A total ENSO-fire association model excludes downstream local rainfall, VPD, drought, and soil moisture; a model containing both RONI and those mediators is predictive/residual and must not be called the total ENSO effect.
- Estimate accessibility × RONI and transformation × RONI only as exploratory effect modification. RONI varies over time, not across cells, so thousands of cells do not create thousands of ENSO replicates; use contiguous three-month temporal blocks plus spatial blocks and report the number of distinct ENSO episodes.
- A frozen final/revised RONI series supports retrospective explanation only. Do not claim real-time forecast performance unless archived data vintages prove that every index value was actually available at its forecast cutoff.

Do not add alternative versions of rainfall, VPD, wind, drought, ENSO, or lightning to the confirmatory formula after viewing results. Those products belong in the named sensitivity inventory. The climatological lightning term means the central result remains a human-accessibility association, not a human-versus-natural ignition decomposition ([NASA lightning climatology](https://data.nasa.gov/dataset/lis-otd-reprocessed-flash-climatology)).

ERA5-Land is natively about 9 km, despite delivery on a 0.1° grid, so 1 km resampling does not create 1 km information ([Copernicus catalog](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview)). CHIRPS v3 is 0.05° and is fundamentally pentadal/monthly; its daily variants are downscaled from those periods ([CHIRPS v3 documentation](https://www.chc.ucsb.edu/data/chirps3)). Preserve source resolution and cluster or model uncertainty accordingly.

Dynamic World is a cloud-masked, per-Sentinel-2-scene probabilistic product available from June 2015; its tree class does not distinguish primary forest from plantations ([official catalog](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1)). ESA WorldCover supplies reference maps for 2020 and 2021, not an annual 2016-2026 time series ([2021 catalog](https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200)). Use MapBiomas Indonesia Collection 4.1 for the primary Indonesian annual land-cover history; it covers 1990-2024 and includes natural-to-anthropogenic transitions ([method document](https://landy.mapbiomas.id/assets/files/ATBD%20Mapbiomas%20ID%20Col%204.1%20EN.pdf)).

Peat maps have material spatial and depth uncertainty. Use a frozen national peat-soil/extent layer for peat presence. Use Indonesia's 1:250,000 Peat Hydrological Units (KHG) separately for hydrological and management context; a KHG boundary is not itself a peat-presence or depth mask ([official national KHG reference](https://pkgppkl.menlhk.go.id/v0/en/kepmen-no-129-tahun-2017-penetapan-peta-kesatuan-hidrologis-gambut-nasional/)). Compare alternative extent/depth maps rather than pretending peat depth is known at 1 km. Peat and canal sources must be harmonized before any international border interpretation.

### Data-access and licence audit

**Bottom line:** the primary fire, wind, rainfall, vegetation, topography, lightning, and ENSO stack can be obtained without buying data. The complete study is **not yet demonstrably fully open**, because the historically dated human-infrastructure and mechanism layers have not all passed an access, provenance, and redistribution audit. “Free to download,” “openly licensed,” and “available through a free research account” are recorded separately.

| Data group | Access classification | Account, licence, and practical constraint |
|---|---|---|
| S-NPP VIIRS active fire/geolocation; MODIS/VIIRS burned area; MOD13Q1 EVI; MOD44B canopy; HLS; LIS/OTD | Open/no purchase | Direct DAAC workflows normally require a free NASA Earthdata Login; cite product DOI/version/access date. NASA data policy supports open use, and MODIS LP DAAC products state no downstream use or redistribution restriction ([NASA data guidance](https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance); [Earthdata Login](https://urs.earthdata.nasa.gov/documentation/what_do_i_need_to_know)). Compute and storage are not free merely because the data are. |
| ERA5-Land wind, temperature/dewpoint, rainfall, and soil water | Open/no purchase, **CC-BY** | Free Climate Data Store registration, licence acceptance, and API credentials. Preserve its approximately 9 km native support; it is modeled reanalysis, not 1 km observed wind ([ERA5-Land licence/catalog](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=documentation)). |
| CHIRPS v3 rainfall | Open; anonymous direct download; public-domain dedication plus **CC BY 4.0** | Cite the repository DOI and access date; its native support is 0.05° and the pentadal/monthly product is primary ([CHIRPS v3](https://www.chc.ucsb.edu/data/chirps3)). |
| NOAA CPC RONI/ONI | Open; anonymous text download | Freeze index name, version, retrieval time, raw bytes, and SHA-256. Recent RONI values can revise for two months ([NOAA CPC RONI](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/)). |
| MapBiomas Indonesia Collection 4.1 | Open for this academic/public-interest study, **CC-BY-SA** | The terms page permits copying and redistribution with collection/version/access-date attribution, while the FAQ describes free access for non-commercial or public-interest use. Preserve share-alike obligations, record both pages, and obtain written clarification before commercial reuse or release of a combined commercial database ([Indonesia terms](https://landy.mapbiomas.id/en/termsofuse); [Indonesia FAQ](https://landy.mapbiomas.id/en/faq)). |
| Dynamic World; ESA WorldCover; Hansen Global Forest Change | Open product licences, chiefly **CC BY 4.0** | Dynamic World/Hansen access through Earth Engine requires a registered project and the platform's research/commercial rules; WorldCover also has anonymous AWS/Zenodo routes. These are sensitivities, not substitutes for MapBiomas annual Indonesian classes ([Dynamic World](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1); [WorldCover access](https://esa-worldcover.org/en/data-access); [Hansen GFC](https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2025_v1_13)). |
| Copernicus DEM GLO-30 | Free under a product-specific licence | CDSE registration and licence acceptance are required for current access, and the prescribed source notice must accompany redistribution. It is a static digital **surface** model, not a bare-earth or time-varying elevation measurement ([Copernicus DEM](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM)). |
| OpenStreetMap roads/settlements | Open, **ODbL** | Attribution and database share-alike obligations apply. A feature's first OSM appearance is not proof of its construction date, so OSM history alone cannot identify road openings ([OSM copyright/licence](https://www.openstreetmap.org/copyright)). |
| Dated official roads, concessions, mines, plantations/ownership, canals/drainage, peat depth, incident records, and commercial very-high-resolution validation imagery | **Not guaranteed open; unresolved gate** | Availability, temporal completeness, access agreements, and redistribution rights vary by custodian. Each asset needs written terms in the manifest. If an authoritative dated road series is unavailable, drop the road-opening causal module; if a restricted validation source is used, publish sampling code and permissible labels/aggregates rather than redistributing imagery. |

The manifest must therefore contain, for every asset: provider, exact asset ID/DOI, version/collection, temporal and spatial support, retrieval URL and timestamp, account/terms accepted, licence/SPDX-like label where possible, required attribution, raw-file checksum, whether raw and derived data may be redistributed, expected update latency, and an open replacement. Release code and download scripts for all sources; redistribute raw inputs only when their terms allow it. A licence-compatible public analysis table, or a documented restricted-data recipe plus synthetic fixture, is a precondition for calling the study reproducible.

## 8. Causal diagram and adjustment sets

Create and publish a directed acyclic graph before fitting the confirmatory model. At minimum, distinguish:

- baseline confounders: terrain, peat origin, long-term climate, ecoregion, baseline forest, historical settlement patterns;
- time-varying first-detection conditions: antecedent drought, soil moisture, wind, fuels;
- mediators: road-induced conversion, drainage, vegetation degradation, plantations;
- outcomes: detectable event onset and unconditional fire burden;
- observation process: cloud, canopy, sensor platform, view geometry, valid looks.

Classify every covariate separately for the accessibility and transformation estimands; a variable may be a confounder for one and a mediator for the other. Report four models with different interpretations:

1. **Environmental baseline model:** no human variables; prediction benchmark.
2. **Co-primary accessibility model:** baseline accessibility + the frozen baseline forest, peat, terrain/ecology, long-term climate, 2012-2014 prior-fire, lightning-climatology, rain/drought/VPD/wind, and observation terms. Exclude subsequent transformation, drainage, current vegetation, plantation footprint, and root-zone soil moisture because they may mediate accessibility.
3. **Co-primary transformation model:** antecedent transformation + cumulative older transformation through `t−4` + 2014 accessibility + the same immutable/baseline terms + the common `t−6` through `t−4` fire-history window + current rain/drought/VPD/wind + lightning climatology + observation terms. Apply this definition to transformed and 0%-recent-transformation cells alike. Exclude post-transformation drainage, vegetation, and soil moisture from this model.
4. **Joint mediator-adjusted model:** accessibility + transformation + current vegetation, plantation footprint, drainage, and soil moisture. This secondary model partitions remaining/direct-like conditional associations; it does not estimate the total accessibility gradient.

If the human coefficient changes after mediator adjustment, do not call one model right and the other wrong; they answer different questions.

## 9. Statistical analysis

### Frozen primary-choice summary

| Item | Primary choice | Objective fallback consequence |
|---|---|---|
| Population | Kalimantan cells with ≥70% natural forest in 2014 | If overlap fails, classify the affected contrast not identifiable; do not substitute a broader cohort |
| Outcome | Newly allocated first-observed S-NPP event onset at an exact processed 1 km cell-overpass opportunity | Active-fire presence is sensitivity only |
| Surveillance | Identical S-NPP orbit/overpass and 0-24/24-48/48-72-hour prior-negative band; positive current processed area for cases and controls | An onset without a qualifying prior negative or eligible matched frame is described but contributes no conditional estimate |
| Accessibility | Frozen equal-weight 2014 road/settlement score | Missing either component excludes the cell from this co-primary analysis |
| Transformation | Fraction of 2014 forest converted during t−3 through t−1 | Exact MapBiomas codes frozen before holdout; unavailable years are not imputed |
| Model | Conditional logistic incidence-density model, stratified by matched risk set | Failure to converge makes the 1 km primary analysis not estimable; the complete 5 km panel is reported separately and cannot replace it |
| Risk set | All tied case cells + every eligible noncase cell in the same matched frame | No control subsampling or inverse-probability weights; a set with no eligible noncase contributes no estimate |
| Local comparison | Exact orbit/overpass × frozen 25 km supercell × prior-negative band | No post-result change of stratum size or band; coarser spatial strata are sensitivity analyses |
| Uncertainty | 2,000-replicate whole-50 km spatial-block bootstrap retaining both locked years, max-\|t\| simultaneous intervals | Fewer than 30 case-bearing blocks in either year or fewer than 1,900 successful replicates makes central inference underpowered/not estimable as applicable |
| Decision estimand | Adjusted incidence-density ratio at the locked exposure contrasts | Non-estimable contrast is reported as not identifiable; absolute risk is outside this design |
| Test period | Untouched 2024-2025 only | If previously inspected, reserve 2027 and relabel this plan |

### Primary occurrence model

Each orbit/overpass × supercell × prior-negative band containing one or more eligible onset cells defines one incidence-density risk set. Fit a conditional logistic model stratified by matched set, using the exact conditional likelihood for tied case cells; the set-specific intercept is conditioned out. Comparing each failure with the complete eligible local risk set estimates a conditional incidence-density ratio rather than a population probability; the design is the full-risk-set analogue of incidence-density sampling ([methodological evidence](https://pmc.ncbi.nlm.nih.gov/articles/PMC1740694/)). Use:

- a natural cubic spline of log current processed hectares within the fixed 2014 forest footprint, with development-period P25/P50/P75 knots, rather than assuming a coefficient-one proportional area offset; standardize every contrast to the frozen development-period median processed area;
- a natural cubic spline for accessibility with internal knots at P25/P50/P75 and boundary knots at P5/P95 of the 2018-2022 development exposure distribution;
- a transformation hurdle comprising any transformation plus a linear fraction among transformed cells, from which the frozen 20%-versus-0% contrast is standardized;
- the separately frozen older-transformation hurdle from 2015 through `t−4` in the transformation model;
- three-knot natural splines for continuous weather terms, with P10/P50/P90 knots fixed from 2015-2023 predictor distributions without inspecting 2024-2025 outcomes;
- one common pre-overpass covariate cutoff for every member of a set, the exact prior-negative band, and a frozen spline of prior-seven-day qualifying-look count;
- the exact matched-set stratum, which conditions on orbit, acquisition time, broad weather, and 25 km local context, plus prespecified within-set baseline/ecological covariates that still vary;
- the two estimand-specific co-primary models defined above rather than mutual adjustment in one model;
- the prespecified accessibility × drought interaction in the conditional model; the drained-peat interaction is estimated only on the absolute-burden scale in the complete 5 km panel; and
- the complete eligible noncase frame, with no control-sampling weights.

The single decision measure is an adjusted **incidence-density ratio (IDR)** for detected, surveillance-bounded first-observed onset at a processed cell-overpass opportunity standardized to the frozen processed-area reference, comparing A(P90) with A(P10) or transformation 20% with 0%. For nonlinear terms, average the prespecified within-risk-set rate-ratio contrast over the locked 2024-2025 risk-set covariate distribution. Report the model coefficient scale and the standardized contrast. Do not report absolute risks or risk differences from this case-triggered sample: they are not identified because times and strata with no cases have zero sampling probability. Absolute calibration belongs only to the complete 5 km surveillance panel.

Assess support separately by risk-set year from each complete eligible frame. An accessibility set supports the locked contrast only if its observed access range contains both frozen A(P10) and A(P90); a transformation set supports its contrast only if it contains at least one 0% cell and one cell at or above 20%. Use the intersection of sets supporting **both** contrasts as the frozen central local-overlap risk-set population and standardize both co-primary IDRs there, so their combined classification refers to one population rather than two convenient subsets. Component-specific estimates in their broader supported sets are secondary. If the common central population is not represented in at least 30 case-bearing 50 km blocks in each locked year, the combined hypothesis is **not identifiable**; if only a component-specific population fails that gate, classify that component accordingly. Do not select a nearer contrast after seeing outcomes. Publish the excluded-set fraction and covariate differences so the loss of transportability is visible.

Freeze the two mechanism contrasts as well. For drought, report `[accessibility IDR at drought P90] / [accessibility IDR at drought P10]`, where each accessibility IDR compares A(P90) with A(P10) and high drought-index values mean drier conditions. For drained peat, report the difference-in-differences in standardized burned hectares per 100 QA-valid baseline-forest hectares: the A(P90)-versus-A(P10) mean difference on drained peat minus the same mean difference on undrained peat in the complete 5 km panel. The latter is mediator-conditioned and descriptive, not the total accessibility association.

Static baseline accessibility is a between-cell association. It cannot be identified by cell fixed effects. Time-varying transformation can additionally be tested within cells with cell and time effects.

### Dependence and inference

Millions of rows do not imply millions of independent observations. The primary uncertainty procedure is a 2,000-replicate spatial block bootstrap that samples whole frozen 50 km blocks and retains **both locked years**, every risk set in the sampled block, all tied cases, and all eligible noncases—including cells reused across overpasses and overlapping source frames. Require at least 30 case-bearing blocks in each year and at least 1,900 replicates in which both co-primary models converge; otherwise label the affected inference underpowered or not estimable rather than change the estimator. Use the synchronized bootstrap max-|t| distribution to construct familywise simultaneous intervals for the two co-primary IDRs. Report 25 and 100 km blocks as sensitivity analyses. With only two locked years, temporal-cluster uncertainty is intrinsically weak; show year-specific estimates and longer 2018-2025 temporal robustness without presenting either as a replacement. Run Moran's I on out-of-set residual diagnostics; Moran's I and generic spatial-lag models do not cure confounding.

The 25 km fixed strata make the static-accessibility estimate a local between-cell comparison. Add a prespecified smooth of coordinates within major ecoregions and report a quantitative spatial-confounding sensitivity analysis; the result remains associational even when residual autocorrelation is small.

For prediction, use buffered spatial folds, leave-year-out tests, and leave-region-out replication. Keep every matched set wholly within one fold; random row splitting is prohibited because it leaks neighboring landscapes and shared risk sets. The primary predictive score is conditional log-loss skill relative to the environmental baseline, with top-5 case recall reported alongside it. A predeclared material gain is at least 5% lower mean conditional log loss with a conditional calibration slope between 0.80 and 1.20 on the locked test. A separate complete 5 km cell-week model may report Brier score and absolute calibration, but neither may change the association classification. Spatial validation can sharply reduce apparently excellent ecological-model performance ([example evidence](https://www.nature.com/articles/s41467-020-18321-y)).

### Machine-learning benchmark

XGBoost may detect nonlinear thresholds, but it remains secondary. Evaluate it on the same locked folds and outcomes. Report calibration and predictive gain over the environmental baseline. Use SHAP only to describe the fitted predictor; correlated variables and SHAP values do not identify causal contribution.

## 10. Severity and burden analysis

Keep unconditional burden and event-conditional characteristics as two distinct designs.

### Unconditional burned-area burden

The confirmatory secondary burden estimand is the rate of MCD64A1 QA-valid burned hectares per QA-valid hectare of the fixed 2014 baseline-forest footprint in a complete **5 km cell-month panel**, whether or not a VIIRS event was linked. Set a pixel to zero only when the product validly classifies it as unburned; retain unmapped pixels as missing. In the primary burden analysis, exclude pixel-months marked as having a shortened mapping period or whose FirstDay/LastDay do not span the complete month, and require at least 80% of the cell's fixed forest footprint to remain QA-valid; a sensitivity analysis uses QA-valid hectare-days and reports the resulting full-month-equivalent denominator. Fit a prespecified Tweedie log-link model with log full-period QA-valid hectares as the offset and variance power selected using 2015-2017 calibration data only. Standardize separate accessibility and transformation models to the same P90-versus-P10 and 20%-versus-0% contrasts and their corresponding adjustment sets from Section 8. VNP64A1 and MapBiomas Fire are product sensitivities, not interchangeable primaries. If the Tweedie model fails its calibration/convergence simulation gate, report this secondary estimand as not estimable rather than choose a favorable family after unlocking the test.

### Event-conditional characteristics

For each detected event, freeze exposures and covariates at its first-observed time. Evaluate:

1. MCD64A1-mapped burned hectares with a frozen two-part model: logistic regression for any mapped scar and a log-link Gamma model for positive area, combined into one standardized mean contrast. Define adequate coverage using the fixed first-overpass in-forest footprint plus a 500 m buffer: at least 90% must be QA-valid and its mapping interval must span the 14-day event window. With adequate coverage and no linked scar, record zero **mapped** hectares; inadequate coverage or ambiguous linkage is missing. This distinguishes a product-valid zero from proof that no ground burn occurred;
2. the number of fire-positive S-NPP overpasses out of valid opportunities in the fixed 14 days beginning at first observation, using a beta-binomial model. Freeze the spatial support to the in-forest first-overpass footprint, count an overpass as valid when at least 80% of that support is processed, and require at least three valid opportunities; report 2- and 4-opportunity threshold sensitivities; and
3. log peak event-overpass FRP within that same 14-day window, using a prespecified robust Gaussian model. For each event-overpass, sum the product's supplied fractional FRP across unique, non-bow-tie linked 375 m fire pixels, then take the maximum overpass total. Do not replace each fractional value by its parent 750 m retrieval. Treat zero/null retrievals caused by saturation or insufficient background as missing/censored, not true zero.

For each outcome, estimate the accessibility P90-versus-P10 and transformation 20%-versus-0% contrasts in separate estimand-specific models: **six event-characteristic contrasts**. Together with the two unconditional-burden contrasts, these are the eight tests in the secondary fire-characteristics family. The confirmatory versions use the same estimand-specific adjustment logic as Section 8: adjust for pre-onset weather, immutable baseline forest/ecology, view geometry, day/night, and the relevant observation denominator, but exclude current EVI/NDMI from the accessibility contrast and vegetation measured during or after the transformation exposure window from the transformation contrast because those may be mediators. Report a separately labeled mediator-adjusted severity model that adds QA-valid prefire EVI/NDMI; it answers a different, direct-like conditional question. Inadequate coverage or ambiguous linkage is missing; adequate coverage with no mapped scar is zero mapped area. Publish vegetation coverage, linkage, and FRP-retrieval rates by exposure with selection-bias bounds.

Median FRP, interval-censored duration beyond 14 days, recurrence, and sampled dNBR/RBR are exploratory. Conditional comparisons answer “among detected and measurable events,” not “what would the same fire have done under a different accessibility state.” Keep every event-characteristic direction two-sided.

### Secondary-family decision protocol

Express the two burden results as standardized burned-area rate ratios, event mapped area and persistence as standardized mean ratios, and peak FRP as a geometric-mean ratio. Use the same whole-50 km, both-year, 2,000-replicate bootstrap for all eight contrasts. The smallest meaningful ratio is frozen at 1.25, with log-symmetric lower boundary 0.80; this wider band acknowledges greater product and selection error than the central occurrence outcome. For each contrast, classify: not estimable if a measurement/support gate fails; meaningfully higher if its Holm-adjusted simultaneous lower bound exceeds 1.25; meaningfully lower if its upper bound is below 0.80; negligible only if both Holm-adjusted one-sided equivalence tests reject for `[0.80, 1.25]`; directionally different if the adjusted interval excludes 1 but not a meaningful boundary; otherwise inconclusive. Never infer “no difference” from a nonsignificant test.

Before testing an event-characteristic contrast, require at least 80% usable events within every peat × locked-exposure group—accessibility quintile for the access contrast, and 0% versus at least 20% for transformation—and require the ratio of usable fractions between its contrasted groups to lie in `[0.80, 1.25]`. Also require at least 30 contributing 50 km blocks in each locked year and the prespecified model-convergence gate. Failure makes that contrast not estimable for confirmatory purposes; publish descriptive data and selection-bias bounds. These gates apply separately to mapped area, persistence, and FRP and cannot be waived because another outcome has better coverage.

## 11. Quasi-experimental modules

### Verified road-opening event study

Define treatment as the first year annual imagery verifies a new road segment that brings a baseline-forest cell within 5 km. Exclude the transition fire season, use not-yet-treated cells as controls, never use already-treated controls, and estimate group-time average treatment effects with the Callaway-Sant'Anna staggered-adoption estimator. Freeze imagery evidence rules and comparison cohorts in a separate module registration.

Estimate three pre-opening and three post-opening fire seasons. Do not use failure to reject a lead as evidence of parallel trends. Require simultaneous pre-period incidence-rate ratios to fall inside [0.833, 1.20], adequate overlap, stable measurement, and no documented concurrent access-related shock. If the lead bounds or other gates fail, report the pattern without a causal claim. Modern staggered difference-in-differences methods require explicit parallel-trend assumptions and careful comparison groups ([methods discussion](https://www.journals.uchicago.edu/doi/full/10.1086/711509)). If dated roads are unavailable, do not run this module.

### Dated land-transformation module

The central protocol does not make a causal transformation claim. Any later causal module must receive its own registration that freezes one treatment regime, a prior-fire-free eligibility rule applied before treatment, the covariate history, one g-formula or weighting estimator, weight truncation, positivity gates, and spillover rule. A simple lagged regression remains an association.

### Border module

The estimand is the local effect of the **jurisdictional/management bundle**, not oil palm, roads, or regulation separately. Use one harmonized dataset on both sides, border-segment effects, signed distance, smooth trends on both sides, and narrow 5/10/20 km bandwidths. Exclude or separately analyze border segments following sharp rivers, ridges, or ecological transitions.

Test continuity of immutable geography and harmonized measurement: terrain, geology/peat extent, hydrology, long-run climate, and observation opportunity. Do **not** use settlement, roads, vegetation, or pre-period fire as pretreatment balance variables because the jurisdiction predates the satellite record; their discontinuities may be part of the jurisdictional bundle. Run pseudo-borders. Geographic regression discontinuity has stronger spatial assumptions than ordinary threshold RD, and naive distance-to-border approaches can fail ([Keele and Titiunik](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1903253)). If geographic or measurement continuity fails, present a matched border association, not a causal result.

## 12. Bold, falsifiable predictions

These are predictions to risk being wrong about, not assumptions to force into a model.

1. **Occurrence:** both co-primary IDR point estimates will be at least 1.50. This is a bold prediction; the inferential support threshold remains the simultaneous lower bound above 1.20.
2. **Drought gating:** the accessibility contrast will be materially attenuated in wet/fuel-saturated periods and larger in the driest decile.
3. **Drained peat:** accessibility and drained peat will interact super-additively on the absolute-burden scale in the complete 5 km panel; the conditional risk-set model cannot identify an absolute-risk interaction.
4. **Timing:** a verified road-opening effect, if real, will appear mainly in the first two subsequent dry seasons and not in the three pre-opening seasons.
5. **Frequency versus conditional size:** accessible landscapes may have more event onsets but not larger conditional burned patches. The severity analysis remains two-sided.
6. **Measurement robustness:** classify the result as detectability-robust only if meaningful-positive support persists after bias correction assuming remote-event sensitivity is 0.50 times accessible-event sensitivity. If the correction loses meaningful support at any remote/access sensitivity ratio of 0.50 or greater, label it measurement-sensitive and report the tipping ratio.

## 13. Assumption register

| Assumption | Why it is bold | Diagnostic | Consequence if it fails |
|---|---|---|---|
| Historical access is measured without severe differential omission | Remote roads and settlements are less likely to be mapped | Stratified imagery audit; require recall ≥0.80 in every main region/access stratum and remote/access recall ratio ≥0.80 | Accessibility component is not identifiable in the failed domain |
| Event linking measures onset consistently | Cloud gaps can split one peat fire and synchronized field burns can merge | Stratified burn-scar review; require precision and recall ≥0.70 in each principal canopy × peat group | First-observed onset is not validated; report active-fire presence descriptively |
| Conditional fire detectability is comparable enough to bound | Canopy, cloud, smoke, fire size, and platform affect detection | Stratified burn-scar validation; processed-observation ratio; probabilistic bias analysis down to remote/access sensitivity 0.50 | Apply correction and report tipping ratio; if sensitivity cannot be bounded, classify the access result not identifiable |
| Exposures precede outcomes | Fire can cause canopy loss and can coincide with access expansion | Dated imagery, prior-fire exclusion, lead/lag checks | Do not interpret loss as antecedent conversion |
| Sufficient common support exists | Truly remote intact forest may have no comparable accessible counterpart | Overlap plots, balance statistics, trimming | Restrict the target population and state the restriction |
| No important unmeasured confounding for the adjusted association | Enforcement, customary burning, suppression, and economics are incompletely observed | Negative controls and quantitative sensitivity analysis | Keep interpretation associational |
| Parallel counterfactual trends hold for road openings | Roads are built where change is already underway | Event-study leads, matched pre-trends, placebo dates | No causal road-opening claim |
| Spillovers are limited or modeled | Fires, roads, smoke, and economic activity cross cell and border boundaries | Buffer exclusions, cross-boundary-event checks, distance-to-treatment analysis | Interpret as a wider-area policy/exposure effect or abandon local ATT |
| Grid and event definitions do not manufacture the result | Spatial aggregation can merge or split both exposures and outcomes | Shifted grids, multiple scales, clustering ensemble | Apply the separately reported effect-scale-instability label and show the full range |

Regression cannot prove these assumptions. The study should display which ones are supported, doubtful, or failed.

## 14. Decision rules that preserve neutrality

Use the synchronized whole-50 km, both-year bootstrap to obtain familywise inference for the two co-primary log IDRs. Construct simultaneous two-sided 95% intervals from the 95th percentile of the replicate maximum absolute studentized statistic. For equivalence, calculate four one-sided bootstrap tests—the lower and upper boundary null for each component—and apply Holm's procedure across all four at familywise α = .05; a component is equivalent only when both adjusted boundary tests reject. The smallest meaningful increase is IDR 1.20; its reciprocal, 0.833, is the symmetric meaningful decrease. IDR 1.50 remains a bold prediction, not an inferential cutoff. The equivalence interval `[0.833, 1.20]` is a scientific convention that must be defended before registration; it is deliberately symmetric on the log scale. Do not derive absolute risks or risk differences from the central risk-set sample. Any policy threshold for the separate full-panel burden analysis must come from a documented utility/cost decision analysis.

First classify each co-primary exposure, applying the rows in this order:

| Code | Component classification | Frozen rule |
|---|---|---|
| NI | Not identifiable | A measurement, eligibility, support, minimum-block, or model-estimation gate fails; no statistical fallback may replace the locked contrast |
| MP | Meaningfully positive | Familywise simultaneous 95% lower bound is greater than 1.20 |
| MN | Meaningfully negative | Familywise simultaneous 95% upper bound is less than 0.833 |
| EQ | Negligible/equivalent | Both Holm-adjusted boundary tests establish equivalence inside `[0.833, 1.20]`, even if the IDR differs statistically from 1 |
| DP | Directionally positive, magnitude unresolved | Simultaneous lower bound is greater than 1, but neither MP nor EQ is established |
| DN | Directionally negative, magnitude unresolved | Simultaneous upper bound is less than 1, but neither MN nor EQ is established |
| UR | Statistically unresolved | None of the rules above is met |

Then combine the unordered pair of component codes by the first matching row. These rows are mutually exclusive and exhaustive:

| Central classification | Frozen rule |
|---|---|
| Not identifiable | Either code is NI; still report the other component separately |
| Full support | Pair `{MP, MP}` |
| Mixed evidence | One code is in `{MP, DP}` and the other is in `{MN, DN}` |
| Partial support | Exactly one code is MP and the other is in `{EQ, DP, UR}` |
| Joint negligibility | Pair `{EQ, EQ}` |
| Central contradiction | Pair `{MN, MN}` |
| Component contradiction | One code is MN and the other is in `{EQ, DN, UR}` |
| Directional support | One code is DP and the other is in `{DP, EQ, UR}` |
| Directional contradiction | One code is DN and the other is in `{DN, EQ, UR}` |
| Inconclusive | Pair `{EQ, UR}` or `{UR, UR}` |

“Not statistically significant” is not evidence of no effect. Negligibility requires equivalence. Prediction is a separate estimand and cannot upgrade or downgrade these association categories. A null, contradiction, failed replication, or failed identification assumption is a valid publishable endpoint.

Sensitivity analyses receive separate labels rather than acting as a significance veto. Flag **effect-scale instability** when a core alternative changes the estimate by more than `|log(IDR_alt) - log(IDR_primary)| > log(1.10)`. The core alternatives are high-confidence-only fires, a half-cell grid shift, the 2 km grid, the frozen alternate historical-access source, and detection-bias correction at a 0.50 remote/access sensitivity ratio. Report the complete range and tipping points even when sampling variation moves an interval across a decision boundary.

## 15. Diagnostics, mechanism tests, placebos, and bias analyses

Run and publish all of the following regardless of direction:

- **Lead-pattern diagnostic:** estimate three future-road/conversion leads and compare simultaneous lead IDRs with [0.833, 1.20]. A failed bound can reflect anticipation or endogenous placement; it blocks a causal claim but does not erase the descriptive association.
- **Road pre-trend gate:** the three registered pre-treatment seasons described in the road module.
- **Placebo dates and geometries:** assign pseudo-opening dates and shifted road geometries that preserve broad density and terrain.
- **Observation negative control:** test whether accessibility predicts the probability of a valid clear view.
- **Non-burnable/static-source test:** estimate the apparent access gradient over water, known thermal sources, and other invalid fire classes.
- **Wet-period mechanism test:** estimate the registered wet-versus-dry interaction; this is an effect-modification hypothesis, not a universal placebo.
- **Prior-fire sensitivity:** separately remove recurrent-fire cells and transformations overlapping earlier burns.
- **Detection-bias bounds:** vary remote-versus-accessible detection sensitivity over a predeclared plausible range.
- **Grid/event sensitivity:** 0.5/1/2/5 km grids, shifted origins, confidence filters, and the complete clustering ensemble.
- **Alternative products:** road, land cover, transformation, peat, climate, and burned-area alternatives.
- **Spatial dependence:** 25/50/100 km blocks and buffered validation folds.
- **Transportability:** leave-year-out, leave-region-out, and harmonized Malaysian-Borneo replication.
- **Border placebos:** pseudo-borders and baseline-covariate continuity.
- **Specification curve:** show all predeclared defensible specifications rather than selecting the most favorable one.

## 16. Multiplicity, missingness, and power

### Multiplicity

- **Central family (2 tests):** accessibility and transformation IDRs; synchronized max-|t| familywise two-sided α = .05 plus the four-boundary Holm TOST specified above.
- **Mechanism family (2 tests):** the drought ratio-of-IDRs and drained-peat absolute-burden difference-in-differences. Use the same synchronized 50 km block draws across the risk-set and full-panel datasets and a max-|t| test on their studentized statistics at familywise two-sided α = .05. The meaningful mechanism scales are a ratio-of-IDRs of 1.25 and an absolute interaction of 0.5 burned hectares per 100 QA-valid forest hectares per month; their opposites are 0.80 and −0.5.
- **Event/burden family (8 tests):** the frozen accessibility and transformation contrasts for unconditional QA-valid burned-area burden, event-conditional burned area, 14-day fire-positive-overpass persistence, and 14-day peak event-overpass FRP. Apply Holm at familywise two-sided α = .05 across all eight and obtain adjusted confidence bounds by inversion. For equivalence, apply Holm across all 16 one-sided boundary tests; both adjusted boundary tests must reject for a contrast to be called negligible.
- **Prediction (1 locked comparison):** conditional log-loss skill of the human-plus-environment model versus the environmental model, with the 5% gain and conditional-calibration rule defined above. It does not enter hypothesis classification. Full-panel Brier score is descriptive.
- **Exploratory inventory:** median FRP, interval-censored duration, recurrence, dNBR, RBR, accessibility components, industry-specific variables, alternate remote labels, regional heterogeneity, XGBoost, and SHAP. If inferential summaries are shown, use Benjamini-Hochberg q = .10. These analyses cannot change the central classification.
- **Replication:** 2026 monitoring and Malaysian-Borneo, Sumatra, or Papua analyses require their own frozen contrasts and are reported separately.

### Missingness and measurement error

- Never convert “not mapped” to zero.
- Never impute fire outcomes.
- Map missingness by year, region, forest type, peat, accessibility, and outcome.
- In the central design, apply the identical positive-current-area, ≤72-hour prior-negative, prior-negative-band, and refractory rules to every case and control; do not introduce a post-result weekly look threshold. In the complete 5 km surveillance panel, use its separately frozen observation-coverage rule and report prespecified coverage sensitivities.
- Use multiple imputation only for covariates with defensible predictors, and publish complete-case results.
- Downgrade a region-year rather than silently substitute whichever source gives a stronger result.
- Pin dataset versions, access dates, checksums, coordinate systems, time zones, resampling rules, and Earth Engine scripts.

### Power

Simulate the exact two-year locked analysis using only the calibration period. Include rare-event prevalence, prior-negative eligibility, missing observation opportunities, event-linking error, spatial correlation, reused controls, overlapping sampled risk sets, and the effective number of spatial blocks. Require at least 90% probability that **both** co-primary simultaneous lower bounds exceed 1.20 when both true IDRs are 1.50, and at least 90% probability that **both** Holm-adjusted equivalence decisions pass when both true IDRs are 1.00. For the mechanism family, require at least 80% probability that both familywise tests reject under a true drought ratio-of-IDRs of 1.25 and a true peat interaction of 0.5 burned hectares per 100 QA-valid hectares per month. For the eight-test family, require at least 80% probability that all eight Holm-adjusted tests reject when every true ratio is 1.50, and at least 80% probability that all eight equivalence decisions pass when every true ratio is 1.00.

If a criterion is not met, label that family underpowered and its eventual non-decisive result inconclusive; do not widen the scope or change thresholds after looking at the result merely to obtain significance.

## 17. Revised implementation roadmap

### Phase 0 — Protocol and provenance

- Freeze the causal diagram, target population, outcomes, exposure contrasts, quality rules, decision thresholds, and analysis inventory.
- Create a dataset manifest with versions, dates, licences, attribution/redistribution rules, account requirements, checksums, expected latency, and an open replacement for every restricted or unavailable asset.
- Register the protocol or submit a Stage 1 Registered Report.

**Gate:** no confirmatory human-association estimate before the protocol is frozen; “effect” is reserved for separately registered intervention designs.

### Phase 1 — Measurement audit

- Build the paired-swath S-NPP observation summaries, exact-overpass sampling frames, and sparse event table.
- Mask static thermal sources.
- Calibrate event linkage without examining exposure-association estimates.
- Validate active-fire detection and burned scars in a stratified random sample.
- Audit historical roads, rivers, canals, land cover, and peat uncertainty.
- Audit MOD13Q1 EVI and HLS NDMI temporal coverage before the prior-negative cutoff, and quantify VIIRS detection sensitivity across frozen 2014 MOD44B canopy strata.

**Deliverable:** a measurement report with detection sensitivity and uncertainty by accessibility and ecosystem.

### Phase 2 — Primary Kalimantan association

- Build the 1 km case-overpass risk-set table and the separate complete 5 km surveillance panel.
- Fit the frozen environmental, accessibility, transformation, and joint mediator-adjusted models.
- Run the named complete-panel RONI sensitivity and exploratory exposure × RONI models; do not insert an unidentifiable ENSO main effect into exact-overpass risk sets.
- Run equivalence, diagnostics, bias analyses, spatial validation, and year-specific checks.
- Release the full specification curve.

**Deliverable:** adjusted detected-onset IDRs with a neutral decision classification, plus clearly separate full-panel descriptive rates and calibration curves.

### Phase 3 — Fire burden and event characteristics

- Link events to burned-area patches.
- Model unconditional burned area and event-conditional characteristics.
- Add sampled ecological-severity mapping.

**Deliverable:** a clear separation of occurrence, burned area, radiative output, persistence, and ecological severity.

### Phase 4 — Quasi-experimental modules

- Run the registered road-opening design only if exposure timing and pre-trend gates pass; give any causal conversion analysis its own complete registration.
- Run the border design only if harmonization and continuity gates pass.

**Deliverable:** narrowly worded causal estimates or a documented finding that causal identification was not credible.

### Phase 5 — External replication

- Harmonized Sabah/Sarawak/Brunei replication.
- Separately registered Sumatra and Papua transportability tests.

**Deliverable:** evidence about where the Kalimantan relationship does and does not generalize.

## 18. Minimum viable study

The strongest MVP is not a large ML system. It is:

1. Kalimantan baseline-forest cohort;
2. science-quality S-NPP VIIRS plus valid-observation masks;
3. dated road/settlement accessibility, with river-based travel time as sensitivity;
4. lagged MapBiomas transformation;
5. antecedent CHIRPS/ERA5-Land conditions, peat, terrain, and baseline forest type;
6. explicit prefire vegetation: lagged QA-valid MOD13Q1 EVI plus baseline canopy/detectability auditing;
7. open NOAA CPC RONI in the complete-panel sensitivity, with its exact-risk-set main effect explicitly recognized as conditioned out;
8. a 1 km exact-overpass conditional risk-set model;
9. spatial-block and year holdouts;
10. equivalence and detection-bias analyses; and
11. a result classified as full/partial support, mixed, negligible, contradictory, inconclusive, or not identifiable under frozen rules.

Only after this passes measurement and validation gates should the project add XGBoost, detailed industry mechanisms, a border design, or a public interactive map.

## 19. Language for the eventual paper

Use language such as:

- “Accessibility was associated with a higher rate of first-observed satellite-detectable landscape-fire onset per processed observation opportunity after prespecified adjustment.”
- “The association was robust/unstable to plausible differences in detection sensitivity.”
- “Among detected events, burned area differed; this conditional contrast is descriptive.”
- “A verified road-opening design estimated a local effect under the stated parallel-trend and spillover assumptions.”

Avoid language such as:

- “Industry caused the fires.”
- “Palm oil caused a hotspot because the hotspot was nearby.”
- “First VIIRS detection was the ignition point.”
- “SHAP proved the human contribution.”
- “No significant result means no human effect.”

## Final judgment

The project should proceed, but as a gated research program:

> **First establish that the satellite and exposure maps measure comparable phenomena across remote and accessible forest. Then estimate the adjusted association. Attempt causation only for dated interventions that survive design diagnostics.**

The boldest unbiased commitment is not predicting a positive result. It is committing in advance to publish the same complete evidence package if the human association is large, negligible, reversed, measurement-sensitive, or simply unresolved.
