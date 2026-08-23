import sourceData from "../data/evidence-explorer.json";
import { EvidenceExplorer } from "../components/evidence-explorer";
import type { ExplorerData } from "../lib/types";

export default function Home() {
  // The build-time sync script validates the bundle before this generated JSON is imported.
  // JSON imports cannot preserve tuple precision, so retain the checked app-facing type here.
  return <EvidenceExplorer data={sourceData as unknown as ExplorerData} />;
}
