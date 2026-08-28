# 2015 local environmental pilot

> Exploratory descriptive output only. It is not the Phase 2 model and does not establish causality.

The table contains **50** diagnostic overpass-events; **43** have complete 72-hour ERA5 support. The diagnostic outcome is positive when at least one valid cell contains a fire pixel.

| Measure | Positive median | Negative median | Difference | Screening p-value |
|---|---:|---:|---:|---:|
| ERA5 regional mean VPD, prior 24 h (kPa) | 0.7964487794772761 | 0.7714202270986145 | 0.02502855237866164 | 0.30187287472372426 |
| ERA5 regional maximum wind, prior 24 h (m/s) | 1.8000262464947596 | 1.6364242057448752 | 0.16360204074988438 | 0.27166647159629287 |
| ERA5 regional rainfall, prior 24 h (mm) | 7.678046561788042 | 9.540729168792955 | -1.8626826070049134 | 0.22594549839274147 |
| ERA5 layer-1 soil water, prior 24 h | 0.3187705455548743 | 0.31296813553713 | 0.005802410017744286 | 0.24609549460893754 |
| MOD13Q1 QA tile-summary EVI (not event-cell linked) | 0.5387730255482633 | 0.5387730255482633 | 0.0 | 1.0 |

## Interpretation boundary

These comparisons describe this small, observation-selected diagnostic subset. They do not correct for satellite opportunity, cloud, spatial clustering, or cell-level exposure. CHIRPS and peat were intentionally left unlinked rather than imputed. The results therefore cannot answer whether peat is more vulnerable, whether El Niño caused the events, or whether an actor caused them.
