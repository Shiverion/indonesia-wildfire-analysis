import phase2Data from "../../data/phase2-environmental.json";
import phase3Data from "../../data/phase3-status.json";
import alphaEarthData from "../../data/ppe-alphaearth.json";
import { FindingsReport } from "../../components/evidence-explorer";
import { ReportShell } from "../../components/report-shell";
import { ResearchAssistantProvider } from "../../components/research-assistant";
import type { AlphaEarthPredictionSummary, Phase2EnvironmentalSummary, Phase3StatusSummary } from "../../lib/types";
import { createPageMetadata } from "../site-metadata";

export const metadata = createPageMetadata({
  title: "Findings · Indonesia Wildfire Evidence Report",
  description: "Registered statistical findings, uncertainty, robustness checks, and predictive validation for the Indonesia wildfire research.",
  path: "/findings/",
});

export default function FindingsPage() {
  return (
    <ResearchAssistantProvider initialSection="forest-loss-result">
      <ReportShell
        activePage="findings"
        pageLabel="Research findings · estimates with uncertainty"
        pageTitle="What the completed analyses found"
        pageDescription="This page contains the fitted results and their robustness checks. Read estimates as associations or predictive evidence unless a section explicitly states otherwise."
      >
        <FindingsReport
          phase2={phase2Data as unknown as Phase2EnvironmentalSummary}
          phase3={phase3Data as unknown as Phase3StatusSummary}
          alphaEarth={alphaEarthData as unknown as AlphaEarthPredictionSummary}
        />
      </ReportShell>
    </ResearchAssistantProvider>
  );
}
