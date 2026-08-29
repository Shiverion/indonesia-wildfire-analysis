# Data licensing and redistribution boundaries

The repository-level MIT licence covers original software only. It does **not**
relicense source data, provider marks, boundary files, imagery, or derived
products whose source terms require attribution or share-alike treatment.

Cloning or forking the repository does not grant additional trademark or brand
rights. Files under `apps/evidence-explorer/public/brands/` are retained only
as source-attribution marks and must not be used to imply endorsement. NASA and
NOAA marks remain subject to the [NASA Brand Center](https://www.nasa.gov/nasa-brand-center/)
and [NOAA emblem policy](https://www.noaa.gov/sites/default/files/2022-12/NOAA-emblem-policy-and-License_Revised_102722_GLD_103122_Clean.pdf);
the MapBiomas mark is used only to reference the project under its public brand
guidance.

## Publication analysis bundle

The optional coordinate-free Phase 3 analysis bundle contains two derived
tables:

1. an exact 1:4 matched opportunity table with pseudonymous cell identifiers,
   pre-event environmental features, and no latitude/longitude; and
2. cell-level MapBiomas annual transition fractions with the same pseudonymous
   identifiers and no coordinates.

The bundle excludes raw SiPongi records, raw satellite imagery, Earthdata/CDS
credentials, `.env`, the private cell-centre table, and third-party logos. It
must be distributed with `publication/data/SOURCE_ATTRIBUTION.md` and its
machine-readable manifest. Derived MapBiomas fields should be treated under
the source's CC BY-SA/public-interest terms; other derived fields retain the
attribution obligations of their providers.

## Source-specific terms

| Source | Role | Terms / redistribution decision |
|---|---|---|
| MapBiomas Indonesia Collection 4.1 | 2014 forest cohort and 1990–2024 annual transitions | Provider describes CC BY-SA/public-interest non-commercial use. Attribute MapBiomas Indonesia and preserve share-alike treatment for derived transition tables. |
| NASA VIIRS VNP14A1.002 and MODIS history fallback | Fire-positive and valid-negative observation status | NASA Earth-science data are openly available; retain NASA/VIIRS/MODIS product attribution and do not imply NASA endorsement. |
| CHIRPS daily | Antecedent rainfall | Cite Funk et al. (2015) and the Climate Hazards Center. |
| ERA5-Land | Antecedent VPD, wind, rainfall, and soil water | Retain Copernicus Climate Change Service attribution and applicable CDS licence notice. |
| MOD13Q1.061 | Pre-fire EVI | Retain NASA LP DAAC product citation and DOI attribution. |
| Global peatland extent ensemble | Static peat-extent covariate | CC BY 4.0; cite Zenodo record 19731872. It is a 2000–2020 reference, not 2026 peat condition. |
| geoBoundaries ADM1 / Natural Earth | Dashboard display geometries | Display context only; retain their individual attribution and licence files. |
| NASA Blue Marble and provider logos | Dashboard surface and source marks | Third-party material; not covered by MIT. Follow provider media/brand guidance and do not imply endorsement. |
| SiPongi portal | Descriptive aggregate context | Record-level redistribution licence was not established. Raw portal records are excluded from the publication bundle and public dashboard. |

## Derived files tracked in Git

The repository includes a compact CHIRPS lag-feature cache and two derived
MapBiomas forest rasters for reproducibility. They remain derived third-party
data, not MIT-licensed software:

- `data/derived/chirps/chirps_lag_features_2015.parquet` retains CHIRPS/Climate
  Hazards Center attribution and contains source-grid indices and rainfall
  lags, not private fire coordinates.
- `data/derived/mapbiomas/mapbiomas_c41_forest_fraction_1km_kalimantan.tif` and
  `data/derived/mapbiomas/mapbiomas_c41_natural_forest_mask_2014_kalimantan.tif`
  retain MapBiomas Indonesia attribution and share-alike treatment.

Public administrative boundary GeoJSON and NASA Blue Marble display imagery
retain the notices in `apps/evidence-explorer/public/globe/NOTICE.md` and the
machine-readable source manifest.

The authoritative access inventory, links, hashes, and limitations are in
`DATA_ACCESS_AUDIT.md` and `data/manifests/assets.json`.
