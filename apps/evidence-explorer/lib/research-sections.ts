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
  suggestions: string[];
}

export const RESEARCH_SECTIONS: Record<ResearchSectionId, ResearchSectionMeta> = {
  "report-introduction": {
    id: "report-introduction",
    title: "Research purpose, questions, and scope",
    shortTitle: "Report introduction",
    suggestions: [
      "What questions does this report investigate?",
      "How is this report organized?",
      "Which claims are outside the research scope?",
    ],
  },
  "report-summary": {
    id: "report-summary",
    title: "Research summary and claim boundaries",
    shortTitle: "Report summary",
    suggestions: [
      "Explain the report summary in plain language.",
      "What are the main findings of this research?",
      "What cannot be concluded from this report?",
    ],
  },
  "forest-loss-result": {
    id: "forest-loss-result",
    title: "Fire-positive cells and subsequent forest loss",
    shortTitle: "Forest-loss finding",
    suggestions: [
      "Explain the forest-loss finding in plain language.",
      "Why does this result not prove deliberate burning?",
      "What does the confidence interval mean here?",
    ],
  },
  "peat-dryness-result": {
    id: "peat-dryness-result",
    title: "Peat, dryness, and pre-fire environmental conditions",
    shortTitle: "Peat and climate",
    suggestions: [
      "Explain the peat and climate finding in plain language.",
      "What does the inconclusive peat × dryness result mean?",
      "Which environmental variables were adjusted for?",
    ],
  },
  "earth-ai-result": {
    id: "earth-ai-result",
    title: "Prior-year AlphaEarth predictive robustness check",
    shortTitle: "Earth AI check",
    suggestions: [
      "Explain the Earth AI robustness check in plain language.",
      "What does AlphaEarth add to the model?",
      "Why were same-year embeddings not used?",
    ],
  },
  "global-comparison": {
    id: "global-comparison",
    title: "Indonesia province context and global peat comparison",
    shortTitle: "Indonesia and global map",
    suggestions: [
      "Explain how to read the Indonesia and global map.",
      "What exactly do the map colors represent?",
      "Do countries with more peat experience more fire detections?",
    ],
  },
  "local-layer": {
    id: "local-layer",
    title: "Kalimantan reporting layers",
    shortTitle: "Kalimantan detail",
    suggestions: [
      "Explain the Kalimantan detail section in plain language.",
      "How do SiPongi and GWIS differ in this section?",
      "Why is a hotspot count not a fire count?",
    ],
  },
  "methods-sources": {
    id: "methods-sources",
    title: "Methods, provenance, and data safeguards",
    shortTitle: "Methods and sources",
    suggestions: [
      "Explain the methods and safeguards in plain language.",
      "Where do the research data come from?",
      "How are missing data handled?",
    ],
  },
};

export function isResearchSectionId(value: unknown): value is ResearchSectionId {
  return typeof value === "string" && (RESEARCH_SECTION_IDS as readonly string[]).includes(value);
}
