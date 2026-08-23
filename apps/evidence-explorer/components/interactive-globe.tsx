"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { EvidenceMode, ProvinceAggregate } from "../lib/types";

type CesiumRuntime = typeof import("cesium");

interface BoundaryFeature {
  type: "Feature";
  properties: {
    province: string;
    boundary_set: string;
    centroid?: { latitude: number; longitude: number };
    legacy_note?: string;
    geometry_role?: string;
  };
  geometry: { type: "Polygon" | "MultiPolygon"; coordinates: unknown };
}

interface BoundaryCollection {
  type: "FeatureCollection";
  name: string;
  features: BoundaryFeature[];
}

interface CesiumState {
  Cesium: CesiumRuntime;
  widget: any;
  entityByProvince: Map<string, any>;
}

interface InteractiveGlobeProps {
  mode: EvidenceMode;
  platform: string;
  periodLabel: string;
  isPartialSnapshot: boolean;
  rows: ProvinceAggregate[];
  selectedProvince: string | null;
  onSelectProvince: (province: string | null) => void;
}

const initialView = { longitude: 114.4, latitude: 0.8, height: 7_100_000 };
const kalimantanView = { longitude: 114.4, latitude: 0.8, height: 2_100_000 };

function scaleColor(ratio: number, mode: EvidenceMode) {
  const start = mode === "sipongi" ? [18, 50, 78] : [65, 40, 46];
  const end = mode === "sipongi" ? [75, 235, 170] : [255, 145, 54];
  const amount = Math.max(0, Math.min(1, ratio));
  const channel = (index: number) => Math.round(start[index] + (end[index] - start[index]) * amount);
  return `rgba(${channel(0)}, ${channel(1)}, ${channel(2)}, ${0.86 + amount * 0.1})`;
}

function upperDisplayQuantile(values: number[], fraction = 0.95) {
  if (!values.length) return 1;
  const ordered = [...values].sort((left, right) => left - right);
  const index = Math.min(ordered.length - 1, Math.max(0, Math.ceil((ordered.length - 1) * fraction)));
  return Math.max(1, ordered[index]);
}

function metricLabel(row: ProvinceAggregate | undefined, mode: EvidenceMode, platform: string) {
  if (!row || row.isUnknown || row.value === null) return "Unknown source-row coverage";
  const value = new Intl.NumberFormat("en-US").format(row.value);
  return mode === "gwis" ? `${value} reported hectares` : `${value} ${platform === "All platforms" ? "positive portal records" : `${platform} portal records`}`;
}

function coverageLabel(row: ProvinceAggregate | undefined, mode: EvidenceMode, isPartialSnapshot: boolean) {
  if (!row || row.isUnknown) return "Unknown — missing source rows are not interpreted as zero.";
  if (mode === "gwis") return `${row.observed} of ${row.expected} Jul–Nov source rows present.`;
  if (isPartialSnapshot) return "One validated response per province through the last closed portal-reported day; no observation denominator.";
  return "Five Jul–Nov months aggregated; no observation denominator.";
}

function runtimeProvince(entity: any, Cesium: CesiumRuntime): string | null {
  const value = entity?.properties?.province?.getValue?.(Cesium.JulianDate.now());
  return typeof value === "string" ? value : null;
}

function compactNumber(value: number) {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function labelProvince(province: string, mode: EvidenceMode) {
  if (mode === "gwis" && province === "Kalimantan Timur") return "K. Timur + Utara";
  return province.replace("Kalimantan ", "K. ");
}

function mapMetricName(mode: EvidenceMode, platform: string) {
  if (mode === "gwis") return "reported burned area";
  return platform === "All platforms" ? "positive portal records" : `${platform} portal records`;
}

function mapMetricUnit(mode: EvidenceMode) {
  return mode === "gwis" ? "ha" : "records";
}

function labelOffset(province: string, mode: EvidenceMode): [number, number] {
  const currentOffsets: Record<string, [number, number]> = {
    "Kalimantan Barat": [-16, -4],
    "Kalimantan Tengah": [-6, -13],
    "Kalimantan Selatan": [3, -18],
    "Kalimantan Timur": [18, 1],
    "Kalimantan Utara": [27, 20],
  };
  const legacyOffsets: Record<string, [number, number]> = {
    "Kalimantan Barat": [-16, -4],
    "Kalimantan Tengah": [-6, -13],
    "Kalimantan Selatan": [3, -18],
    "Kalimantan Timur": [22, 12],
  };
  return (mode === "gwis" ? legacyOffsets : currentOffsets)[province] ?? [0, -5];
}

export function InteractiveGlobe({ mode, platform, periodLabel, isPartialSnapshot, rows, selectedProvince, onSelectProvince }: InteractiveGlobeProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const runtimeRef = useRef<CesiumState | null>(null);
  const styleLayerRef = useRef<() => void>(() => undefined);
  const onSelectRef = useRef(onSelectProvince);
  const selectedRef = useRef(selectedProvince);
  const hoveredRef = useRef<string | null>(null);
  const rowsRef = useRef(rows);
  const modeRef = useRef(mode);
  const platformRef = useRef(platform);
  const [runtimeReady, setRuntimeReady] = useState(false);
  const [layerReady, setLayerReady] = useState(false);
  const [loadingText, setLoadingText] = useState("Loading verified globe engine…");
  const [failure, setFailure] = useState<string | null>(null);
  const [hoveredProvince, setHoveredProvince] = useState<string | null>(null);
  const [showMapGuide, setShowMapGuide] = useState(true);
  const [tooltipPosition, setTooltipPosition] = useState({ left: 8, top: 42 });
  const [boundaries, setBoundaries] = useState<Record<EvidenceMode, BoundaryCollection> | null>(null);

  const metrics = useMemo(() => new Map(rows.map((row) => [row.province, row])), [rows]);
  const hoveredRow = hoveredProvince ? metrics.get(hoveredProvince) : undefined;
  const selectedRow = selectedProvince ? metrics.get(selectedProvince) : undefined;
  const activeBoundaryUrl = mode === "sipongi" ? "/geo/kalimantan-current-five.geojson" : "/geo/kalimantan-legacy-four.geojson";
  const availableValues = useMemo(
    () => rows.flatMap((row) => row.value === null || row.isUnknown ? [] : [row.value]),
    [rows],
  );
  const valueRange = availableValues.length
    ? { low: Math.min(...availableValues), high: Math.max(...availableValues) }
    : null;

  useEffect(() => {
    onSelectRef.current = onSelectProvince;
    selectedRef.current = selectedProvince;
    hoveredRef.current = hoveredProvince;
    rowsRef.current = rows;
    modeRef.current = mode;
    platformRef.current = platform;
    styleLayerRef.current();
  }, [hoveredProvince, mode, onSelectProvince, platform, rows, selectedProvince]);

  const moveCamera = useCallback((view: typeof initialView, duration = 600) => {
    const runtime = runtimeRef.current;
    if (!runtime) return;
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    runtime.widget.camera.flyTo({
      destination: runtime.Cesium.Cartesian3.fromDegrees(view.longitude, view.latitude, view.height),
      duration: reducedMotion ? 0 : duration / 1000,
    });
  }, []);

  const focusKalimantan = useCallback(() => moveCamera(kalimantanView), [moveCamera]);
  const resetGlobe = useCallback(() => moveCamera(initialView), [moveCamera]);

  const zoom = useCallback((factor: number) => {
    const runtime = runtimeRef.current;
    if (!runtime) return;
    const cartographic = runtime.Cesium.Cartographic.fromCartesian(runtime.widget.camera.position);
    const altitude = Math.max(450_000, Math.min(16_000_000, cartographic.height * factor));
    runtime.widget.camera.flyTo({
      destination: runtime.Cesium.Cartesian3.fromRadians(cartographic.longitude, cartographic.latitude, altitude),
      duration: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? 0 : 0.32,
    });
  }, []);

  const fullscreen = useCallback(async () => {
    try {
      if (!document.fullscreenElement) await hostRef.current?.requestFullscreen?.();
      else await document.exitFullscreen?.();
    } catch {
      // Fullscreen is an optional enhancement; the data controls remain usable without it.
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadBoundaries() {
      try {
        const [currentResponse, legacyResponse] = await Promise.all([
          fetch("/geo/kalimantan-current-five.geojson"),
          fetch("/geo/kalimantan-legacy-four.geojson"),
        ]);
        if (!currentResponse.ok || !legacyResponse.ok) throw new Error("A frozen boundary asset could not be loaded.");
        const [current, legacy] = await Promise.all([
          currentResponse.json() as Promise<BoundaryCollection>,
          legacyResponse.json() as Promise<BoundaryCollection>,
        ]);
        if (current.features?.length !== 5 || legacy.features?.length !== 4) throw new Error("Boundary feature counts do not match the approved display systems.");
        if (!cancelled) setBoundaries({ sipongi: current, gwis: legacy });
      } catch {
        if (!cancelled) setFailure("Verified boundary geometry could not be loaded. The semantic province table remains available; the globe does not substitute zeroes.");
      }
    }
    void loadBoundaries();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;
    async function startGlobe() {
      const host = hostRef.current;
      if (!host) return;
      const testCanvas = document.createElement("canvas");
      if (!testCanvas.getContext("webgl") && !testCanvas.getContext("experimental-webgl")) {
        setFailure("This browser does not provide WebGL. Use the province table below for the full accessible evidence view.");
        return;
      }
      try {
        setLoadingText("Initializing WGS84 globe…");
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
        scene.globe.baseColor = Cesium.Color.fromCssColorString("#163c4b");
        scene.globe.enableLighting = true;
        scene.globe.showGroundAtmosphere = true;
        if (scene.skyAtmosphere) scene.skyAtmosphere.show = true;
        if (scene.moon) scene.moon.show = false;
        if (scene.sun) scene.sun.show = false;
        const controller = scene.screenSpaceCameraController;
        controller.enableTranslate = false;
        controller.enableTilt = false;
        controller.minimumZoomDistance = 350_000;
        controller.maximumZoomDistance = 18_000_000;
        controller.inertiaSpin = 0.78;
        controller.inertiaZoom = 0.68;
        widget.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);

        try {
          const imagery = await Cesium.SingleTileImageryProvider.fromUrl("/globe/earth-blue-marble.jpg", {
            credit: new Cesium.Credit("NASA Blue Marble — Land Surface, Ocean Color and Sea Ice"),
          });
          if (!cancelled) scene.imageryLayers.addImageryProvider(imagery);
        } catch {
          // The real WGS84 ellipsoid and local vector geometry remain useful if the optional texture cannot decode.
        }
        if (cancelled) {
          widget.destroy();
          return;
        }

        const runtime: CesiumState = { Cesium, widget, entityByProvince: new Map() };
        runtimeRef.current = runtime;
        let pointerDown: any = null;
        let dragged = false;
        const provinceAt = (position: any) => {
          const picked = scene.pick(position);
          return runtimeProvince(picked?.id, Cesium);
        };
        const placeTooltip = (position: any) => {
          const canvasRect = scene.canvas.getBoundingClientRect();
          const nextPosition = {
            left: Math.max(8, Math.min(canvasRect.width - 260, position.x + 14)),
            top: Math.max(42, Math.min(canvasRect.height - 132, position.y + 14)),
          };
          setTooltipPosition((previous) => (
            previous.left === nextPosition.left && previous.top === nextPosition.top ? previous : nextPosition
          ));
        };
        widget.screenSpaceEventHandler.setInputAction((event: any) => {
          pointerDown = event.position;
          dragged = false;
        }, Cesium.ScreenSpaceEventType.LEFT_DOWN);
        widget.screenSpaceEventHandler.setInputAction((movement: any) => {
          if (pointerDown && Cesium.Cartesian2.distance(pointerDown, movement.endPosition) > 5) dragged = true;
          if (pointerDown && dragged) {
            setHoveredProvince((previous) => previous === null ? previous : null);
            return;
          }
          const province = provinceAt(movement.endPosition);
          host.style.cursor = province ? "pointer" : "grab";
          placeTooltip(movement.endPosition);
          setHoveredProvince((previous) => previous === province ? previous : province);
        }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
        widget.screenSpaceEventHandler.setInputAction((event: any) => {
          const province = provinceAt(event.position);
          if (!dragged && province) onSelectRef.current(selectedRef.current === province ? null : province);
          pointerDown = null;
          dragged = false;
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
        widget.screenSpaceEventHandler.setInputAction(() => {
          pointerDown = null;
        }, Cesium.ScreenSpaceEventType.LEFT_UP);
        scene.canvas.addEventListener("mouseleave", () => setHoveredProvince(null));

        resizeObserver = new ResizeObserver(() => scene.requestRender());
        resizeObserver.observe(host);
        setLoadingText("Loading verified aggregate evidence…");
        setRuntimeReady(true);
        // Start close enough to read the five province polygons. The global
        // globe has its own world-scale camera; this local layer should not
        // render Kalimantan as an undifferentiated island silhouette.
        moveCamera(kalimantanView, 0);
      } catch {
        if (!cancelled) setFailure("The WebGL globe could not initialize. Use the province table below for the full accessible evidence view.");
      }
    }
    void startGlobe();
    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      const runtime = runtimeRef.current;
      runtimeRef.current = null;
      if (runtime && !runtime.widget.isDestroyed()) runtime.widget.destroy();
    };
  }, [moveCamera]);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime || !runtimeReady || !boundaries) return;
    const activeRuntime: CesiumState = runtime;
    const activeBoundaries = boundaries;
    let cancelled = false;
    let dataSource: any;
    async function loadLayer() {
      try {
        setLayerReady(false);
        setLoadingText("Loading verified aggregate evidence…");
        const source = await activeRuntime.Cesium.GeoJsonDataSource.load(activeBoundaryUrl, {
          clampToGround: false,
          stroke: activeRuntime.Cesium.Color.fromCssColorString("#d9fff2"),
          strokeWidth: 3,
        });
        if (cancelled || runtimeRef.current !== activeRuntime) return;
        dataSource = source;
        activeRuntime.widget.dataSources.add(source);
        activeRuntime.entityByProvince.clear();
        source.entities.values.forEach((entity: any) => {
          const province = runtimeProvince(entity, activeRuntime.Cesium);
          if (!province) return;
          activeRuntime.entityByProvince.set(province, entity);
          const feature = activeBoundaries[mode].features.find((entry) => entry.properties.province === province);
          const centroid = feature?.properties.centroid;
          if (centroid) {
            const [offsetX, offsetY] = labelOffset(province, mode);
            entity.position = activeRuntime.Cesium.Cartesian3.fromDegrees(centroid.longitude, centroid.latitude, 42_000);
            entity.label = new activeRuntime.Cesium.LabelGraphics({
              text: labelProvince(province, mode),
              font: "600 12px system-ui",
              fillColor: activeRuntime.Cesium.Color.WHITE,
              outlineColor: activeRuntime.Cesium.Color.fromCssColorString("#001018"),
              outlineWidth: 3,
              style: activeRuntime.Cesium.LabelStyle.FILL_AND_OUTLINE,
              showBackground: true,
              backgroundColor: activeRuntime.Cesium.Color.fromCssColorString("rgba(2, 14, 21, .76)"),
              backgroundPadding: new activeRuntime.Cesium.Cartesian2(7, 5),
              verticalOrigin: activeRuntime.Cesium.VerticalOrigin.BOTTOM,
              pixelOffset: new activeRuntime.Cesium.Cartesian2(offsetX, offsetY),
              distanceDisplayCondition: new activeRuntime.Cesium.DistanceDisplayCondition(0, 10_500_000),
            });
          }
        });
        styleLayerRef.current = () => {
          const activeRows = rowsRef.current;
          const values = activeRows.flatMap((row) => row.value === null ? [] : [row.value]);
          const maximum = upperDisplayQuantile(values);
          for (const [province, entity] of activeRuntime.entityByProvince) {
            const row = activeRows.find((candidate) => candidate.province === province);
            if (!entity.polygon) continue;
            const isSelected = selectedRef.current === province;
            const isHovered = hoveredRef.current === province;
            if (!row || row.isUnknown || row.value === null) {
              entity.polygon.material = new activeRuntime.Cesium.CheckerboardMaterialProperty({
                evenColor: activeRuntime.Cesium.Color.fromCssColorString("rgba(139, 157, 158, .52)"),
                oddColor: activeRuntime.Cesium.Color.fromCssColorString("rgba(32, 50, 56, .74)"),
                repeat: new activeRuntime.Cesium.Cartesian2(8, 8),
              });
            } else {
              const logRatio = Math.min(1, Math.log1p(row.value) / Math.log1p(maximum));
              // The five province values are highly skewed. A contrast curve
              // keeps neighbouring reporting units visibly distinct while the
              // label and table retain the exact aggregate count.
              const ratio = Math.pow(logRatio, 1.8);
              entity.polygon.material = activeRuntime.Cesium.Color.fromCssColorString(scaleColor(ratio, modeRef.current));
            }
            entity.polygon.outline = true;
            entity.polygon.outlineColor = activeRuntime.Cesium.Color.fromCssColorString(
              isSelected ? "#ffffff" : isHovered ? "#9fffea" : "#d9fff2",
            );
            entity.polygon.outlineWidth = isSelected ? 4 : isHovered ? 3 : 2;
            entity.polygon.height = isSelected ? 28_000 : isHovered ? 18_000 : 9_000;
            entity.polygon.extrudedHeight = entity.polygon.height;
            if (entity.label) {
              const valueLabel = !row || row.isUnknown || row.value === null
                ? "unknown coverage"
                : `${compactNumber(row.value)} ${mapMetricUnit(modeRef.current)}`;
              entity.label.text = `${labelProvince(province, modeRef.current)}\n${valueLabel}`;
              entity.label.scale = isSelected ? 1.13 : isHovered ? 1.07 : 1;
              entity.label.backgroundColor = activeRuntime.Cesium.Color.fromCssColorString(
                isSelected ? "rgba(8, 57, 66, .92)" : isHovered ? "rgba(13, 82, 84, .88)" : "rgba(2, 14, 21, .76)",
              );
            }
          }
          activeRuntime.widget.scene.requestRender();
        };
        styleLayerRef.current();
        if (!cancelled) {
          setLayerReady(true);
          setLoadingText("");
        }
      } catch {
        if (!cancelled) setFailure("The selected verified boundary layer could not be drawn. It is unavailable rather than represented as zero.");
      }
    }
    void loadLayer();
    return () => {
      cancelled = true;
      styleLayerRef.current = () => undefined;
      if (dataSource && !activeRuntime.widget.isDestroyed()) activeRuntime.widget.dataSources.remove(dataSource, true);
    };
  }, [activeBoundaryUrl, boundaries, runtimeReady]);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime || !selectedProvince || !boundaries) return;
    const feature = boundaries[mode].features.find((entry) => entry.properties.province === selectedProvince);
    const centroid = feature?.properties.centroid;
    if (centroid) moveCamera({ longitude: centroid.longitude, latitude: centroid.latitude, height: 1_350_000 }, 550);
  }, [boundaries, mode, moveCamera, selectedProvince]);

  const boundaryDescriptor = mode === "gwis"
    ? "Legacy-four display geometry. Kalimantan Timur is one topological union of current East and North Kalimantan."
    : "Current-five display geometry from the frozen geoBoundaries ADM1 subset.";
  const hoverText = hoveredProvince && hoveredRow
    ? `${hoveredProvince}: ${metricLabel(hoveredRow, mode, platform)}`
    : "Hover a boundary to preview; click or tap to pin full details.";
  const selectedSummary = selectedRow && selectedProvince
    ? `${selectedProvince} selected: ${metricLabel(selectedRow, mode, platform)}.`
    : "No province selected.";

  return (
    <section className="globe-card real-globe-card" aria-label="Interactive real-world evidence globe">
      <header className="section-heading">
        <div>
          <h2>{mode === "gwis" ? "Real WGS84 GWIS evidence globe" : "Real WGS84 SiPongi evidence globe"}</h2>
          <p>Actual frozen province geometry on a local NASA Blue Marble Earth surface. Drag to orbit, scroll or pinch to zoom, hover to preview, and click a boundary for full aggregate details.</p>
        </div>
        <span className="layer-key">{mode === "gwis" ? "GWIS legacy four" : "SiPongi current five"}</span>
      </header>
      <div
        ref={hostRef}
        className="real-globe-stage"
        tabIndex={0}
        role="region"
        aria-label={`Interactive real-world ${mode === "gwis" ? "GWIS legacy-four" : "SiPongi current-five"} globe for ${periodLabel}. Use the visible camera controls or the accessible province table below.`}
        onKeyDown={(event) => {
          if (event.key === "Escape") onSelectProvince(null);
          if (event.key === "Home") { event.preventDefault(); focusKalimantan(); }
          if (event.key === "+" || event.key === "=") { event.preventDefault(); zoom(0.72); }
          if (event.key === "-" || event.key === "_") { event.preventDefault(); zoom(1.35); }
        }}
      >
        <div className="globe-visual-badges" aria-hidden="true">
          <span>WGS84 · local imagery</span>
          <span>{boundaryDescriptor}</span>
        </div>
        <aside className={`globe-reading-guide${showMapGuide ? "" : " is-collapsed"}`} aria-label="How to read this map">
          <button
            type="button"
            className="map-guide-toggle"
            aria-expanded={showMapGuide}
            onClick={() => setShowMapGuide((shown) => !shown)}
          >
            {showMapGuide ? "Hide map explanation" : "How to read this map"}
          </button>
          {showMapGuide && (
            <div className="map-guide-content">
              <p className="map-guide-kicker">READ THIS VIEW</p>
              <h3>{mapMetricName(mode, platform)}</h3>
              <dl className="map-guide-facts">
                <div><dt>Period</dt><dd>{periodLabel}</dd></div>
                <div><dt>Boundary units</dt><dd>{mode === "gwis" ? "Four separate legacy reporting polygons" : "Five separate current province polygons"}</dd></div>
                <div><dt>What color means</dt><dd>Each outlined polygon is one reporting unit. More saturated / brighter = a higher source-specific aggregate in this exact view. Contrast is enhanced on a logarithmic display scale; the label and table retain exact values.</dd></div>
              </dl>
              <figure className="map-guide-scale">
                <figcaption className="sr-only">
                  {`Color scale: lower to higher ${mapMetricName(mode, platform)}, from ${valueRange ? compactNumber(valueRange.low) : "unknown"} to ${valueRange ? compactNumber(valueRange.high) : "unknown"} ${mapMetricUnit(mode)}.`}
                </figcaption>
                <span>Lower</span>
                <i className={mode === "gwis" ? "map-color-scale gwis" : "map-color-scale sipongi"} />
                <span>Higher</span>
              </figure>
              <p className="map-guide-range">
                {valueRange
                  ? `${compactNumber(valueRange.low)} to ${compactNumber(valueRange.high)} ${mapMetricUnit(mode)} in the displayed provinces.`
                  : "No source values are available for this view."}
              </p>
              <div className="map-guide-terms">
                {mode === "gwis" ? (
                  <p><strong>Reported hectares</strong> are GWIS&apos;s reported monthly burned-area estimate, summed for July-November. A missing row is not treated as zero.</p>
                ) : (
                  <p><strong>Positive portal record</strong> is one hotspot record returned by SiPongi. It is not a unique fire, ignition, fire rate, or observation-adjusted detection.</p>
                )}
                <p><strong>Unknown coverage</strong> uses the checkered fill: the source does not support a zero claim for that unit/time.</p>
                <p><strong>Important:</strong> this is an aggregate descriptive map. It does not show individual fire locations, fire risk, causal effects, or a comparison between the two source systems.</p>
                {mode === "sipongi" && platform === "All platforms" && (
                  <p><strong>All platforms</strong> combines reported MODIS, S-NPP, and NOAA-20 records; their mix changes over time, so pooled totals are not a uniform trend.</p>
                )}
                {mode === "sipongi" && isPartialSnapshot && (
                  <p><strong>Partial snapshot</strong> ends on the last closed portal-reported day. It is not a completed Jul-Nov season and is excluded from the archive year selector and annual trend chart.</p>
                )}
                {mode === "gwis" && (
                  <p><strong>Legacy East Kalimantan</strong> is displayed as one historical unit that includes today&apos;s North Kalimantan; it is never split between them.</p>
                )}
              </div>
            </div>
          )}
        </aside>
        {!layerReady && !failure && <div className="globe-loading" role="status"><span className="loading-orb" />{loadingText}</div>}
        {failure && <div className="globe-fallback" role="status"><strong>Globe unavailable</strong><span>{failure}</span></div>}
        {hoveredProvince && hoveredRow && !failure && (
          <div className="real-globe-tooltip" style={tooltipPosition} aria-hidden="true">
            <strong>{hoveredProvince}</strong>
            <span>{metricLabel(hoveredRow, mode, platform)}</span>
            <small>{coverageLabel(hoveredRow, mode, isPartialSnapshot)}</small>
          </div>
        )}
      </div>
      <div className="real-globe-controls">
        <div className="globe-control-group" aria-label="Globe camera controls">
          <button type="button" onClick={focusKalimantan} disabled={!runtimeReady}>Focus Kalimantan</button>
          <button type="button" onClick={resetGlobe} disabled={!runtimeReady}>Reset globe</button>
          <button type="button" aria-label="Zoom globe out" onClick={() => zoom(1.35)} disabled={!runtimeReady}>−</button>
          <button type="button" aria-label="Zoom globe in" onClick={() => zoom(0.72)} disabled={!runtimeReady}>+</button>
          <button type="button" onClick={fullscreen} disabled={!runtimeReady}>Fullscreen</button>
          <button type="button" onClick={() => onSelectProvince(null)} disabled={!selectedProvince}>Clear selection</button>
        </div>
        <span>{hoverText}</span>
      </div>
      <div className="globe-data-key" aria-label="Globe legend">
        <span><i className={mode === "gwis" ? "legend-ramp gwis" : "legend-ramp sipongi"} /> Color ramp: lower to higher aggregate for this selected source, period, and year</span>
        <span><i className="legend-hatch" /> Checkered unknown coverage (not zero)</span>
        <span>Polygons are aggregate reporting units, not fire locations or risk areas.</span>
      </div>
      <footer className="globe-footer real-globe-footer">
        <span><strong>Boundary source:</strong> geoBoundaries IDN ADM1, source OpenStreetMap / Wambacher; © OpenStreetMap contributors, ODbL 1.0.</span>
        <span><strong>Earth surface:</strong> NASA Blue Marble. Boundary geometry is a display layer only; it does not replace the still-blocked primary study frame.</span>
      </footer>
      <p className="sr-only" aria-live="polite">{selectedSummary}</p>
    </section>
  );
}
