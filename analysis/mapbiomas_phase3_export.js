// Phase 3 — compact MapBiomas Indonesia Collection 4.1 transition export
//
// REFERENCE FALLBACK ONLY. The validated production path is:
//   python analysis/export_phase3_earthengine.py --wait
// A single 18,664-cell / 307-band Code Editor export can exceed Earth Engine's
// computed-value limit. The Python runner uses small transition-histogram
// chunks, automatic retry/resume, local validation, and temporary-asset cleanup.
// This reference does not download the 1990–2024 national raster stack.
//
// Preparation:
// 1. Run: python analysis/phase3_land_change.py --prepare-private-cells
// 2. Upload data/derived/phase3/phase3_cell_centres_private.csv as a PRIVATE
//    Earth Engine table asset, using longitude/latitude as point geometry.
// 3. Paste its asset ID below. Keep that asset private.
// 4. Confirm the MapBiomas image metadata/bands in the Code Editor, then Run.

var CELL_POINTS_ASSET = 'PASTE_PRIVATE_CELL_POINTS_ASSET_ID';
var MAPBIOMAS_ASSET = 'projects/mapbiomas-public/assets/indonesia/lulc/collection4/mapbiomas_indonesia_collection4_coverage_v2';

if (CELL_POINTS_ASSET.indexOf('PASTE_') === 0) {
  throw new Error('Set CELL_POINTS_ASSET to the private uploaded cell-centre table.');
}

var cells = ee.FeatureCollection(CELL_POINTS_ASSET);
var landCover = ee.Image(MAPBIOMAS_ASSET);
// The current Earth Engine endpoint does not resolve the short EPSG:6933
// alias consistently. This is the official equivalent WKT used by the locked
// local 1 km EASE-Grid raster, with the same globally aligned transform.
var GRID_WKT = 'PROJCS["WGS 84 / NSIDC EASE-Grid 2.0 Global",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Cylindrical_Equal_Area"],PARAMETER["standard_parallel_1",30],PARAMETER["central_meridian",0],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","6933"]]';
var gridProjection = ee.Projection(GRID_WKT, [1000, 0, 0, 0, -1000, 0]);
var naturalCodes = [3, 5, 76];
var notObservedCode = 27;
var destinations = {
  nonforest_natural: [13],
  rice_paddy: [40],
  oil_palm: [35],
  pulpwood_plantation: [9],
  other_agriculture: [21],
  mining: [30],
  urban: [24],
  other_nonvegetated: [25],
  aquaculture: [31],
  water: [33]
};

function anyCode(image, codes) {
  var result = ee.Image(0);
  codes.forEach(function(code) {
    result = result.or(image.eq(code));
  });
  return result;
}

function fractionOnRegisteredGrid(binaryImage, name) {
  return binaryImage
    .unmask(0)
    .toFloat()
    .reduceResolution({
      reducer: ee.Reducer.mean(),
      maxPixels: 4096,
      bestEffort: false
    })
    .reproject(gridProjection)
    .rename(name);
}

function classification(year) {
  return landCover.select('classification_' + year);
}

var summary = ee.Image([]);
var eventYearsByHorizon = {
  1: [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
  2: [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022],
  3: [2015, 2016, 2017, 2018, 2019, 2020, 2021]
};

Object.keys(eventYearsByHorizon).forEach(function(horizonText) {
  var horizon = parseInt(horizonText, 10);
  eventYearsByHorizon[horizon].forEach(function(eventYear) {
    var pre = classification(eventYear - 1);
    var post = classification(eventYear + horizon);
    var preNatural = anyCode(pre, naturalCodes);
    var postNatural = anyCode(post, naturalCodes);
    var preObserved = pre.neq(notObservedCode).and(pre.neq(0));
    var postObserved = post.neq(notObservedCode).and(post.neq(0));
    var validPair = preObserved.and(postObserved);
    var loss = preNatural.and(postNatural.not()).and(validPair);

    // Pre-index bands repeat across horizons; add them only once.
    if (horizon === 1) {
      summary = summary.addBands(
        fractionOnRegisteredGrid(preNatural.and(preObserved), 'pre_natural_fraction_' + eventYear)
      );
      summary = summary.addBands(
        fractionOnRegisteredGrid(preObserved, 'pre_observed_fraction_' + eventYear)
      );
    }
    summary = summary.addBands(
      fractionOnRegisteredGrid(postObserved, 'post_observed_fraction_' + eventYear + '_h' + horizon)
    );
    summary = summary.addBands(
      fractionOnRegisteredGrid(loss, 'loss_fraction_cell_' + eventYear + '_h' + horizon)
    );
    Object.keys(destinations).forEach(function(destination) {
      var transition = preNatural
        .and(anyCode(post, destinations[destination]))
        .and(validPair);
      summary = summary.addBands(
        fractionOnRegisteredGrid(
          transition,
          'to_' + destination + '_fraction_cell_' + eventYear + '_h' + horizon
        )
      );
    });
  });
});

print('MapBiomas asset', landCover);
print('Private cell count', cells.size());
print('Summary band count', summary.bandNames().size());
print('Summary bands', summary.bandNames());

var sampled = summary.sampleRegions({
  collection: cells,
  properties: ['cell_id'],
  projection: gridProjection,
  scale: 1000,
  geometries: false,
  tileScale: 8
});

Export.table.toDrive({
  collection: sampled,
  description: 'mapbiomas_c41_phase3_transition_summary_private',
  folder: 'indonesia-wildfire-analysis',
  fileNamePrefix: 'mapbiomas_c41_transition_summary_private',
  fileFormat: 'CSV'
});
