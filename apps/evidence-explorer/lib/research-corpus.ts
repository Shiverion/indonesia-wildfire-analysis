import "server-only";

import { createHash } from "node:crypto";
import explorerSource from "../data/evidence-explorer.json";
import environmentalSource from "../data/phase2-environmental.json";
import forestLossSource from "../data/phase3-status.json";
import alphaEarthSource from "../data/ppe-alphaearth.json";
import type {
  AlphaEarthPredictionSummary,
  ExplorerData,
  Phase2EnvironmentalSummary,
  Phase3StatusSummary,
} from "./types";
import { RESEARCH_SECTIONS, type ResearchSectionId } from "./research-sections";

const explorer = explorerSource as unknown as ExplorerData;
const environmental = environmentalSource as unknown as Phase2EnvironmentalSummary;
const forestLoss = forestLossSource as unknown as Phase3StatusSummary;
const alphaEarth = alphaEarthSource as unknown as AlphaEarthPredictionSummary;

export interface ResearchFact {
  id: string;
  statement: string;
  sourceLabel: string;
  sourceUrl?: string;
}

export interface ResearchEvidencePack {
  sectionId: ResearchSectionId;
  title: string;
  facts: ResearchFact[];
  limitations: string[];
}

function fixed(value: number, digits = 2) {
  return value.toFixed(digits);
}

function percentagePoint(value: number, digits = 1) {
  return `${(value * 100).toFixed(digits)} percentage points`;
}

function displayPValue(value: number) {
  return value < 0.001 ? "p<0.001" : `p=${value.toFixed(3)}`;
}

const forestModel = forestLoss.primary_result?.status === "estimated" ? forestLoss.primary_result.model : null;
const peatModel = explorer.peat_fire_comparison?.primary_fixed_effect_model ?? null;
const latest = explorer.latest_global_fire ?? null;

const commonClaimBoundaries = [
  "The registered results are associations or predictive checks, not causal identification of an actor, intent, ownership, legality, government performance, plantation expansion motive, or profit.",
  "Absence of evidence in this report is not evidence that a mechanism or allegation is false; it means the required design and data were not completed here.",
  "The public assistant may use only compact, coordinate-free evidence statements. Raw provider records, private cell coordinates, credentials, and unpublished analysis data are excluded.",
];

const packs: Record<ResearchSectionId, ResearchEvidencePack> = {
  "report-introduction": {
    sectionId: "report-introduction",
    title: RESEARCH_SECTIONS["report-introduction"].title,
    facts: [
      {
        id: "introduction.questions",
        statement: "The report investigates four linked questions: how fire detections vary with weather and peat conditions; whether fire-positive forest cells are followed by mapped land-cover change; how Indonesia compares with other countries; and which public allegations cannot yet be evaluated with the completed design.",
        sourceLabel: "Registered research scope",
      },
      {
        id: "introduction.structure",
        statement: "The report is organized into three evidence pages: Findings contains the fitted statistical and predictive results; Maps and comparisons contains descriptive geographic context; Methods and sources documents provenance, missingness rules, validation, and claim boundaries.",
        sourceLabel: "Report reading guide",
      },
      {
        id: "introduction.boundary",
        statement: "The completed research does not identify a person, company, land owner, ignition intent, legal responsibility, government performance, plantation-development motive, or profit. Those questions require separately timed and attributable evidence.",
        sourceLabel: "Registered claim boundary",
      },
    ],
    limitations: commonClaimBoundaries,
  },
  "report-summary": {
    sectionId: "report-summary",
    title: RESEARCH_SECTIONS["report-summary"].title,
    facts: [
      {
        id: "summary.forest-loss",
        statement: forestModel
          ? `In ${forestModel.matched_set_count.toLocaleString("en-US")} complete matched sets, the adjusted association between a fire-positive cell and losing at least 10% of pre-index forest within one year was ${percentagePoint(forestModel.primary_term.estimate)}, with a 95% confidence interval from ${percentagePoint(forestModel.primary_term.ci95[0])} to ${percentagePoint(forestModel.primary_term.ci95[1])}; ${displayPValue(forestModel.primary_term.p_two_sided)}.`
          : "The registered forest-loss result is unavailable because the outcome data did not pass its gate.",
        sourceLabel: "Registered forest-loss analysis",
      },
      {
        id: "summary.peat-dryness",
        statement: `The primary peat-by-dryness interaction odds ratio was ${fixed(environmental.primary.odds_ratio)} with 95% confidence interval ${fixed(environmental.primary.ci95[0])} to ${fixed(environmental.primary.ci95[1])} and p=${environmental.primary.p_two_sided.toFixed(3)}; the registered classification is inconclusive.`,
        sourceLabel: "Registered environmental-condition analysis",
      },
      {
        id: "summary.scope",
        statement: "The fitted inferential analyses are restricted to matched baseline-natural-forest cells in Kalimantan. The Indonesia province map and world map are descriptive context and are not the fitted model domain.",
        sourceLabel: "Analysis scope and map guardrails",
      },
    ],
    limitations: commonClaimBoundaries,
  },
  "forest-loss-result": {
    sectionId: "forest-loss-result",
    title: RESEARCH_SECTIONS["forest-loss-result"].title,
    facts: [
      {
        id: "forest.primary",
        statement: forestModel
          ? `The adjusted risk-difference estimate was ${percentagePoint(forestModel.primary_term.estimate)} with a 95% confidence interval from ${percentagePoint(forestModel.primary_term.ci95[0])} to ${percentagePoint(forestModel.primary_term.ci95[1])}; ${displayPValue(forestModel.primary_term.p_two_sided)}.`
          : "No registered forest-loss estimate is available.",
        sourceLabel: "Primary registered forest-loss model",
      },
      {
        id: "forest.unadjusted",
        statement: forestModel
          ? `The unadjusted one-year probability of losing at least 10% of pre-index forest was ${(forestModel.unadjusted.fire_positive_risk * 100).toFixed(1)}% for fire-positive cells and ${(forestModel.unadjusted.fire_negative_risk * 100).toFixed(1)}% for matched fire-negative cells.`
          : "No unadjusted forest-loss contrast is available.",
        sourceLabel: "Matched-set outcome summary",
      },
      {
        id: "forest.support",
        statement: forestModel
          ? `The primary model included ${forestModel.matched_set_count.toLocaleString("en-US")} matched sets and ${forestModel.unique_cell_count.toLocaleString("en-US")} unique 1-km cells.`
          : `The locked frame contains ${forestLoss.matched_set_count.toLocaleString("en-US")} matched sets, but no model result.`,
        sourceLabel: "Locked analysis support",
      },
      {
        id: "forest.negative-control",
        statement: forestLoss.publication_robustness
          ? `The pre-exposure negative-control difference was ${percentagePoint(forestLoss.publication_robustness.negative_control.estimate, 2)}, with 95% confidence interval ${percentagePoint(forestLoss.publication_robustness.negative_control.ci95[0], 2)} to ${percentagePoint(forestLoss.publication_robustness.negative_control.ci95[1], 2)}. This indicates pre-existing land-change trajectory or residual confounding and blocks a causal interpretation.`
          : "The pre-exposure negative-control diagnostic is unavailable.",
        sourceLabel: "Publication robustness diagnostics",
      },
    ],
    limitations: [
      ...commonClaimBoundaries,
      "The result cannot distinguish deliberate ignition from accidental or natural ignition and cannot identify whether a later land-cover destination was planned before the fire.",
    ],
  },
  "peat-dryness-result": {
    sectionId: "peat-dryness-result",
    title: RESEARCH_SECTIONS["peat-dryness-result"].title,
    facts: [
      {
        id: "environment.primary",
        statement: `For cells with at least 50% mapped peat extent, the peat-by-one-standard-deviation-drier-soil interaction odds ratio was ${fixed(environmental.primary.odds_ratio)} with 95% confidence interval ${fixed(environmental.primary.ci95[0])} to ${fixed(environmental.primary.ci95[1])} and p=${environmental.primary.p_two_sided.toFixed(3)}. Because the interval crosses 1, the result is inconclusive.`,
        sourceLabel: "Primary peat × dryness model",
      },
      {
        id: "environment.design",
        statement: `The environmental frame covers ${environmental.scope}, with ${environmental.data_summary.row_count.toLocaleString("en-US")} rows in ${environmental.data_summary.matched_set_count.toLocaleString("en-US")} exact daily 1:4 matched sets.`,
        sourceLabel: "Locked environmental frame",
      },
      {
        id: "environment.adjustment",
        statement: "The fitted comparison adjusts for pre-detection rainfall, vapour-pressure deficit, wind, vegetation, forest fraction, and soil moisture. Observation opportunity is controlled through the matched risk-set design.",
        sourceLabel: "Registered environmental specification",
      },
      {
        id: "environment.interpretation",
        statement: "An inconclusive interaction does not prove that dry peat has no effect and does not prove that peatland is safe. It means this design did not estimate a sufficiently precise non-null interaction.",
        sourceLabel: "Interpretation guardrail",
      },
    ],
    limitations: [
      ...commonClaimBoundaries,
      "Drainage history and water-table intervention require a separately timed analysis; they are not identified by the completed primary model.",
    ],
  },
  "earth-ai-result": {
    sectionId: "earth-ai-result",
    title: RESEARCH_SECTIONS["earth-ai-result"].title,
    facts: [
      {
        id: "alphaearth.primary",
        statement: `Adding prior-year AlphaEarth embeddings improved conditional log loss by ${fixed(alphaEarth.combined_improvement.conditional_log_loss, 3)} on the locked test, with a 95% bootstrap interval from ${fixed(alphaEarth.combined_improvement.ci95[0], 3)} to ${fixed(alphaEarth.combined_improvement.ci95[1], 3)}.`,
        sourceLabel: "AlphaEarth locked-test ablation",
        sourceUrl: alphaEarth.source.documentation,
      },
      {
        id: "alphaearth.design",
        statement: `The embeddings cover ${alphaEarth.design.embedding_years}; every cell uses the calendar year before its fire opportunity. Same-year embeddings and post-fire features were rejected by the automated feature gate.`,
        sourceLabel: "AlphaEarth leakage gate",
        sourceUrl: alphaEarth.source.documentation,
      },
      {
        id: "alphaearth.support",
        statement: `The locked 2024–2025 test contains ${alphaEarth.design.locked_test_matched_sets.toLocaleString("en-US")} matched sets. Model selection used 2018–2022 spatial folds and 2023 was a rehearsal year.`,
        sourceLabel: "AlphaEarth out-of-time design",
      },
      {
        id: "alphaearth.boundary",
        statement: "The embedding adds reproducible predictive ranking information beyond named covariates, but an embedding dimension is not an identified physical or human mechanism and does not support a causal claim.",
        sourceLabel: "AlphaEarth interpretation guardrail",
      },
    ],
    limitations: commonClaimBoundaries,
  },
  "global-comparison": {
    sectionId: "global-comparison",
    title: RESEARCH_SECTIONS["global-comparison"].title,
    facts: [
      {
        id: "global.latest",
        statement: latest
          ? `The latest validated closed-day snapshot is ${latest.snapshot_date}. It contains ${latest.matched_point_count.toLocaleString("en-US")} matched NASA FIRMS MODIS and VIIRS positive-detection records across ${latest.country_count} country geometries and ${latest.indonesia_provinces.length} frozen Indonesia province display geometries.`
          : "No latest closed-day NASA FIRMS snapshot is available.",
        sourceLabel: "NASA FIRMS latest closed-day aggregate",
        sourceUrl: latest?.source_url,
      },
      {
        id: "global.province-availability",
        statement: "At province level, this public bundle contains only the latest NRT positive-detection aggregate. Completed-2024 detection rates and peatland share are available only for country-level comparison, so those controls are intentionally hidden in province mode.",
        sourceLabel: "Public bundle coverage contract",
      },
      {
        id: "global.peat-test",
        statement: peatModel
          ? `Across ${explorer.peat_fire_comparison?.matched_country_count ?? 0} matched countries, the primary country fixed-effects peat comparison rate ratio was ${fixed(peatModel.rate_ratio ?? Number.NaN)} with 95% confidence interval ${fixed(peatModel.ci95?.[0] ?? Number.NaN)} to ${fixed(peatModel.ci95?.[1] ?? Number.NaN)} and p=${peatModel.p_two_sided?.toFixed(3) ?? "unknown"}. The result was not statistically significant.`
          : "The completed-2024 country peat comparison is unavailable.",
        sourceLabel: "Completed-2024 global peat comparison",
      },
      {
        id: "global.map-meaning",
        statement: "A coloured polygon represents an aggregate attached to a legal or reporting geometry. It does not mean the entire polygon burned. A FIRMS detection is a satellite thermal detection record, not a unique fire, burned-area polygon, ignition, or risk probability.",
        sourceLabel: "Map interpretation guardrail",
      },
    ],
    limitations: [
      ...commonClaimBoundaries,
      "The global country comparison lacks an observation-opportunity denominator and remains vulnerable to cloud, orbit, sensor, land-management, and spatial confounding.",
    ],
  },
  "local-layer": {
    sectionId: "local-layer",
    title: RESEARCH_SECTIONS["local-layer"].title,
    facts: [
      {
        id: "local.sipongi",
        statement: "SiPongi values are positive portal hotspot records for the current five Kalimantan province reporting units. They are not unique fires, ignitions, occurrence rates, or detection probabilities; platform composition changes across time.",
        sourceLabel: "SiPongi aggregate guardrail",
        sourceUrl: "https://sipongi.gakkum.kehutanan.go.id/sebaran-titik-panas",
      },
      {
        id: "local.gwis",
        statement: "GWIS values are historic four-province aggregate burned-area rows. The legacy Kalimantan Timur unit includes territory now represented as Kalimantan Utara and cannot be directly totalled with the current five-province SiPongi system.",
        sourceLabel: "GWIS legacy geography guardrail",
        sourceUrl: "https://gwis.jrc.ec.europa.eu/",
      },
      {
        id: "local.missingness",
        statement: "Missing, rejected, or incomplete source rows are rendered as unknown and are never replaced with zero. The map polygons are aggregate reporting units, not fire footprints.",
        sourceLabel: "Missingness and geometry safeguards",
      },
    ],
    limitations: commonClaimBoundaries,
  },
  "methods-sources": {
    sectionId: "methods-sources",
    title: RESEARCH_SECTIONS["methods-sources"].title,
    facts: [
      {
        id: "methods.sources",
        statement: "The report combines NASA FIRMS fire detections, SiPongi hotspot aggregates, GWIS burned-area context, NOAA CPC RONI, CHIRPS rainfall, ERA5-Land fire-weather and soil variables, MOD13Q1 vegetation indices, MapBiomas Indonesia annual land cover, a global peatland baseline, geoBoundaries display geometries, and prior-year AlphaEarth embeddings.",
        sourceLabel: "Research source inventory",
      },
      {
        id: "methods.provenance",
        statement: `The browser bundle was generated at ${explorer.generated_at_utc}. It exposes frozen aggregate values with a provenance ledger containing ${explorer.ledger.entry_count} entries; raw SiPongi coordinates and private cell coordinates are not embedded.`,
        sourceLabel: "Public provenance bundle",
      },
      {
        id: "methods.missingness",
        statement: "The pipeline preserves missingness explicitly: unavailable or quarantined values remain unknown, rather than being imputed as zero. Public maps are descriptive layers and do not become causal or predictive surfaces through visualization.",
        sourceLabel: "Research data-quality policy",
      },
      {
        id: "methods.assistant",
        statement: "The research assistant receives only the selected compact evidence pack, must cite fact IDs, cannot browse the web or retrieve private files, and is rejected by a deterministic validator if its citations or numbers are not grounded in the pack.",
        sourceLabel: "Assistant accountability contract",
      },
    ],
    limitations: commonClaimBoundaries,
  },
};

const corpusMaterial = JSON.stringify(packs);
export const RESEARCH_CORPUS_VERSION = `research-corpus/2026-08-29/${createHash("sha256").update(corpusMaterial).digest("hex").slice(0, 12)}`;

export function getResearchEvidencePack(sectionId: ResearchSectionId): ResearchEvidencePack {
  return packs[sectionId];
}
