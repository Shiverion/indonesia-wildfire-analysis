import Link from "next/link";

const researchQuestions = [
  {
    label: "Environmental conditions",
    question: "When fire detections occur, how do rainfall, soil moisture, wind, vegetation condition, peat extent, and ENSO context differ from matched non-detections?",
  },
  {
    label: "What follows fire",
    question: "Are fire-positive forest cells more often followed by mapped forest loss or land-cover transition than comparable fire-negative cells?",
  },
  {
    label: "Indonesia and the world",
    question: "Do spatial patterns observed in Indonesia resemble patterns in other countries, and where do differences in source coverage prevent direct comparison?",
  },
  {
    label: "Claim accountability",
    question: "Which public claims can the completed evidence address, and which still require actor-, ownership-, policy-, or intent-specific data?",
  },
];

const readingPaths = [
  {
    href: "/findings",
    index: "01",
    title: "Read the findings",
    copy: "Start with the fitted statistical evidence, uncertainty intervals, robustness checks, and the difference between association and causation.",
  },
  {
    href: "/explore",
    index: "02",
    title: "Explore maps and comparisons",
    copy: "Inspect Indonesia province context, the global comparison, and Kalimantan reporting layers without treating aggregate polygons as burned footprints.",
  },
  {
    href: "/methods",
    index: "03",
    title: "Audit methods and sources",
    copy: "Review the data inventory, validation gates, missingness rules, provenance ledger, and the claims the design cannot establish.",
  },
];

export function ReportIntroduction() {
  return (
    <>
      <section id="report-introduction" className="intro-statement" aria-labelledby="intro-statement-heading">
        <p className="intro-kicker">A public-interest investigation into evidence—not a dashboard of conclusions</p>
        <h3 id="intro-statement-heading">Wildfire narratives often mix climate, vulnerable peat, land-use change, and human intent. This report keeps those questions separate.</h3>
        <p>
          The purpose is to test what the available evidence can support while keeping uncertainty, missing data, and alternative explanations visible. Begin with the question that matters to you, then move to the evidence page designed for it.
        </p>
      </section>

      <section className="intro-question-section" aria-labelledby="research-questions-heading">
        <div className="intro-section-heading">
          <span className="eyebrow">Research agenda</span>
          <h3 id="research-questions-heading">The questions this report is built to examine</h3>
        </div>
        <div className="intro-question-grid">
          {researchQuestions.map((item, index) => (
            <article key={item.label} className="intro-question-card">
              <span>{String(index + 1).padStart(2, "0")} · {item.label}</span>
              <p>{item.question}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="intro-reading-section" aria-labelledby="reading-path-heading">
        <div className="intro-section-heading">
          <span className="eyebrow">Choose a reading path</span>
          <h3 id="reading-path-heading">One report, organized by purpose</h3>
          <p>Each page groups related evidence. Anchors are used only within a page, so browser navigation always matches the direction and destination shown.</p>
        </div>
        <div className="intro-route-grid">
          {readingPaths.map((path) => (
            <Link key={path.href} href={path.href} className="intro-route-card">
              <span>{path.index}</span>
              <strong>{path.title}</strong>
              <p>{path.copy}</p>
              <em>Open page →</em>
            </Link>
          ))}
        </div>
      </section>

      <aside className="intro-boundary" aria-label="Evidence boundary">
        <span className="eyebrow">Before reading the evidence</span>
        <strong>The report can evaluate patterns and associations. It cannot identify guilt, intent, ownership, legality, or profit without separately attributable evidence.</strong>
      </aside>
    </>
  );
}
