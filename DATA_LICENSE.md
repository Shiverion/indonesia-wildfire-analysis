# Data licensing and redistribution boundaries

The repository-level MIT licence covers original software only. It does **not**
relicense source data, provider marks, boundary files, imagery, or derived
products whose source terms require attribution or share-alike treatment.

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

The authoritative access inventory, links, hashes, and limitations are in
`DATA_ACCESS_AUDIT.md` and `data/manifests/assets.json`.
