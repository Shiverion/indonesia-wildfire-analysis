import { access, copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

const source = fileURLToPath(
  new URL("../../../outputs/evidence-explorer/evidence-explorer.json", import.meta.url),
);
const destination = fileURLToPath(
  new URL("../data/evidence-explorer.json", import.meta.url),
);
const receipt = fileURLToPath(
  new URL("../data/evidence-explorer.receipt.json", import.meta.url),
);

try {
  await access(source);
} catch {
  throw new Error(
    "Missing aggregate evidence bundle. Run `python scripts/research.py build-explorer` from the repository root first.",
  );
}

const text = await readFile(source, "utf8");
const data = JSON.parse(text);
const prohibited = ["latitude", "longitude", "district", "subdistrict", "village", "reported_time", "source_file", "source_sha256"];
const serialised = JSON.stringify(data).toLowerCase();
const leaked = prohibited.filter((field) => serialised.includes(`\"${field}\"`));
if (leaked.length) {
  throw new Error(`Refusing to copy a browser bundle with prohibited fields: ${leaked.join(", ")}`);
}
if (data?.display_status?.primary_association !== "NI - Not identifiable") {
  throw new Error("Explorer source bundle lost its primary-association guardrail.");
}
if (data?.display_status?.phase_1_ready !== false) {
  throw new Error("Explorer source bundle no longer represents a blocked Phase 1 analysis.");
}
if (data?.quality?.sipongi?.raw_records_embedded !== false) {
  throw new Error("Explorer source bundle must not contain raw SiPongi records.");
}
if ([...(data?.sipongi_annual ?? []), ...(data?.sipongi_monthly ?? [])].some((row) => row?.year === 2024)) {
  throw new Error("Explorer source bundle must not expose quarantined 2024 SiPongi responses.");
}
const peatFire = data?.peat_fire_comparison;
if (peatFire) {
  if (peatFire.status !== "exploratory_association_not_causal" || peatFire.analysis_year !== 2024 || peatFire.peat_reference_period !== "2000-2020") {
    throw new Error("Peat/fire comparison must remain a 2024 exploratory test against the 2000-2020 peat baseline.");
  }
  if (!Array.isArray(peatFire.countries) || peatFire.countries.length < 100) {
    throw new Error("Peat/fire comparison must contain the matched global country aggregates.");
  }
  if (JSON.stringify(peatFire).match(/"(latitude|longitude|acq_time|reported_time|source_file|source_sha256|firm_file)"/i)) {
    throw new Error("Peat/fire browser data must not contain detection-level or local-file fields.");
  }
  if (JSON.stringify(peatFire.threshold_sensitivity?.map((row) => row.threshold_percent)) !== JSON.stringify([25, 50, 75])) {
    throw new Error("Peat/fire comparison must include ordered 25/50/75% sensitivities.");
  }
}
const conditionAudit = data?.condition_phase_audit;
if (conditionAudit) {
  if (conditionAudit.schema_version !== "condition-phase-audit/v1" || conditionAudit.condition_phase_ready !== false) {
    throw new Error("Condition audit must remain a blocked, aggregate-only browser status.");
  }
  if (!conditionAudit.assets || Object.values(conditionAudit.assets).length < 4) {
    throw new Error("Condition audit must expose the required asset-group statuses.");
  }
}
const snapshot = data?.sipongi_current_snapshot;
if (snapshot !== undefined && snapshot !== null) {
  const guardrail = snapshot?.comparison_guardrail;
  const validation = snapshot?.validation;
  const requiredFalse = [
    "included_in_annual_archive",
    "eligible_for_year_slider",
    "eligible_for_annual_chart",
    "comparable_to_completed_jul_nov_seasons",
  ];
  if (snapshot?.status !== "validated_partial" || snapshot?.season?.complete !== false) {
    throw new Error("Current SiPongi snapshot must be explicitly validated and partial.");
  }
  if (requiredFalse.some((key) => guardrail?.[key] !== false)) {
    throw new Error("Current SiPongi snapshot lost a required comparison guardrail.");
  }
  if (validation?.expected_province_responses !== 5 || validation?.validated_province_responses !== 5) {
    throw new Error("Current SiPongi snapshot does not have five validated province responses.");
  }
  if (validation?.raw_records_embedded !== false || validation?.has_observation_denominator !== false) {
    throw new Error("Current SiPongi snapshot must stay aggregate-only without an observation denominator.");
  }
  const counts = snapshot?.province_platform_counts;
  if (!Array.isArray(counts) || counts.length !== 20 || counts.some((row) => !Number.isInteger(row?.record_count) || row.record_count < 0)) {
    throw new Error("Current SiPongi snapshot must contain a dense nonnegative 5x4 aggregate count grid.");
  }
  if (counts.reduce((total, row) => total + row.record_count, 0) !== snapshot?.total_record_count) {
    throw new Error("Current SiPongi snapshot aggregate counts do not conserve the source total.");
  }
}

await mkdir(fileURLToPath(new URL("../data", import.meta.url)), { recursive: true });
await copyFile(source, destination);
const sha256 = createHash("sha256").update(text).digest("hex");
await writeFile(receipt, `${JSON.stringify({
  source: "../../../outputs/evidence-explorer/evidence-explorer.json",
  source_sha256: sha256,
  synchronized_at_utc: new Date().toISOString(),
  primary_association: data.display_status.primary_association,
  phase_1_ready: data.display_status.phase_1_ready,
  raw_sipongi_records_embedded: data.quality.sipongi.raw_records_embedded,
  sipongi_current_snapshot: snapshot ? {
    snapshot_id: snapshot.snapshot_id,
    through_date: snapshot.through_date,
    total_record_count: snapshot.total_record_count,
  } : null,
}, null, 2)}\n`);
console.log(`Synchronized aggregate bundle: ${destination} (${sha256})`);
