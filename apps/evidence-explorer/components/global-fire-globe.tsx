"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { LatestGlobalFireCountry, LatestGlobalFireSnapshot, PeatFireComparison, PeatFireCountry } from "../lib/types";

type CesiumRuntime = typeof import("cesium");
type GlobalMetric = "peat_share" | "fire_latest" | "fire_2024";

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

function metricValue(country: PeatFireCountry | LatestGlobalFireCountry | undefined, metric: GlobalMetric) {
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

function formatMetricValue(country: PeatFireCountry | LatestGlobalFireCountry | undefined, metric: GlobalMetric) {
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
  const metricRef = useRef<GlobalMetric>(initialMetric);
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
  const metricCountries = metric === "peat_share"
    ? comparison.countries
    : metric === "fire_latest" && latestGlobalFire
      ? latestGlobalFire.countries
      : comparison.countries;
  const countries = useMemo(() => new Map(metricCountries.map((country) => [country.country_id, country])), [metricCountries]);
  const activeCountry = selected ? countries.get(selected) : undefined;
  const activePeatCountry = selected ? peatCountries.get(selected) : undefined;
  const activeLatestCountry = selected ? latestCountries.get(selected) : undefined;
  const hoveredCountry = hovered ? countries.get(hovered) : undefined;
  const values = useMemo(
    () => metricCountries.map((country) => metricValue(country, metric)).filter((value): value is number => value !== null && Number.isFinite(value)),
    [metricCountries, metric],
  );
  const maxValue = Math.max(1, ...values);

  useEffect(() => {
    metricRef.current = metric;
    hoveredRef.current = hovered;
    selectedRef.current = selected;
    styleLayerRef.current();
  }, [hovered, metric, selected]);

  useEffect(() => {
    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;
    async function start() {
      const host = hostRef.current;
      if (!host) return;
      const canvas = document.createElement("canvas");
      if (!canvas.getContext("webgl") && !canvas.getContext("experimental-webgl")) {
        setFailure("WebGL is unavailable. Use the country picker and table below; the globe is only a visual enhancement.");
        return;
      }
      try {
        (window as Window & { CESIUM_BASE_URL?: string }).CESIUM_BASE_URL = "/cesium/";
        const Cesium = await import("cesium");
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
          return readProperty(picked?.id, "country_id", Cesium);
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
          if (dragged) {
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
        widget.screenSpaceEventHandler.setInputAction(() => { pointerDown = null; }, Cesium.ScreenSpaceEventType.LEFT_UP);
        scene.canvas.addEventListener("mouseleave", () => setHovered(null));
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
      resizeObserver?.disconnect();
      const runtime = runtimeRef.current;
      runtimeRef.current = null;
      if (runtime && !runtime.widget.isDestroyed()) runtime.widget.destroy();
    };
  }, []);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime || !runtimeReady) return;
    const activeRuntime = runtime;
    let cancelled = false;
    let dataSource: any;
    async function load() {
      try {
        setLayerReady(false);
        const source = await activeRuntime.Cesium.GeoJsonDataSource.load("/geo/global-countries.geojson", { clampToGround: false });
        if (cancelled || runtimeRef.current !== activeRuntime) return;
        dataSource = source;
        activeRuntime.widget.dataSources.add(source);
        activeRuntime.entities.clear();
        source.entities.values.forEach((entity: any) => {
          const id = readProperty(entity, "country_id", activeRuntime.Cesium);
          if (id) activeRuntime.entities.set(id, entity);
        });
        styleLayerRef.current = () => {
          const activeMetric = metricRef.current;
          const activeCountries = activeMetric === "peat_share"
            ? comparison.countries
            : activeMetric === "fire_latest" && latestGlobalFire
              ? latestGlobalFire.countries
              : comparison.countries;
          const maximum = Math.max(1, ...activeCountries.map((country) => metricValue(country, activeMetric) ?? 0));
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
              const ratio = Math.log1p(value) / Math.log1p(maximum);
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
  }, [comparison.countries, countries, latestGlobalFire, metricCountries, runtimeReady]);

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
    runtime.widget.camera.flyTo({ destination: runtime.Cesium.Cartesian3.fromDegrees(worldView.longitude, worldView.latitude, worldView.height), duration: 0.45 });
  };
  const selectFromPicker = (countryId: string) => setSelected(countryId || null);

  return (
    <section className="global-globe-card" aria-labelledby="global-globe-heading">
      <header className="section-heading">
        <div>
          <span className="eyebrow">Global context · {latestGlobalFire?.country_count ?? comparison.matched_country_count} country geometries</span>
          <h2 id="global-globe-heading">Global peatland / fire comparison globe</h2>
          <p>This is a separate country-level layer. {latestGlobalFire ? `The default is the latest closed UTC day (${latestGlobalFire.snapshot_date}) from NASA FIRMS NRT MODIS + VIIRS positive detection records.` : "It shows the mapped peat baseline and completed 2024 NASA FIRMS MODIS detection aggregates."} A colored country does not mean the whole country burned.</p>
        </div>
        <span className="layer-key">Exploratory · not causal</span>
      </header>
      <div className="global-globe-toolbar">
        <div className="segmented-control" role="group" aria-label="Global map metric">
          {latestGlobalFire && <button type="button" className={metric === "fire_latest" ? "is-selected" : ""} onClick={() => setMetric("fire_latest")}>Latest NRT · {latestGlobalFire.snapshot_date}</button>}
          <button type="button" className={metric === "fire_2024" ? "is-selected" : ""} onClick={() => setMetric("fire_2024")}>Completed 2024</button>
          <button type="button" className={metric === "peat_share" ? "is-selected" : ""} onClick={() => setMetric("peat_share")}>Peatland share</button>
        </div>
        <label className="global-country-picker">
          <span className="field-label">Jump to a matched country</span>
          <select value={selected ?? ""} onChange={(event) => selectFromPicker(event.target.value)}>
            <option value="">No country selected</option>
            {[...metricCountries].sort((a, b) => a.country.localeCompare(b.country)).map((country) => <option key={country.country_id} value={country.country_id}>{country.country}</option>)}
          </select>
        </label>
      </div>
      <div ref={hostRef} className="global-globe-stage" tabIndex={0} role="region" aria-label="Interactive world globe for matched country aggregates" onKeyDown={(event) => { if (event.key === "Escape") setSelected(null); if (event.key === "+" || event.key === "=") { event.preventDefault(); moveCamera(.72); } if (event.key === "-" || event.key === "_") { event.preventDefault(); moveCamera(1.35); } }}>
        <div className="global-globe-badges" aria-hidden="true"><span>WGS84 · local Natural Earth boundaries</span><span>Country aggregates only · no hotspot points</span></div>
        {!layerReady && !failure && <div className="globe-loading" role="status"><span className="loading-orb" />Loading global country geometry…</div>}
        {failure && <div className="globe-fallback" role="status"><strong>Global globe unavailable</strong><span>{failure}</span></div>}
        {hoveredCountry && !failure && <div className="real-globe-tooltip global-globe-tooltip" style={tooltip} aria-hidden="true"><strong>{hoveredCountry.country}</strong><span>{metricLabel(metric)}: {formatMetricValue(hoveredCountry, metric)}</span><small>Click for details · {displayMetricUnit(metric)}</small></div>}
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
      <div className="global-globe-legend"><span><i className={`legend-ramp ${metric === "peat_share" ? "global-peat" : "global-fire"}`} /> {metricLabel(metric)}: lower → higher</span><span><i className="legend-hatch" /> No matched aggregate / unknown</span><span>Scale uses log display for rates; it is not a risk probability.</span></div>
      {activeCountry ? (
        <aside className="global-selection" aria-live="polite">
          <div><span className="eyebrow">Selected country aggregate</span><h3>{activeCountry.country}</h3></div>
          <dl>
            <div><dt>Peatland share</dt><dd>{activePeatCountry ? `${activePeatCountry.peat_share_percent.toFixed(2)}% (${compact(activePeatCountry.peat_area_km2)} km²)` : "Unknown"}</dd></div>
            <div><dt>Latest closed-day snapshot</dt><dd>{activeLatestCountry && latestGlobalFire ? `${compact(activeLatestCountry.positive_detection_count)} positive detection records · ${latestGlobalFire.snapshot_date}` : "Unknown"}</dd></div>
            <div><dt>Completed 2024 comparison</dt><dd>{activePeatCountry ? `${compact(activePeatCountry.peat_detection_count + activePeatCountry.nonpeat_detection_count)} records · ${activePeatCountry.total_detection_rate_per_1000_km2.toFixed(2)} / 1,000 km²` : "Unknown"}</dd></div>
          </dl>
          <p>Latest values are positive satellite detection records from a closed-day NRT snapshot, not unique fires, burned-area polygons, or an observation-adjusted rate. The peat baseline covers 2000–2020; it is not a 2026 peatland map.</p>
        </aside>
      ) : <p className="global-selection-empty">Select a country on the globe or from the picker to see its peat share, detection counts, rates, and the comparison caveats.</p>}
      <p className="global-globe-footnote"><strong>Boundary source:</strong> Natural Earth Admin-0 countries, public domain. <strong>Data meaning:</strong> polygons are display units for matched country aggregates; they do not say that all land inside the polygon burned.</p>
    </section>
  );
}
