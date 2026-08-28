// MapBiomas Indonesia Collection 4.1 — 2014 land-cover export recipe
//
// Run this in the Google Earth Engine Code Editor after registering through
// the official MapBiomas Landy GEE page. Do not replace the Collection 4.1
// asset with Collection 4: the baseline version is part of the protocol.
// Paste the exact asset ID and band name shown by the official catalog.

var ASSET_ID = 'PASTE_COLLECTION_4_1_ASSET_ID_FROM_MAPBIOMAS_LANDY';
var BAND_NAME = 'classification_2014';
var REGION = ee.Geometry.Rectangle([109.0, -5.0, 120.0, 8.0], 'EPSG:4326', false);

if (ASSET_ID.indexOf('PASTE_') === 0) {
  throw new Error('Set ASSET_ID to the official MapBiomas Indonesia Collection 4.1 asset before running.');
}

var collection = ee.Image(ASSET_ID);
var landCover2014 = collection.select(BAND_NAME).rename('mapbiomas_class_2014');

Map.centerObject(REGION, 5);
Map.addLayer(landCover2014.clip(REGION), {}, 'MapBiomas C4.1 class 2014');

// Export the original class codes. Forest/non-forest is created locally only
// after the researcher records the official legend code crosswalk.
Export.image.toDrive({
  image: landCover2014.clip(REGION),
  description: 'mapbiomas_indonesia_c41_landcover_2014_kalimantan',
  folder: 'indonesia-wildfire-analysis',
  fileNamePrefix: 'mapbiomas_indonesia_c41_landcover_2014_kalimantan',
  region: REGION,
  scale: 30,
  crs: 'EPSG:4326',
  fileFormat: 'GeoTIFF',
  maxPixels: 1e13,
  formatOptions: {cloudOptimized: true}
});
