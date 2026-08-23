"use client";

import { useMemo, useState } from "react";
import { InteractiveGlobe } from "./interactive-globe";
import { GlobalFireGlobe } from "./global-fire-globe";
import type { EvidenceMode, ExplorerData, PeatFireComparison, ProvinceAggregate, SipongiCurrentSnapshot } from "../lib/types";

const CURRENT_FIVE = [
  "Kalimantan Barat",
  "Kalimantan Tengah",
  "Kalimantan Selatan",
  "Kalimantan Timur",
  "Kalimantan Utara",
];

const LEGACY_FOUR = [
  "Kalimantan Barat",
  "Kalimantan Tengah",
  "Kalimantan Selatan",
  "Kalimantan Timur",
];

const number = new Intl.NumberFormat("en-US");
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const decimal = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const SOURCE_LOGOS = [
  { label: "NASA FIRMS", role: "fire detections", href: "https://firms.modaps.eosdis.nasa.gov/", logo: "/brands/nasa.svg", className: "source-logo-nasa" },
  { label: "NOAA CPC", role: "RONI / ENSO", href: "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt", logo: "/brands/noaa.svg", className: "source-logo-noaa" },
  { label: "MapBiomas Indonesia", role: "vegetation context", href: "https://mapbiomas.id/", logo: "/brands/mapbiomas.svg", className: "source-logo-mapbiomas" },
  { label: "Global Forest Watch / WRI", role: "peatland baseline", href: "https://www.globalforestwatch.org/", logo: "/brands/gfw.png", className: "source-logo-gfw" },
  { label: "GWIS / JRC", role: "burned-area context", href: "https://gwis.jrc.ec.europa.eu/", logo: "/brands/gwis.png", className: "source-logo-gwis" },
  { label: "SiPongi / Kemenhut", role: "Indonesia hotspot portal", href: "https://sipongi.gakkum.kehutanan.go.id/sebaran-titik-panas", logo: "/brands/kemenhut.png", className: "source-logo-kemenhut" },
];

function sum(values: readonly number[]) {
  return values.reduce((total, value) => total + value, 0);
}

function sourceAvailableYears(data: ExplorerData, mode: EvidenceMode) {
  const rows = mode === "sipongi" ? data.sipongi_annual : data.gwis_annual;
  return [...new Set(rows.map((row) => row.year))].sort((left, right) => left - right);
}

function formatRoni(value: number | null | undefined) {
  return value === null || value === undefined ? "Unknown" : `${value >= 0 ? "+" : ""}${decimal.format(value)} °C`;
}

function modeLabel(mode: EvidenceMode) {
  return mode === "sipongi" ? "SiPongi current five" : "GWIS legacy four";
}

type SipongiPeriodView = "archive" | "partial_snapshot";

function formatIsoDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
    .format(new Date(`${value}T00:00:00Z`));
}

function snapshotPeriodLabel(snapshot: SipongiCurrentSnapshot) {
  const start = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })
    .format(new Date(`${snapshot.season.start_date}T00:00:00Z`));
  return `${start} to ${formatIsoDate(snapshot.through_date)} (partial)`;
}

interface EvidenceExplorerProps {
  data: ExplorerData;
}

export function EvidenceExplorer({ data }: EvidenceExplorerProps) {
  const currentSnapshot = data.sipongi_current_snapshot ?? null;
  const [mode, setMode] = useState<EvidenceMode>("sipongi");
  const [year, setYear] = useState(data.scope.sipongi_years[1]);
  const [platform, setPlatform] = useState("All platforms");
  const [sipongiPeriodView, setSipongiPeriodView] = useState<SipongiPeriodView>(currentSnapshot ? "partial_snapshot" : "archive");
  const [selectedProvince, setSelectedProvince] = useState<string | null>(null);
  const [limitationsOpen, setLimitationsOpen] = useState(false);

  const availableYears = useMemo(() => sourceAvailableYears(data, mode), [data, mode]);
  const selectedYearIndex = Math.max(0, availableYears.indexOf(year));
  const isPartialSnapshot = mode === "sipongi" && sipongiPeriodView === "partial_snapshot" && currentSnapshot !== null;
  const displayPeriod = isPartialSnapshot && currentSnapshot
    ? snapshotPeriodLabel(currentSnapshot)
    : `Jul-Nov ${year}`;

  const provinceRows = useMemo<ProvinceAggregate[]>(() => {
    if (mode === "gwis") {
      return LEGACY_FOUR.map((province) => {
        const row = data.gwis_province.find((candidate) => candidate.year === year && candidate.province === province);
        return {
          province,
          value: row?.burned_area_ha ?? null,
          fireCount: row?.fire_count ?? null,
          observed: row?.observed_months ?? 0,
          expected: row?.expected_months ?? 5,
          isUnknown: !row || row.observed_months < row.expected_months,
        };
      });
    }
    return CURRENT_FIVE.map((province) => {
      const records = isPartialSnapshot
        ? currentSnapshot!.province_platform_counts.filter(
          (candidate) => candidate.province === province && (platform === "All platforms" || candidate.platform === platform),
        )
        : data.sipongi_annual.filter(
          (candidate) => candidate.year === year && candidate.province === province && (platform === "All platforms" || candidate.platform === platform),
        );
      return {
        province,
        value: sum(records.map((candidate) => candidate.record_count)),
        observed: isPartialSnapshot ? 1 : records.length > 0 ? 5 : 0,
        expected: isPartialSnapshot ? 1 : 5,
        isUnknown: false,
      };
    });
  }, [currentSnapshot, data.gwis_province, data.sipongi_annual, isPartialSnapshot, mode, platform, year]);

  const currentGwis = data.gwis_annual.find((candidate) => candidate.year === year);
  const currentRoni = data.roni_annual.find((candidate) => candidate.year === year);
  const selectedRow = provinceRows.find((row) => row.province === selectedProvince) ?? null;
  const total = sum(provinceRows.flatMap((row) => row.value === null ? [] : [row.value]));
  const observedRows = sum(provinceRows.map((row) => row.observed));
  const expectedRows = sum(provinceRows.map((row) => row.expected));

  const jumpToGlobalComparison = () => {
    const target = document.getElementById("global-comparison");
    if (!target) return;
    target.scrollIntoView({ behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  };

  const chooseMode = (nextMode: EvidenceMode) => {
    const nextYears = sourceAvailableYears(data, nextMode);
    setMode(nextMode);
    setYear(nextYears.at(-1) ?? year);
    if (nextMode === "sipongi" && currentSnapshot) setSipongiPeriodView("partial_snapshot");
    setSelectedProvince(null);
  };

  const chooseYear = (nextYear: number) => {
    if (!availableYears.includes(nextYear)) return;
    setYear(nextYear);
    setSelectedProvince(null);
  };

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand-block">
          <span className="eyebrow">Global + Kalimantan wildfire research · evidence explorer</span>
          <h1>{data.title}</h1>
        </div>
        <div className="header-status" aria-label="Research status">
          <span className="status-dot" />
          <span>{data.display_status.label}</span>
          <strong>{data.display_status.primary_association}</strong>
        </div>
      </header>

      <section className="source-strip" aria-labelledby="source-strip-heading">
        <div className="source-strip-heading">
          <span className="eyebrow" id="source-strip-heading">Data taken from</span>
          <p>Source marks identify the datasets represented in this bundle; they are attribution only, not endorsements.</p>
        </div>
        <div className="source-logo-list">
          {SOURCE_LOGOS.map((source) => (
            <a key={source.label} className="source-logo-chip" href={source.href} target="_blank" rel="noreferrer" title={`${source.label} — ${source.role}`}>
              <span className={`source-logo-frame ${source.className}`}><img src={source.logo} alt={`${source.label} logo`} /></span>
              <span><strong>{source.label}</strong><small>{source.role}</small></span>
            </a>
          ))}
          <span className="source-text-chip"><strong>CHIRPS · GWIS · SiPongi</strong><small>rainfall and portal aggregates</small></span>
        </div>
      </section>

      <section className="hero-grid" aria-labelledby="purpose-heading">
        <div>
          <p className="eyebrow">Interactive aggregate context — not a fire-risk map</p>
          <h2 id="purpose-heading">Explore what the currently acquired evidence can support.</h2>
          <p className="hero-copy">The default globe is a WGS84 country layer covering the frozen global boundary set, colored only by aggregate satellite detection records or peatland share. The Kalimantan province layer remains separate because SiPongi and GWIS use incompatible local reporting units.</p>
          <div className="coverage-callout" aria-label="Geographic coverage">
            <div><strong>Local layer</strong><span>5 current / 4 legacy Kalimantan units</span></div>
            <div><strong>Global layer</strong><span>{data.peat_fire_comparison?.matched_country_count ?? 0} matched countries</span></div>
            <button type="button" onClick={jumpToGlobalComparison}>Focus global globe ↓</button>
          </div>
        </div>
        <div className="guardrail-card">
          <span className="guardrail-label">Primary association</span>
          <strong>{data.display_status.primary_association}</strong>
          <p>Phase 1 is still blocked by {data.display_status.blocked_assets.length} required asset groups. The controls below change descriptive context only.</p>
          <button type="button" className="text-button" onClick={() => setLimitationsOpen(true)}>Read evidence boundaries</button>
        </div>
      </section>

      {data.peat_fire_comparison && <PeatFireComparisonPanel comparison={data.peat_fire_comparison} latestGlobalFire={data.latest_global_fire} />}

      <section className="navigator-card" aria-label="Explorer controls">
        <div className="control-cluster">
          <span className="field-label">Evidence layer</span>
          <div className="segmented-control" role="group" aria-label="Evidence layer">
            <button type="button" className={mode === "sipongi" ? "is-selected" : ""} onClick={() => chooseMode("sipongi")}>SiPongi current five</button>
            <button type="button" className={mode === "gwis" ? "is-selected" : ""} onClick={() => chooseMode("gwis")}>GWIS legacy four</button>
          </div>
        </div>
        {!isPartialSnapshot && <label className="control-cluster year-control">
          <span className="field-label">Year</span>
          <div className="year-picker">
            <button type="button" aria-label="Previous year" disabled={selectedYearIndex === 0} onClick={() => chooseYear(availableYears[selectedYearIndex - 1])}>←</button>
            <input type="range" min={0} max={Math.max(0, availableYears.length - 1)} value={selectedYearIndex} onChange={(event) => chooseYear(availableYears[Number(event.target.value)])} aria-label="Evidence year" />
            <button type="button" aria-label="Next year" disabled={selectedYearIndex === availableYears.length - 1} onClick={() => chooseYear(availableYears[selectedYearIndex + 1])}>→</button>
            <output aria-live="polite">{year}</output>
          </div>
        </label>}
        {mode === "sipongi" && (
          <label className="control-cluster platform-control">
            <span className="field-label">Platform</span>
            <select value={platform} onChange={(event) => { setPlatform(event.target.value); setSelectedProvince(null); }}>
              <option>All platforms</option>
              {data.sipongi_platforms.map((entry) => <option key={entry}>{entry}</option>)}
            </select>
          </label>
        )}
        {mode === "sipongi" && currentSnapshot && (
          <div className="control-cluster period-control">
            <span className="field-label">SiPongi period</span>
            <div className="segmented-control" role="group" aria-label="SiPongi period view">
              <button
                type="button"
                className={sipongiPeriodView === "partial_snapshot" ? "is-selected" : ""}
                onClick={() => { setSipongiPeriodView("partial_snapshot"); setSelectedProvince(null); }}
              >
                Latest closed-day snapshot
              </button>
              <button
                type="button"
                className={sipongiPeriodView === "archive" ? "is-selected" : ""}
                onClick={() => { setSipongiPeriodView("archive"); setSelectedProvince(null); }}
              >
                Completed seasons
              </button>
            </div>
          </div>
        )}
        <div className="source-badge">
          <span>Boundary system</span>
          <strong>{modeLabel(mode)}</strong>
        </div>
      </section>

      <section className="metric-grid" aria-label="Current context metrics">
        <article className="metric-card">
          <span>{mode === "gwis" ? "Reported burned area" : isPartialSnapshot ? "Latest positive portal records" : "Positive portal records"}</span>
          <strong>{mode === "gwis" ? `${compact.format(total)} ha` : number.format(total)}</strong>
          <small>{mode === "gwis" ? "Jul–Nov, rows with observed source data only" : isPartialSnapshot ? `${platform} · ${displayPeriod} · closed-day partial monitor, not fires or ignitions` : `${platform} · Jul–Nov · records, not fires or ignitions`}</small>
        </article>
        <article className="metric-card climate">
          <span>{isPartialSnapshot ? "Latest RONI context" : "RONI seasonal context"}</span>
          <strong>{formatRoni(isPartialSnapshot ? data.latest_roni?.anomaly_c : currentRoni?.mean_aug_nov_c ?? currentGwis?.roni_aug_nov_c)}</strong>
          <small>{isPartialSnapshot ? `${data.latest_roni?.season ?? "Latest"} ${data.latest_roni?.season_year ?? ""}, ending ${data.latest_roni ? formatIsoDate(data.latest_roni.end_date) : "unknown"}; provisional and not a same-period fire-season mean.` : "Mean of 3-month seasons ending Aug–Nov; not a monthly El Niño wave."}</small>
        </article>
        <article className="metric-card coverage">
          <span>{mode === "gwis" ? "Reported row coverage" : "Source-bounded provinces"}</span>
          <strong>{mode === "gwis" ? `${observedRows} / ${expectedRows}` : "5 / 5"}</strong>
          <small>{mode === "gwis" ? "Missing source rows remain unknown, never zero." : isPartialSnapshot ? "Five validated provincial responses; no observation denominator." : "Current five-province source system."}</small>
        </article>
        <article className="metric-card status">
          <span>Research readiness</span>
          <strong>Phase 1 gated</strong>
          <small>Exact-overpass outcome and covariate sources are not yet locally validated.</small>
        </article>
      </section>

      <div className="map-scope-heading">
        <div><span className="eyebrow">Local reporting layer</span><h2>Kalimantan province evidence</h2><p>These polygons represent reporting units and their aggregates—not areas that are all burned.</p></div>
        <button type="button" className="text-button" onClick={jumpToGlobalComparison}>Compare other countries ↓</button>
      </div>
      <section className="globe-layout" aria-label="Kalimantan evidence globe and selected-region summary">
        <InteractiveGlobe
          mode={mode}
          platform={platform}
          periodLabel={displayPeriod}
          isPartialSnapshot={isPartialSnapshot}
          rows={provinceRows}
          selectedProvince={selectedProvince}
          onSelectProvince={setSelectedProvince}
        />
        <aside className="selection-card" aria-live="polite">
          <span className="eyebrow">Selected aggregate</span>
          {selectedRow ? (
            <>
              <span className="selection-kind">{mode === "gwis" ? "Legacy aggregate reporting unit" : isPartialSnapshot ? "Current partial monitoring unit" : "Current aggregate reporting unit"}</span>
              <h2>{selectedRow.province}</h2>
              <strong className="selection-value">{selectedRow.isUnknown ? "Unknown" : mode === "gwis" ? `${number.format(selectedRow.value ?? 0)} ha` : number.format(selectedRow.value ?? 0)}</strong>
              <p>{selectedRow.isUnknown
                ? "At least one Jul–Nov source row is absent. This is not evidence of zero burned area or zero fires."
                : mode === "gwis"
                  ? `${number.format(selectedRow.fireCount ?? 0)} reported counts; ${selectedRow.observed} of ${selectedRow.expected} season-month rows were present.`
                  : `${platform} positive portal records from ${displayPeriod}. ${isPartialSnapshot ? "This is a closed-day partial monitor, not a completed season or a comparable annual trend value." : "These are not individual fires, ignitions, or an observation-adjusted rate."}`}</p>
              <dl className="selection-details">
                <div><dt>Layer</dt><dd>{mode === "gwis" ? "GWIS legacy-four aggregate" : "SiPongi current-five aggregate"}</dd></div>
                <div><dt>Season support</dt><dd>{displayPeriod}</dd></div>
                <div><dt>Geometry</dt><dd>{mode === "gwis" && selectedRow.province === "Kalimantan Timur" ? "One topological union of current East and North Kalimantan." : "Frozen geoBoundaries ADM1 display geometry."}</dd></div>
                <div><dt>Interpretation</dt><dd>Aggregate context only - not fire occurrence, causal effect, or risk.</dd></div>
              </dl>
              <button type="button" className="text-button" onClick={() => setSelectedProvince(null)}>Clear selection</button>
            </>
          ) : (
            <>
              <h2>Choose a province</h2>
              <p>Click or tap a real frozen province boundary on the WGS84 globe, or use the accessible province table below. The geometry is an aggregate reporting layer, not a hotspot, event, or exposure location.</p>
              <div className="selection-key">
                <span><i className="dot sipongi" /> SiPongi current-five reporting polygons</span>
                <span><i className="dot gwis" /> GWIS legacy-four reporting polygons</span>
                <span><i className="dot unknown" /> Unknown source-row coverage, never zero</span>
              </div>
            </>
          )}
        </aside>
      </section>

      {isPartialSnapshot && currentSnapshot ? (
        <section className="monitoring-caution" aria-label="Partial snapshot interpretation">
          <span className="eyebrow">Latest portal monitor</span>
          <h2>Not part of the completed-season trend</h2>
          <p>This view stops on the last closed portal-reported date, {formatIsoDate(currentSnapshot.through_date)}. It is deliberately excluded from the year slider, annual trend chart, July-November comparison, and August-November RONI mean.</p>
          <p>Use it to inspect the current aggregate portal response only. It is not a fire rate, a detection-adjusted count, a forecast, a risk surface, or a causal result.</p>
        </section>
      ) : (
        <section className="support-grid" aria-label="Trend context">
          <AnnualContextChart data={data} mode={mode} platform={platform} selectedYear={year} onSelectYear={chooseYear} />
          <MonthlyContextChart data={data} mode={mode} platform={platform} selectedYear={year} />
        </section>
      )}

      <ConditionalPeatHypothesisPanel audit={data.condition_phase_audit ?? null} />

      <section className="table-card" aria-labelledby="province-table-heading">
        <div className="section-heading">
          <div>
            <h2 id="province-table-heading">Province aggregate table</h2>
            <p>Keyboard-accessible alternative to the canvas. The two boundary systems cannot be merged or directly totalled.</p>
          </div>
          <span className="layer-key">{modeLabel(mode)}</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Province</th>
                <th scope="col">{mode === "gwis" ? "Reported burned area" : "Positive portal records"}</th>
                <th scope="col">{mode === "gwis" ? "Reported count" : "Platform"}</th>
                <th scope="col">Coverage / interpretation</th>
              </tr>
            </thead>
            <tbody>
              {provinceRows.map((row) => (
                <tr key={row.province} className={selectedProvince === row.province ? "is-selected" : ""}>
                  <th scope="row"><button type="button" className="province-button" onClick={() => setSelectedProvince(row.province)}>{row.province}</button></th>
                  <td>{row.isUnknown ? "Unknown" : mode === "gwis" ? `${number.format(row.value ?? 0)} ha` : number.format(row.value ?? 0)}</td>
                  <td>{mode === "gwis" ? (row.isUnknown ? "Unknown" : number.format(row.fireCount ?? 0)) : platform}</td>
                  <td>{row.isUnknown ? "Missing source row(s); never interpreted as zero." : mode === "gwis" ? `${row.observed}/${row.expected} Jul–Nov rows present` : isPartialSnapshot ? `Validated through ${currentSnapshot ? formatIsoDate(currentSnapshot.through_date) : "the closed portal date"}; partial monitor, no observation denominator` : "Portal-reported aggregate; no observation denominator"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="provenance-card" aria-labelledby="provenance-heading">
        <div className="section-heading">
          <div>
            <h2 id="provenance-heading">Data provenance and safeguards</h2>
            <p>Every browser-visible value comes from the frozen aggregate evidence bundle generated by the research pipeline.</p>
          </div>
          <span className="layer-key">Ledger valid · {data.ledger.entry_count} entries</span>
        </div>
        <div className="provenance-grid">
          {data.provenance.map((source) => (
            <article key={source.id}>
              <span>{source.label}</span>
              <strong>{source.record_count === "" ? "Context source" : number.format(Number(source.record_count))} records</strong>
              <p>{source.analysis_limit}</p>
              <a href={source.source_url} target="_blank" rel="noreferrer">Open source record ↗</a>
            </article>
          ))}
        </div>
      </section>

      <footer className="app-footer">
        <span>Generated {new Date(data.generated_at_utc).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" })} UTC</span>
        <button type="button" className="text-button" onClick={() => setLimitationsOpen(true)}>Evidence boundaries</button>
      </footer>

      {limitationsOpen && (
        <div className="dialog-backdrop" role="presentation" onMouseDown={() => setLimitationsOpen(false)}>
          <section className="method-dialog" role="dialog" aria-modal="true" aria-labelledby="limitations-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="dialog-heading">
              <div>
                <span className="eyebrow">Method guardrails</span>
                <h2 id="limitations-title">What this explorer does not claim</h2>
              </div>
              <button type="button" className="close-button" onClick={() => setLimitationsOpen(false)} aria-label="Close evidence boundaries">×</button>
            </div>
            <ul>
              {data.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
            </ul>
            <p className="blocked-assets"><strong>Blocked Phase 1 asset groups:</strong> {data.display_status.blocked_assets.join(", ")}.</p>
            <button type="button" className="primary-button" onClick={() => setLimitationsOpen(false)}>I understand</button>
          </section>
        </div>
      )}
    </main>
  );
}

function PeatFireComparisonPanel({ comparison, latestGlobalFire }: { comparison: PeatFireComparison; latestGlobalFire?: ExplorerData["latest_global_fire"] }) {
  const model = comparison.primary_fixed_effect_model;
  const ci = model.ci95 ?? [null, null];
  const p = model.p_two_sided;
  const countries = comparison.countries.filter((row) => Number.isFinite(row.total_detection_rate_per_1000_km2));
  const maxShare = Math.max(1, ...countries.map((row) => row.peat_share_percent));
  const maxRate = Math.max(1, ...countries.map((row) => Math.log10(1 + row.total_detection_rate_per_1000_km2)));
  const width = 720;
  const height = 265;
  const pad = { left: 56, right: 22, top: 18, bottom: 43 };
  // Serialize plotted coordinates to a fixed precision. Without this, the
  // server and browser can stringify the same floating-point calculation with
  // different trailing digits, which causes a React hydration mismatch on the
  // SVG circles (the visual difference is zero, but the DOM attributes differ).
  const x = (share: number) => (pad.left + Math.min(1, share / maxShare) * (width - pad.left - pad.right)).toFixed(6);
  const y = (rate: number) => (height - pad.bottom - (Math.log10(1 + Math.max(0, rate)) / maxRate) * (height - pad.top - pad.bottom)).toFixed(6);
  return (
    <section id="global-comparison" className="peat-fire-card" aria-labelledby="peat-fire-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Global comparison · completed 2024 fire year</span>
          <h2 id="peat-fire-heading">Does peatland show more fire detections?</h2>
          <p>
            The chart remains the completed-2024 scientific comparison. The globe below defaults to the latest validated closed-day FIRMS NRT snapshot when available. Peatland is a mapped baseline exposure area; each circle is a country-level aggregate of NASA MODIS active-fire detections. A coloured country area is not a claim that the whole country burned, and the points are not a complete inventory of fires.
          </p>
        </div>
        <span className="layer-key">Exploratory · not causal</span>
      </div>
      <div className="peat-fire-grid">
        <div className="peat-fire-plot-wrap">
          <svg className="peat-fire-plot" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Country peatland share versus log-scaled MODIS active-fire detections per 1000 square kilometres">
            {[0, 0.5, 1].map((fraction) => {
              const yy = height - pad.bottom - fraction * (height - pad.top - pad.bottom);
              return <line key={fraction} x1={pad.left} x2={width - pad.right} y1={yy} y2={yy} className="chart-gridline" />;
            })}
            <line x1={pad.left} x2={width - pad.right} y1={height - pad.bottom} y2={height - pad.bottom} className="peat-axis" />
            <line x1={pad.left} x2={pad.left} y1={pad.top} y2={height - pad.bottom} className="peat-axis" />
            {countries.map((row) => (
              <circle key={row.country_id} cx={x(row.peat_share_percent)} cy={y(row.total_detection_rate_per_1000_km2)} r="3.5" className="peat-point" tabIndex={0} role="img" aria-label={`${row.country}: ${row.peat_share_percent.toFixed(1)}% peatland; ${row.total_detection_rate_per_1000_km2.toFixed(2)} detections per 1,000 square kilometres`}>
                <title>{`${row.country}: ${row.peat_share_percent.toFixed(1)}% peatland; ${row.total_detection_rate_per_1000_km2.toFixed(2)} detections/1,000 km²`}</title>
              </circle>
            ))}
            <text x={width / 2} y={height - 8} textAnchor="middle" className="peat-axis-label">Country peatland share (%)</text>
            <text transform={`translate(14 ${height / 2}) rotate(-90)`} textAnchor="middle" className="peat-axis-label">MODIS detections / 1,000 km² (log scale)</text>
          </svg>
          <p className="chart-note">Each dot is one of {comparison.matched_country_count} matched countries. The chart is descriptive; it has no observation-opportunity denominator.</p>
        </div>
        <div className="peat-fire-summary">
          <div className="peat-stat"><span>Primary test</span><strong>≥{comparison.primary_threshold_percent}% peat extent</strong><small>Country fixed-effects Poisson model with log(area) offset.</small></div>
          <div className="peat-stat"><span>Adjusted rate ratio</span><strong>{model.rate_ratio?.toFixed(2) ?? "Unknown"}</strong><small>95% CI {ci[0] === null ? "Unknown" : `${ci[0].toFixed(2)}–${ci[1]?.toFixed(2)}`} · p={p === null || p === undefined ? "Unknown" : p.toFixed(3)}</small></div>
          <div className="peat-stat"><span>Interpretation</span><strong>{p !== null && p !== undefined && p < 0.05 ? "Evidence of association" : "Not statistically significant"}</strong><small>CI includes 1, so this test does not establish higher detection in peatland.</small></div>
        </div>
      </div>
      <GlobalFireGlobe comparison={comparison} latestGlobalFire={latestGlobalFire} />
      <div className="peat-threshold-table-wrap">
        <h3>Threshold sensitivity</h3>
        <p className="table-explainer">The conclusion is unchanged when “peatland” is defined as a cell with at least 25%, 50%, or 75% peat extent.</p>
        <table className="peat-threshold-table">
          <thead><tr><th>Definition</th><th>Adjusted RR</th><th>95% CI</th><th>p-value</th></tr></thead>
          <tbody>{comparison.threshold_sensitivity.map((row) => <tr key={row.threshold_percent}>
            <th scope="row">≥{row.threshold_percent}% peat extent</th>
            <td>{row.fixed_effect_rate_ratio?.toFixed(2) ?? "Unknown"}</td>
            <td>{row.fixed_effect_ci95 ? `${row.fixed_effect_ci95[0].toFixed(2)}–${row.fixed_effect_ci95[1].toFixed(2)}` : "Unknown"}</td>
            <td>{row.fixed_effect_p_two_sided === null || row.fixed_effect_p_two_sided === undefined ? "Unknown" : row.fixed_effect_p_two_sided.toFixed(3)}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <details className="peat-fire-method">
        <summary>How to read this correctly</summary>
        <ul>
          <li>Peat source: latest global ensemble release (24 Apr 2026), but its mapped reference period is 2000–2020—not a 2026 land-cover observation.</li>
          <li>Fire source: 2024 NASA FIRMS MODIS Collection 6.1 standard archive, presumed vegetation-fire detections with confidence ≥30.</li>
          <li>“Detection” means a satellite thermal detection, not a unique fire, burned-area polygon, or fire probability. Cloud, orbit, sensor, land management, and spatial confounding remain.</li>
          <li>This is a country-level association test. It cannot prove that peat causes fire or that peatland is less vulnerable when the ratio is below 1.</li>
        </ul>
      </details>
    </section>
  );
}

function ConditionalPeatHypothesisPanel({ audit }: { audit: ExplorerData["condition_phase_audit"] }) {
  const conditions = [
    ["Dry hydrology", "Low soil moisture or a low water table removes peat’s water protection."],
    ["Drainage pressure", "Canals and ditches can make peat dry, especially near disturbed edges."],
    ["Stressed vegetation", "Low pre-fire NDMI/EVI can indicate drier live fuel and degraded cover."],
    ["Fire weather", "Rainfall deficit, high VPD, wind, and an ignition source can align in the same window."],
  ];
  return (
    <section className="condition-card" aria-labelledby="condition-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Next hypothesis · condition effect</span>
          <h2 id="condition-heading">Peatland may become vulnerable only under the right conditions</h2>
          <p>The global test above averages intact, wet, drained, degraded, and dry peat together. A null average does not rule out a strong effect in a dry or disturbed subset.</p>
        </div>
        <span className="layer-key">{audit?.condition_phase_ready ? "Ready for design matrix" : "Blocked · inputs missing"}</span>
      </div>
      <div className="condition-grid">
        {conditions.map(([title, description]) => <article key={title} className="condition-item"><strong>{title}</strong><p>{description}</p></article>)}
      </div>
      <div className="condition-footer">
        <code>fire ~ peat + condition + peat × condition + observation opportunity</code>
        <span>Target: interaction term, not a main “peat is dangerous” coefficient. {audit ? `Audit: ${Object.values(audit.assets).filter((status) => status === "blocked").length} input groups blocked.` : "Audit not loaded."}</span>
      </div>
      {audit?.temporal_support && (
        <div className="condition-temporal-status" role="status">
          <strong>Phase 1 temporal QA:</strong> {audit.temporal_support.status.replaceAll("_", " ")} · denominator unlock: {audit.temporal_support.phase_1_unlock ? "yes" : "no"}.
          <span>ERA5: {audit.temporal_support.assets.era5_land?.replaceAll("_", " ") ?? "unknown"}; CHIRPS: {audit.temporal_support.assets.chirps?.replaceAll("_", " ") ?? "unknown"}; VIIRS: {audit.temporal_support.assets.viirs_outcome_and_opportunity?.replaceAll("_", " ") ?? "unknown"}.</span>
        </div>
      )}
    </section>
  );
}

interface AnnualContextChartProps {
  data: ExplorerData;
  mode: EvidenceMode;
  platform: string;
  selectedYear: number;
  onSelectYear: (year: number) => void;
}

function AnnualContextChart({ data, mode, platform, selectedYear, onSelectYear }: AnnualContextChartProps) {
  const rows = mode === "gwis"
    ? data.gwis_annual.map((row) => ({ year: row.year, value: row.burned_area_ha, roni: row.roni_aug_nov_c }))
    : Array.from(new Set(data.sipongi_annual.map((row) => row.year))).sort((a, b) => a - b).map((entryYear) => ({
      year: entryYear,
      value: sum(data.sipongi_annual.filter((row) => row.year === entryYear && (platform === "All platforms" || row.platform === platform)).map((row) => row.record_count)),
      roni: data.roni_annual.find((row) => row.year === entryYear)?.mean_aug_nov_c ?? null,
    }));
  const width = 680;
  const height = 208;
  const pad = { left: 42, right: 16, top: 18, bottom: 30 };
  const max = Math.max(1, ...rows.map((row) => row.value));
  const minYear = rows[0]?.year ?? selectedYear;
  const maxYear = rows.at(-1)?.year ?? selectedYear;
  const position = (entryYear: number, value: number) => ({
    x: pad.left + ((entryYear - minYear) / Math.max(1, maxYear - minYear)) * (width - pad.left - pad.right),
    y: height - pad.bottom - (value / max) * (height - pad.top - pad.bottom),
  });
  const polyline = rows.map((row) => {
    const point = position(row.year, row.value);
    return `${point.x},${point.y}`;
  }).join(" ");
  const title = mode === "gwis"
    ? "GWIS aggregate context, 2002–2024"
    : `SiPongi completed-season context, ${minYear}–${maxYear}`;
  return (
    <article className="chart-card">
      <div className="section-heading compact-heading">
        <div>
          <h2>{title}</h2>
          <p>{mode === "gwis" ? "Reported seasonal burned area; incomplete rows are not replaced with zero." : `${platform} portal records; sensor mix changes across years.`}</p>
        </div>
      </div>
      <svg className="context-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        {[0.25, 0.5, 0.75, 1].map((fraction) => {
          const y = height - pad.bottom - fraction * (height - pad.top - pad.bottom);
          return <line key={fraction} x1={pad.left} x2={width - pad.right} y1={y} y2={y} className="chart-gridline" />;
        })}
        <polyline points={polyline} className={mode === "gwis" ? "chart-line gwis-line" : "chart-line sipongi-line"} />
        {rows.map((row) => {
          const point = position(row.year, row.value);
          return <g key={row.year} className="chart-point-group" onClick={() => onSelectYear(row.year)}>
            <circle cx={point.x} cy={point.y} r={row.year === selectedYear ? 6 : 3.5} className={row.year === selectedYear ? "chart-point is-active" : "chart-point"} />
            <title>{`${row.year}: ${mode === "gwis" ? `${number.format(row.value)} ha` : number.format(row.value)}; RONI ${formatRoni(row.roni)}`}</title>
          </g>;
        })}
        <text x={pad.left} y={height - 8}>{minYear}</text>
        <text x={width - pad.right} y={height - 8} textAnchor="end">{maxYear}</text>
        <text x={pad.left} y={pad.top - 4}>{compact.format(max)}</text>
      </svg>
      <div className="chart-note"><span className="chart-swatch" /> Select a point to change the explorer year. RONI is shown in the accessible hover label only; the line metric is source-specific.</div>
    </article>
  );
}

interface MonthlyContextChartProps {
  data: ExplorerData;
  mode: EvidenceMode;
  platform: string;
  selectedYear: number;
}

function MonthlyContextChart({ data, mode, platform, selectedYear }: MonthlyContextChartProps) {
  const months = [7, 8, 9, 10, 11];
  const sipongiValues = months.map((month) => sum(
    data.sipongi_monthly
      .filter((row) => row.year === selectedYear && row.month === month && (platform === "All platforms" || row.platform === platform))
      .map((row) => row.record_count),
  ));
  const max = Math.max(1, ...sipongiValues);
  const names = ["Jul", "Aug", "Sep", "Oct", "Nov"];
  const title = mode === "sipongi" ? `${selectedYear} SiPongi seasonal distribution` : `${selectedYear} GWIS coverage caution`;
  return (
    <article className="chart-card monthly-card">
      <div className="section-heading compact-heading">
        <div>
          <h2>{title}</h2>
          <p>{mode === "sipongi" ? "Positive portal records by month, not an observation-adjusted frequency." : "GWIS annual province totals only; monthly disaggregation is intentionally not inferred."}</p>
        </div>
      </div>
      {mode === "sipongi" ? (
        <div className="month-bars" aria-label={`${selectedYear} monthly positive portal record distribution`}>
          {sipongiValues.map((value, index) => (
            <div className="month-bar" key={months[index]}>
              <span className="bar-value">{compact.format(value)}</span>
              <div className="bar-track"><div className="bar-fill" style={{ height: `${(value / max) * 100}%` }} /></div>
              <span>{names[index]}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="caution-panel"><span>Missingness protected</span><strong>Monthly GWIS values are not interpolated.</strong><p>The public bundle preserves reported province-season aggregates and source-row coverage. It does not derive a false monthly pattern from annual totals.</p></div>
      )}
    </article>
  );
}
