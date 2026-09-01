import sourceData from "../../data/evidence-explorer.json";
import { EvidenceExplorer } from "../../components/evidence-explorer";
import { ReportShell } from "../../components/report-shell";
import { ResearchAssistantProvider } from "../../components/research-assistant";
import type { ExplorerData } from "../../lib/types";
import { createPageMetadata } from "../site-metadata";

export const metadata = createPageMetadata({
  title: "Maps & comparisons · Indonesia Wildfire Evidence Report",
  description: "Interactive Indonesia province, global, and Kalimantan wildfire evidence maps with explicit aggregate-data safeguards.",
  path: "/explore/",
});

export default function ExplorePage() {
  return (
    <ResearchAssistantProvider initialSection="global-comparison">
      <ReportShell
        activePage="explore"
        pageLabel="Interactive evidence · geography with guardrails"
        pageTitle="Maps and comparisons"
        pageDescription="Explore Indonesia first, compare country-level context, then inspect Kalimantan reporting layers. Coloured polygons represent aggregates attached to reporting boundaries—not complete burned areas or fire-risk surfaces."
      >
        <EvidenceExplorer data={sourceData as unknown as ExplorerData} />
      </ReportShell>
    </ResearchAssistantProvider>
  );
}
