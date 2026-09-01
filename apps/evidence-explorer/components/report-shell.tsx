import Link from "next/link";
import type { ReactNode } from "react";

export type ReportPage = "introduction" | "findings" | "explore" | "methods";

const pages: Array<{ id: ReportPage; href: string; label: string; description: string }> = [
  { id: "introduction", href: "/", label: "Introduction", description: "Questions and scope" },
  { id: "findings", href: "/findings", label: "Findings", description: "Statistical evidence" },
  { id: "explore", href: "/explore", label: "Maps & comparisons", description: "Geographic context" },
  { id: "methods", href: "/methods", label: "Methods & sources", description: "Audit trail" },
];

export function ReportShell({
  activePage,
  pageLabel,
  pageTitle,
  pageDescription,
  children,
}: {
  activePage: ReportPage | "privacy";
  pageLabel: string;
  pageTitle: string;
  pageDescription: string;
  children: ReactNode;
}) {
  return (
    <main className="app-shell">
      <header className="app-header report-header">
        <Link className="brand-identity brand-link" href="/" aria-label="Indonesia Wildfire Evidence Report home">
          <img className="site-logo" src="/brands/wildfire-evidence-logo.svg" alt="" />
          <div className="brand-block">
            <span className="eyebrow">Interactive research report · Indonesia and global context</span>
            <h1>Indonesia Wildfire Evidence Report</h1>
          </div>
        </Link>
        <div className="header-status" aria-label="Report standard">
          <span className="status-dot" />
          <span>Evidence-bounded research</span>
          <strong>Methods, uncertainty, and claim limits remain visible</strong>
        </div>
      </header>

      <nav className="report-route-nav" aria-label="Primary report pages">
        {pages.map((page) => (
          <Link
            key={page.id}
            href={page.href}
            className={activePage === page.id ? "report-route-link is-active" : "report-route-link"}
            aria-current={activePage === page.id ? "page" : undefined}
          >
            <strong>{page.label}</strong>
            <span>{page.description}</span>
          </Link>
        ))}
      </nav>

      <section className="route-page-intro" aria-labelledby={`${activePage}-page-title`}>
        <span className="eyebrow">{pageLabel}</span>
        <h2 id={`${activePage}-page-title`}>{pageTitle}</h2>
        <p>{pageDescription}</p>
      </section>

      {children}

      <footer className="app-footer report-footer">
        <span>Indonesia Wildfire Evidence Report</span>
        <span>Associations and descriptive maps are not proof of cause, intent, ownership, or liability.</span>
        <a href="https://github.com/Shiverion/indonesia-wildfire-analysis" target="_blank" rel="noreferrer">Public source repository</a>
        <a href="https://shiverion.com/projects/indonesia-wildfire-analysis" target="_blank" rel="noreferrer">Portfolio case study</a>
        <a href="/llms.txt">LLMs.txt</a>
        <Link href="/privacy">Privacy &amp; AI processing</Link>
      </footer>
    </main>
  );
}
