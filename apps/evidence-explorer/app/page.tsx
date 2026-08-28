import sourceData from "../data/evidence-explorer.json";
import phase2Data from "../data/phase2-environmental.json";
import phase3Data from "../data/phase3-status.json";
import { EvidenceExplorer } from "../components/evidence-explorer";
import type { ExplorerData, Phase2EnvironmentalSummary, Phase3StatusSummary } from "../lib/types";

export default function Home() {
  // The build-time sync script validates the bundle before this generated JSON is imported.
  // JSON imports cannot preserve tuple precision, so retain the checked app-facing type here.
  return (
    <EvidenceExplorer
      data={sourceData as unknown as ExplorerData}
      phase2={phase2Data as unknown as Phase2EnvironmentalSummary}
      phase3={phase3Data as unknown as Phase3StatusSummary}
    />
  );
}
