import type { Metadata } from "next";
import { ReportShell } from "../../components/report-shell";
import { MOONSHOT_MODEL_USE_URL, MOONSHOT_PRIVACY_URL } from "../../lib/assistant-privacy";

export const metadata: Metadata = {
  title: "Privacy & AI processing · Indonesia Wildfire Evidence Report",
  description: "Privacy information for the optional evidence-bounded Kimi explanation feature.",
};

export default function PrivacyPage() {
  return (
    <ReportShell
      activePage="privacy"
      pageLabel="Privacy · optional AI explanation"
      pageTitle="What leaves your browser when you ask the report"
      pageDescription="The report and its curated suggestion answers can be used without an external AI processor. This notice applies when you choose to send a free-form question to the optional explanation feature."
    >
      <article className="privacy-report">
        <section>
          <span className="eyebrow">Data sent</span>
          <h2>Only free-form questions use Moonshot</h2>
          <p>The three curated suggestions in each section are answered locally from their pre-checked fact-ID contracts and are not sent to Moonshot. When you submit a free-form question, this application sends Moonshot&apos;s Kimi API your question, up to four recent messages in the current section, and a compact pack of public facts and limitations from that section. It does not send raw hotspot coordinates, private research files, credentials, or the full research archive.</p>
        </section>
        <section>
          <span className="eyebrow">Retention</span>
          <h2>This application does not retain the raw question</h2>
          <p>The server validates the answer and returns an accountability receipt, but the application does not add the raw question to the research dataset or maintain a raw-question database. Hosting and security providers may still process ordinary technical metadata such as IP address, request timing, and status codes.</p>
        </section>
        <section>
          <span className="eyebrow">External processor</span>
          <h2>Moonshot&apos;s terms apply to submitted content</h2>
          <p>Moonshot is a separate processor. Its published policy states that submitted content may be retained and used under its service and model-use terms. Review those terms before using the feature, and do not submit personal data, confidential information, contact details, or allegations about identifiable people or organizations.</p>
          <p><a href={MOONSHOT_PRIVACY_URL} target="_blank" rel="noreferrer">Moonshot privacy policy</a> · <a href={MOONSHOT_MODEL_USE_URL} target="_blank" rel="noreferrer">Moonshot model-use terms</a></p>
        </section>
        <section>
          <span className="eyebrow">Choice and safeguards</span>
          <h2>The chatbot is optional and cannot change the research</h2>
          <p>You must acknowledge the notice before a free-form question can be sent. The API checks the same notice version, applies rate limits and request bounds, and rejects out-of-scope or prompt-injection requests. Curated suggestions bypass the external model and return only their contracted report facts. AI answers are explanatory only; the versioned statistical outputs and cited sources remain the record of evidence.</p>
        </section>
      </article>
    </ReportShell>
  );
}
