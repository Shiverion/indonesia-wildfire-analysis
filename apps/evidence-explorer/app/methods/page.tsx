import type { Metadata } from "next";
import sourceData from "../../data/evidence-explorer.json";
import phase2Data from "../../data/phase2-environmental.json";
import { MethodsReport } from "../../components/evidence-explorer";
import { ReportShell } from "../../components/report-shell";
import { ResearchAssistantProvider } from "../../components/research-assistant";
import type { ExplorerData, Phase2EnvironmentalSummary } from "../../lib/types";

export const metadata: Metadata = {
  title: "Methods & sources · Indonesia Wildfire Evidence Report",
  description: "Data inventory, validation gates, provenance, missingness rules, and claim boundaries for the Indonesia wildfire research.",
};

const explorer = sourceData as unknown as ExplorerData;
const environmental = phase2Data as unknown as Phase2EnvironmentalSummary;

export default function MethodsPage() {
  return (
    <ResearchAssistantProvider initialSection="methods-sources">
      <ReportShell
        activePage="methods"
        pageLabel="Audit trail · sources, validation, and limitations"
        pageTitle="How the evidence was assembled and constrained"
        pageDescription="Use this page to audit where the data came from, which preparation gates passed, how missingness was protected, and which conclusions remain outside the completed design."
      >
        <MethodsReport
          data={{
            phase1b_readiness: explorer.phase1b_readiness,
            provenance: explorer.provenance,
            ledger: explorer.ledger,
            generated_at_utc: explorer.generated_at_utc,
            limitations: explorer.limitations,
            display_status: { blocked_assets: explorer.display_status.blocked_assets },
          }}
          phase2={{ primary: environmental.primary }}
        />
      </ReportShell>
    </ResearchAssistantProvider>
  );
}
