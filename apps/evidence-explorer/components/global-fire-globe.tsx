"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { LatestGlobalFireCountry, LatestGlobalFireSnapshot, LatestIndonesiaProvince, PeatFireComparison, PeatFireCountry } from "../lib/types";

type CesiumRuntime = typeof import("cesium");
type GlobalMetric = "peat_share" | "fire_latest" | "fire_2024";
type GlobalGeography = "countries" | "indonesia_provinces";

interface GlobalFeatureCollection {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    properties: { country_id: string; country_name: string };
    geometry: { type: string; coordinates: unknown };
  }>;
}

interface GlobalRuntime {
  Cesium: CesiumRuntime;
  widget: any;
  entities: Map<string, any>;
}

const worldView = { longitude: 22, latitude: 8, height: 15_500_000 };
const indonesiaView = { longitude: 117, latitude: -2, height: 3_900_000 };

function metricValue(country: PeatFireCountry | LatestGlobalFireCountry | LatestIndonesiaProvince | undefined, metric: GlobalMetric) {
  if (!country) return null;
  if (metric === "peat_share") return "peat_share_percent" in country ? country.peat_share_percent : null;
  if (metric === "fire_latest") return "positive_detection_count" in country ? country.positive_detection_count : null;
  return "total_detection_rate_per_1000_km2" in country ? country.total_detection_rate_per_1000_km2 : null;
}

function metricLabel(metric: GlobalMetric) {
  if (metric === "peat_share") return "Peatland share";
  if (metric === "fire_latest") return "Latest NRT detections";
  return "2024 MODIS detection rate";
}

function displayMetricUnit(metric: GlobalMetric) {
  if (metric === "peat_share") return "% of country area";
  if (metric === "fire_latest") return "positive detection records";
  return "detections per 1,000 km2";
}

function metricColor(metric: GlobalMetric, ratio: number) {
  const amount = Math.max(0, Math.min(1, ratio));
  const start = metric === "peat_share" ? [32, 62, 86] : [105, 57, 34];
  const end = metric === "peat_share" ? [88, 217, 181] : [255, 175, 76];
  const channel = (index: number) => Math.round(start[index] + (end[index] - start[index]) * amount);
  return `rgba(${channel(0)}, ${channel(1)}, ${channel(2)}, ${0.72 + amount * 0.2})`;
}

function readProperty(entity: any, key: string, Cesium: CesiumRuntime): string | null {
  const value = entity?.properties?.[key]?.getValue?.(Cesium.JulianDate.now());
  return typeof value === "string" ? value : null;
}

function compact(value: number) {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function geographyName(country: PeatFireCountry | LatestGlobalFireCountry | LatestIndonesiaProvince) {
  return "country" in country ? country.country : country.province;
}

function upperDisplayQuantile(values: number[], fraction = 0.95) {
  if (!values.length) return 1;
  const ordered = [...values].sort((left, right) => left - right);
  const index = Math.min(ordered.length - 1, Math.max(0, Math.ceil((ordered.length - 1) * fraction)));
  return Math.max(1, ordered[index]);
}

function formatMetricValue(country: PeatFireCountry | LatestGlobalFireCountry | LatestIndonesiaProvince | undefined, metric: GlobalMetric) {
  const value = metricValue(country, metric);
  if (value === null || !Number.isFinite(value)) return "Unknown";
  if (metric === "peat_share") return `${value.toFixed(2)}%`;
  if (metric === "fire_latest") return compact(value);
  return value.toFixed(2);
}

export function GlobalFireGlobe({
  comparison,
  latestGlobalFire = null,
}: {
  comparison: PeatFireComparison;
  latestGlobalFire?: LatestGlobalFireSnapshot | null;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const runtimeRef = useRef<GlobalRuntime | null>(null);
  const styleLayerRef = useRef<() => void>(() => undefined);
  const initialMetric: GlobalMetric = latestGlobalFire ? "fire_latest" : "fire_2024";
  const defaultGeography: GlobalGeography = latestGlobalFire?.indonesia_provinces.length ? "indonesia_provinces" : "countries";
  const [geography, setGeography] = useState<GlobalGeography>(defaultGeography);
  const metricRef = useRef<GlobalMetric>(initialMetric);
  const geographyRef = useRef<GlobalGeography>("countries");
  const hoveredRef = useRef<string | null>(null);
  const selectedRef = useRef<string | null>(null);
  const [metric, setMetric] = useState<GlobalMetric>(initialMetric);
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [runtimeReady, setRuntimeReady] = useState(false);
  const [layerReady, setLayerReady] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState({ left: 12, top: 48 });

  const peatCountries = useMemo(() => new Map(comparison.countries.map((country) => [country.country_id, country])), [comparison.countries]);
  const latestCountries = useMemo(() => new Map((latestGlobalFire?.countries ?? []).map((country) => [country.country_id, country])), [latestGlobalFire?.countries]);
  const indonesiaProvinces = latestGlobalFire?.indonesia_provinces ?? [];
  const metricCountries = geography === "indonesia_provinces"
    ? indonesiaProvinces
    : metric === "peat_share"
    ? comparison.countries
    : metric === "fire_latest" && latestGlobalFire
      ? latestGlobalFire.countries
      : comparison.countries;
  const countries = useMemo(() => new Map(metricCountries.map((country) => ["country_id" in country ? country.country_id : country.province_id, country])), [metricCountries]);
  const activeCountry = selected ? countries.get(selected) : undefined;
  const activePeatCountry = selected ? peatCountries.get(selected) : undefined;
  const activeLatestCountry = selected ? latestCountries.get(selected) : undefined;
  const activeProvince = selected ? indonesiaProvinces.find((province) => province.province_id === selected) : undefined;
  const hoveredCountry = hovered ? countries.get(hovered) : undefined;
  const values = useMemo(
    () => metricCountries.map((country) => metricValue(country, metric)).filter((value): value is number => value !== null && Number.isFinite(value)),
    [metricCountries, metric],
  );
  const maxValue = Math.max(1, ...values);

  useEffect(() => {
    geographyRef.current = geography;
    metricRef.current = metric;
    hoveredRef.current = hovered;
    selectedRef.current = selected;
    styleLayerRef.current();
  }, [hovered, metric, selected]);

  useEffect(() => {
    if (geography === "indonesia_provinces") {
      setMetric("fire_latest");
      setSelected(null);
    }
  }, [geography]);

  useEffect(() => {
    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;
    let removeCanvasRecovery: (() => void) | null = null;
    async function start() {
      const host = hostRef.current;
      if (!host) return;
      const canvas = document.createElement("canvas");
      if (!canvas.getContext("webgl") && !canvas.getContext("experimental-webgl")) {
        setFailure("WebGL is unavailable. Use the country picker and table below; the globe is only a visual enhancement.");
        return;
      }
      try {
        const runtimeWindow = window as Window & { CESIUM_BASE_URL?: string; Cesium?: CesiumRuntime };
        runtimeWindow.CESIUM_BASE_URL = "/cesium/";
        const Cesium = runtimeWindow.Cesium;
        if (!Cesium) throw new Error("Cesium runtime did not load.");
        if (cancelled || !hostRef.current) return;
        const widget = new Cesium.CesiumWidget(host, {
          ellipsoid: Cesium.Ellipsoid.WGS84,
          terrainProvider: new Cesium.EllipsoidTerrainProvider({ ellipsoid: Cesium.Ellipsoid.WGS84 }),
          baseLayer: false,
          scene3DOnly: true,
          requestRenderMode: true,
          maximumRenderTimeChange: Number.POSITIVE_INFINITY,
          skyBox: false,
        });
        const scene = widget.scene;
        scene.backgroundColor = Cesium.Color.fromCssColorString("#030b12");
        scene.globe.baseColor = Cesium.Color.fromCssColorString("#153848");
        scene.globe.enableLighting = true;
        scene.globe.showGroundAtmosphere = true;
        if (scene.skyAtmosphere) scene.skyAtmosphere.show = true;
        if (scene.moon) scene.moon.show = false;
        if (scene.sun) scene.sun.show = false;
        const controller = scene.screenSpaceCameraController;
        controller.enableTranslate = false;
        controller.enableTilt = false;
        controller.minimumZoomDistance = 350_000;
        controller.maximumZoomDistance = 20_000_000;
        controller.inertiaSpin = 0.78;
        controller.inertiaZoom = 0.68;
        widget.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);
        try {
          const imagery = await Cesium.SingleTileImageryProvider.fromUrl("/globe/earth-blue-marble.jpg", {
            credit: new Cesium.Credit("NASA Blue Marble — Land Surface, Ocean Color and Sea Ice"),
          });
          if (!cancelled) scene.imageryLayers.addImageryProvider(imagery);
        } catch {
          // The vector country layer remains usable if the optional local texture cannot decode.
        }
        const runtime: GlobalRuntime = { Cesium, widget, entities: new Map() };
        runtimeRef.current = runtime;
        let pointerDown: any = null;
        let dragged = false;
        const countryAt = (position: any) => {
          const picked = scene.pick(position);
          return readProperty(picked?.id, geographyRef.current === "countries" ? "country_id" : "province_id", Cesium);
        };
        const placeTooltip = (position: any) => {
          const rect = scene.canvas.getBoundingClientRect();
          setTooltip({
            left: Math.max(10, Math.min(rect.width - 272, position.x + 14)),
            top: Math.max(44, Math.min(rect.height - 140, position.y + 14)),
          });
        };
        widget.screenSpaceEventHandler.setInputAction((event: any) => {
          pointerDown = event.position;
          dragged = false;
        }, Cesium.ScreenSpaceEventType.LEFT_DOWN);
        widget.screenSpaceEventHandler.setInputAction((movement: any) => {
          if (pointerDown && Cesium.Cartesian2.distance(pointerDown, movement.endPosition) > 5) dragged = true;
          if (pointerDown && dragged) {
            host.style.cursor = "grabbing";
            setHovered(null);
            return;
          }
          const country = countryAt(movement.endPosition);
          host.style.cursor = country ? "pointer" : "grab";
          placeTooltip(movement.endPosition);
          setHovered((previous) => previous === country ? previous : country);
        }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
        widget.screenSpaceEventHandler.setInputAction((event: any) => {
          const country = countryAt(event.position);
          if (!dragged && country) setSelected((previous) => previous === country ? null : country);
          pointerDown = null;
          dragged = false;
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
        widget.screenSpaceEventHandler.setInputAction((event: any) => {
          pointerDown = null;
          const position = event?.position;
          const country = position ? countryAt(position) : null;
          host.style.cursor = country ? "pointer" : "grab";
          if (position) placeTooltip(position);
          setHovered(country);
          // Keep `dragged` until LEFT_CLICK (or the next LEFT_DOWN) so a drag
          // cannot accidentally pin a polygon. Hover is active again because
          // pointerDown is now null.
        }, Cesium.ScreenSpaceEventType.LEFT_UP);
        const recoverFromCanvasExit = () => {
          pointerDown = null;
          dragged = false;
          host.style.cursor = "grab";
          setHovered(null);
        };
        scene.canvas.addEventListener("mouseleave", recoverFromCanvasExit);
        removeCanvasRecovery = () => scene.canvas.removeEventListener("mouseleave", recoverFromCanvasExit);
        resizeObserver = new ResizeObserver(() => scene.requestRender());
        resizeObserver.observe(host);
        setRuntimeReady(true);
        widget.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(worldView.longitude, worldView.latitude, worldView.height), duration: 0 });
      } catch {
        if (!cancelled) setFailure("The global WGS84 globe could not initialize. The country comparison remains available in the table and scatter plot.");
      }
    }
    void start();
    return () => {
      cancelled = true;
      removeCanvasRecovery?.();
      resizeObserver?.disconnect();
      const runtime = runtimeRef.current;
      runtimeRef.current = null;
      if (runtime && !runtime.widget.isDestroyed()) runtime.widget.destroy();
    };
  }, []);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime || !runtimeReady) return;
    const view = geography === "indonesia_provinces" ? indonesiaView : worldView;
    runtime.widget.camera.flyTo({
      destination: runtime.Cesium.Cartesian3.fromDegrees(view.longitude, view.latitude, view.height),
      duration: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? 0 : 0.45,
    });
  }, [geography, runtimeReady]);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime || !runtimeReady) return;
    const activeRuntime = runtime;
    let cancelled = false;
    let dataSource: any;
    async function load() {
      try {
        setLayerReady(false);
        const source = await activeRuntime.Cesium.GeoJsonDataSource.load(
          geography === "countries" ? "/geo/global-countries.geojson" : "/geo/indonesia-adm1.geojson",
          { clampToGround: false },
        );
        if (cancelled || runtimeRef.current !== activeRuntime) return;
        dataSource = source;
        activeRuntime.widget.dataSources.add(source);
        activeRuntime.entities.clear();
        source.entities.values.forEach((entity: any) => {
          const id = readProperty(entity, geography === "countries" ? "country_id" : "province_id", activeRuntime.Cesium);
          if (id) activeRuntime.entities.set(id, entity);
        });
        styleLayerRef.current = () => {
          const activeMetric = metricRef.current;
          const activeCountries = geography === "indonesia_provinces"
            ? indonesiaProvinces
            : activeMetric === "peat_share"
            ? comparison.countries
            : activeMetric === "fire_latest" && latestGlobalFire
              ? latestGlobalFire.countries
              : comparison.countries;
          const maximum = upperDisplayQuantile(
            activeCountries
              .map((country) => metricValue(country, activeMetric))
              .filter((value): value is number => value !== null && Number.isFinite(value)),
          );
          for (const [id, entity] of activeRuntime.entities) {
            const country = countries.get(id);
            if (!entity.polygon) continue;
            const value = metricValue(country, activeMetric);
            const isUnknown = !country || value === null || !Number.isFinite(value);
            if (isUnknown) {
              entity.polygon.material = new activeRuntime.Cesium.CheckerboardMaterialProperty({
                evenColor: activeRuntime.Cesium.Color.fromCssColorString("rgba(139, 157, 158, .52)"),
                oddColor: activeRuntime.Cesium.Color.fromCssColorString("rgba(32, 50, 56, .74)"),
                repeat: new activeRuntime.Cesium.Cartesian2(7, 7),
              });
            } else {
              const ratio = Math.min(1, Math.log1p(value) / Math.log1p(maximum));
              entity.polygon.material = activeRuntime.Cesium.Color.fromCssColorString(metricColor(activeMetric, ratio));
            }
            const isSelected = selectedRef.current === id;
            const isHovered = hoveredRef.current === id;
            entity.polygon.outline = true;
            entity.polygon.outlineColor = activeRuntime.Cesium.Color.fromCssColorString(isSelected ? "#edfff9" : isHovered ? "#8cf5d1" : "rgba(220, 255, 243, .58)");
            entity.polygon.outlineWidth = isSelected ? 3 : isHovered ? 2 : 1;
          }
          activeRuntime.widget.scene.requestRender();
        };
        styleLayerRef.current();
        if (!cancelled) setLayerReady(true);
      } catch {
        if (!cancelled) setFailure("The frozen global country geometry could not be loaded. It is unavailable rather than represented as zero.");
      }
    }
    void load();
    return () => {
      cancelled = true;
      styleLayerRef.current = () => undefined;
      if (dataSource && !activeRuntime.widget.isDestroyed()) activeRuntime.widget.dataSources.remove(dataSource, true);
    };
  }, [comparison.countries, countries, geography, indonesiaProvinces, latestGlobalFire, metricCountries, runtimeReady]);

  const moveCamera = (factor: number) => {
    const runtime = runtimeRef.current;
    if (!runtime) return;
    const cartographic = runtime.Cesium.Cartographic.fromCartesian(runtime.widget.camera.position);
    const height = Math.max(350_000, Math.min(20_000_000, cartographic.height * factor));
    runtime.widget.camera.flyTo({
      destination: runtime.Cesium.Cartesian3.fromRadians(cartographic.longitude, cartographic.latitude, height),
      duration: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? 0 : 0.32,
    });
  };
  const reset = () => {
    const runtime = runtimeRef.current;
    if (!runtime) return;
    const view = geography === "indonesia_provinces" ? indonesiaView : worldView;
    runtime.widget.camera.flyTo({ destination: runtime.Cesium.Cartesian3.fromDegrees(view.longitude, view.latitude, view.height), duration: 0.45 });
  };
  const selectFromPicker = (countryId: string) => setSelected(countryId || null);
  const selectGeography = (next: GlobalGeography) => {
    setSelected(null);
    setHovered(null);
    setGeography(next);
  };

  return (
    <section className="global-globe-card" aria-labelledby="global-globe-heading">
      <header className="section-heading">
        <div>
          <span className="eyebrow">{geography === "countries" ? `Global context · ${latestGlobalFire?.country_count ?? comparison.matched_country_count} country geometries` : `Indonesia context · ${latestGlobalFire?.indonesia_provinces.length ?? 0} province geometries`}</span>
          <h2 id="global-globe-heading">{geography === "countries" ? "World country context" : "Indonesia province context"}</h2>
          <p>{geography === "countries" ? (latestGlobalFire ? `The default is the latest closed UTC day (${latestGlobalFire.snapshot_date}) from NASA FIRMS NRT MODIS + VIIRS positive detection records.` : "It shows the mapped peat baseline and completed 2024 NASA FIRMS MODIS detection aggregates.") : `Indonesia is split into ${latestGlobalFire?.indonesia_provinces.length ?? 0} frozen ADM1 display units. Province colors show only the latest FIRMS positive detection-record aggregate; the 2017 boundary source is not a current legal boundary.`} A colored polygon does not mean the whole polygon burned.</p>
        </div>
        <span className="layer-key">Exploratory · not causal</span>
      </header>
      <div className="global-globe-toolbar">
        <div className="segmented-control" role="group" aria-label="Global map geography">
          <button type="button" className={geography === "indonesia_provinces" ? "is-selected" : ""} onClick={() => selectGeography("indonesia_provinces")} disabled={!latestGlobalFire?.indonesia_provinces.length}>Indonesia provinces</button>
          <button type="button" className={geography === "countries" ? "is-selected" : ""} onClick={() => selectGeography("countries")}>World countries</button>
        </div>
        <div className="segmented-control" role="group" aria-label="Global map metric">
          {latestGlobalFire && <button type="button" className={metric === "fire_latest" ? "is-selected" : ""} onClick={() => setMetric("fire_latest")}>Latest NRT · {latestGlobalFire.snapshot_date}</button>}
          {geography === "countries" && <button type="button" className={metric === "fire_2024" ? "is-selected" : ""} onClick={() => setMetric("fire_2024")}>Completed 2024</button>}
          {geography === "countries" && <button type="button" className={metric === "peat_share" ? "is-selected" : ""} onClick={() => setMetric("peat_share")}>Peatland share</button>}
        </div>
        {geography === "indonesia_provinces" && <span className="metric-coverage-note">Province bundle: latest NRT only</span>}
        <label className="global-country-picker">
          <span className="field-label">{geography === "countries" ? "Jump to a matched country" : "Jump to an Indonesian province"}</span>
          <select value={selected ?? ""} onChange={(event) => selectFromPicker(event.target.value)}>
            <option value="">No {geography === "countries" ? "country" : "province"} selected</option>
            {[...metricCountries].sort((a, b) => geographyName(a).localeCompare(geographyName(b))).map((country) => {
              const id = "country_id" in country ? country.country_id : country.province_id;
              return <option key={id} value={id}>{geographyName(country)}</option>;
            })}
          </select>
        </label>
      </div>
      <div ref={hostRef} className="global-globe-stage" tabIndex={0} role="region" aria-label={geography === "countries" ? "Interactive world globe for country aggregates" : "Interactive Indonesia province globe for FIRMS aggregates"} onKeyDown={(event) => { if (event.key === "Escape") setSelected(null); if (event.key === "+" || event.key === "=") { event.preventDefault(); moveCamera(.72); } if (event.key === "-" || event.key === "_") { event.preventDefault(); moveCamera(1.35); } }}>
        <div className="global-globe-badges" aria-hidden="true"><span>WGS84 · {geography === "countries" ? "Natural Earth country boundaries" : "geoBoundaries Indonesia ADM1"}</span><span>{geography === "countries" ? "Country aggregates" : "Province aggregates"} only · no hotspot points</span></div>
        {!layerReady && !failure && <div className="globe-loading" role="status"><span className="loading-orb" />Loading {geography === "countries" ? "global country" : "Indonesia province"} geometry…</div>}
        {failure && <div className="globe-fallback" role="status"><strong>Global globe unavailable</strong><span>{failure}</span></div>}
        {hoveredCountry && !failure && <div className="real-globe-tooltip global-globe-tooltip" style={tooltip} aria-hidden="true"><strong>{geographyName(hoveredCountry)}</strong><span>{metricLabel(metric)}: {formatMetricValue(hoveredCountry, metric)}</span><small>Click for details · {displayMetricUnit(metric)}</small></div>}
      </div>
      <div className="real-globe-controls">
        <div className="globe-control-group" aria-label="Global globe camera controls">
          <button type="button" onClick={reset} disabled={!runtimeReady}>Reset world</button>
          <button type="button" aria-label="Zoom global globe out" onClick={() => moveCamera(1.35)} disabled={!runtimeReady}>−</button>
          <button type="button" aria-label="Zoom global globe in" onClick={() => moveCamera(.72)} disabled={!runtimeReady}>+</button>
          <button type="button" onClick={() => setSelected(null)} disabled={!selected}>Clear selection</button>
        </div>
        <span>Drag to orbit · scroll/pinch to zoom · hover to preview · click to pin</span>
      </div>
      <div className="global-globe-legend"><span><i className={`legend-ramp ${metric === "peat_share" ? "global-peat" : "global-fire"}`} /> {metricLabel(metric)}: lower → higher</span><span><i className="legend-hatch" /> No matched aggregate / unknown</span><span>{metric === "peat_share" ? "Area share uses a robust 95th-percentile display cap." : "Counts use a log scale with a robust 95th-percentile display cap; above-cap units remain visible."} This is not a risk probability.</span></div>
      {activeCountry ? (
        <aside className="global-selection" aria-live="polite">
          <div><span className="eyebrow">{geography === "countries" ? "Selected country aggregate" : "Selected Indonesia province aggregate"}</span><h3>{geographyName(activeCountry)}</h3></div>
          {geography === "indonesia_provinces" ? (
            <dl>
              <div><dt>Latest closed-day snapshot</dt><dd>{activeProvince && latestGlobalFire ? `${compact(activeProvince.positive_detection_count)} positive detection records · ${latestGlobalFire.snapshot_date}` : "Unknown"}</dd></div>
              <div><dt>Boundary source</dt><dd>geoBoundaries ADM1; reference year 2017</dd></div>
              <div><dt>Other metrics</dt><dd>Peat share and completed-2024 country metrics are not available at this province join.</dd></div>
            </dl>
          ) : (
            <dl>
              <div><dt>Peatland share</dt><dd>{activePeatCountry ? `${activePeatCountry.peat_share_percent.toFixed(2)}% (${compact(activePeatCountry.peat_area_km2)} km²)` : "Unknown"}</dd></div>
              <div><dt>Latest closed-day snapshot</dt><dd>{activeLatestCountry && latestGlobalFire ? `${compact(activeLatestCountry.positive_detection_count)} positive detection records · ${latestGlobalFire.snapshot_date}` : "Unknown"}</dd></div>
              <div><dt>Completed 2024 comparison</dt><dd>{activePeatCountry ? `${compact(activePeatCountry.peat_detection_count + activePeatCountry.nonpeat_detection_count)} records · ${activePeatCountry.total_detection_rate_per_1000_km2.toFixed(2)} / 1,000 km²` : "Unknown"}</dd></div>
            </dl>
          )}
          <p>Latest values are positive satellite detection records from a closed-day NRT snapshot, not unique fires, burned-area polygons, or an observation-adjusted rate. A colored polygon is a reporting unit, not proof that all land inside it burned.</p>
        </aside>
      ) : <p className="global-selection-empty">Select a {geography === "countries" ? "country" : "province"} on the globe or from the picker to see its aggregate value and source caveats.</p>}
      <p className="global-globe-footnote"><strong>Boundary source:</strong> {geography === "countries" ? "Natural Earth Admin-0 countries, public domain." : "geoBoundaries IDN ADM1, reference year 2017, Open Database License."} <strong>Data meaning:</strong> polygons are display units for positive detection aggregates; they do not say that all land inside the polygon burned.</p>
    </section>
  );
}
