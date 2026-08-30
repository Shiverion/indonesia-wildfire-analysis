export const RESEARCH_SECTION_IDS = [
  "report-introduction",
  "report-summary",
  "forest-loss-result",
  "peat-dryness-result",
  "earth-ai-result",
  "global-comparison",
  "local-layer",
  "methods-sources",
] as const;

export type ResearchSectionId = (typeof RESEARCH_SECTION_IDS)[number];

export interface ResearchSectionMeta {
  id: ResearchSectionId;
  title: string;
  shortTitle: string;
  suggestions: Array<{
    question: string;
    expectedFactIds: string[];
  }>;
}

export const RESEARCH_SECTIONS: Record<ResearchSectionId, ResearchSectionMeta> = {
  "report-introduction": {
    id: "report-introduction",
    title: "Research purpose, questions, and scope",
    shortTitle: "Report introduction",
    suggestions: [
      { question: "What questions does this report investigate?", expectedFactIds: ["introduction.questions"] },
      { question: "How is this report organized?", expectedFactIds: ["introduction.structure"] },
      { question: "Which claims are outside the research scope?", expectedFactIds: ["introduction.boundary"] },
    ],
  },
  "report-summary": {
    id: "report-summary",
    title: "Research summary and claim boundaries",
    shortTitle: "Report summary",
    suggestions: [
      { question: "Explain the report summary in plain language.", expectedFactIds: ["summary.forest-loss", "summary.peat-dryness", "summary.scope"] },
      { question: "What are the main findings of this research?", expectedFactIds: ["summary.forest-loss", "summary.peat-dryness", "summary.scope"] },
      { question: "What cannot be concluded from this report?", expectedFactIds: ["summary.boundary"] },
    ],
  },
  "forest-loss-result": {
    id: "forest-loss-result",
    title: "Fire-positive cells and subsequent forest loss",
    shortTitle: "Forest-loss finding",
    suggestions: [
      { question: "Explain the forest-loss finding in plain language.", expectedFactIds: ["forest.primary", "forest.unadjusted", "forest.negative-control"] },
      { question: "Why does this result not prove deliberate burning?", expectedFactIds: ["forest.negative-control", "forest.boundary"] },
      { question: "What does the confidence interval mean for this estimate?", expectedFactIds: ["forest.primary", "forest.uncertainty"] },
    ],
  },
  "peat-dryness-result": {
    id: "peat-dryness-result",
    title: "Peat, dryness, and pre-fire environmental conditions",
    shortTitle: "Peat and climate",
    suggestions: [
      { question: "Explain the peat and climate finding in plain language.", expectedFactIds: ["environment.primary", "environment.interpretation"] },
      { question: "What does the inconclusive peat × dryness result mean?", expectedFactIds: ["environment.primary", "environment.interpretation"] },
      { question: "Which environmental variables were adjusted for?", expectedFactIds: ["environment.adjustment"] },
    ],
  },
  "earth-ai-result": {
    id: "earth-ai-result",
    title: "Prior-year AlphaEarth predictive robustness check",
    shortTitle: "Earth AI check",
    suggestions: [
      { question: "Explain the Earth AI robustness check in plain language.", expectedFactIds: ["alphaearth.primary", "alphaearth.design", "alphaearth.boundary"] },
      { question: "What does AlphaEarth add to the model?", expectedFactIds: ["alphaearth.primary", "alphaearth.boundary"] },
      { question: "Why were same-year embeddings not used?", expectedFactIds: ["alphaearth.design"] },
    ],
  },
  "global-comparison": {
    id: "global-comparison",
    title: "Indonesia province context and global peat comparison",
    shortTitle: "Indonesia and global map",
    suggestions: [
      { question: "Explain how to read the Indonesia and global map.", expectedFactIds: ["global.map-meaning", "global.map-colors", "global.province-availability"] },
      { question: "What exactly do the map colors represent?", expectedFactIds: ["global.map-colors", "global.map-meaning"] },
      { question: "Does this comparison show that countries with more peat have more fire detections?", expectedFactIds: ["global.peat-test", "global.map-meaning"] },
    ],
  },
  "local-layer": {
    id: "local-layer",
    title: "Kalimantan reporting layers",
    shortTitle: "Kalimantan detail",
    suggestions: [
      { question: "Explain the Kalimantan detail section in plain language.", expectedFactIds: ["local.sipongi", "local.gwis", "local.missingness", "local.archive-gap"] },
      { question: "How do SiPongi and GWIS differ in this section?", expectedFactIds: ["local.sipongi", "local.gwis", "local.archive-gap"] },
      { question: "Why is a hotspot record not the same as a unique fire?", expectedFactIds: ["local.sipongi"] },
    ],
  },
  "methods-sources": {
    id: "methods-sources",
    title: "Methods, provenance, and data safeguards",
    shortTitle: "Methods and sources",
    suggestions: [
      { question: "Explain the methods and safeguards in plain language.", expectedFactIds: ["methods.sources", "methods.provenance", "methods.missingness", "methods.assistant"] },
      { question: "Where do the research data come from?", expectedFactIds: ["methods.sources"] },
      { question: "How are missing data handled?", expectedFactIds: ["methods.missingness"] },
    ],
  },
};

export function isResearchSectionId(value: unknown): value is ResearchSectionId {
  return typeof value === "string" && (RESEARCH_SECTION_IDS as readonly string[]).includes(value);
}

export function getSuggestionContract(sectionId: ResearchSectionId, question: string) {
  return RESEARCH_SECTIONS[sectionId].suggestions.find(
    (suggestion) => suggestion.question.toLowerCase() === question.trim().toLowerCase(),
  ) ?? null;
}
