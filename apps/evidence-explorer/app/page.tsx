import type { Metadata } from "next";
import { ReportIntroduction } from "../components/report-introduction";
import { ReportShell } from "../components/report-shell";
import { ResearchAssistantProvider } from "../components/research-assistant";

export const metadata: Metadata = {
  title: "Introduction · Indonesia Wildfire Evidence Report",
  description: "Research questions, scope, and reading guide for an evidence-bounded investigation of wildfire, peat conditions, and land-cover change.",
};

export default function Home() {
  return (
    <ResearchAssistantProvider initialSection="report-introduction">
      <ReportShell
        activePage="introduction"
        pageLabel="Introduction · questions before results"
        pageTitle="Why this research exists, and what it is designed to ask"
        pageDescription="This opening page contains the research purpose, scope, and reading paths only. Statistical results, maps, and source audits live on their own pages so each kind of evidence can be read in the right context."
      >
        <ReportIntroduction />
      </ReportShell>
    </ResearchAssistantProvider>
  );
}
