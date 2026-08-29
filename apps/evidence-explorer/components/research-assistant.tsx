"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { RESEARCH_SECTIONS, type ResearchSectionId } from "../lib/research-sections";

interface Citation {
  id: string;
  label: string;
  sectionId: ResearchSectionId;
  href: string;
  sourceUrl: string | null;
}

interface AuditReceipt {
  request_id: string;
  created_at_utc: string;
  model: string;
  prompt_version: string;
  corpus_version: string;
  section_ids: ResearchSectionId[];
  citation_ids: string[];
  validator: string;
  token_usage: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number } | null;
  latency_ms: number;
  raw_question_stored_by_app: false;
  reasoning_exposed: false;
}

interface AssistantResponse {
  status: "answered" | "insufficient_evidence" | "out_of_scope";
  answer: string;
  citations: Citation[];
  limitations: string[];
  audit: AuditReceipt;
}

type ConversationItem =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "assistant"; content: string; response: AssistantResponse };

interface ResearchAssistantContextValue {
  openForSection: (sectionId: ResearchSectionId) => void;
  currentSection: ResearchSectionId;
  isOpen: boolean;
}

const ResearchAssistantContext = createContext<ResearchAssistantContextValue | null>(null);

function AskIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M10 2.25c.45 3.42 1.82 4.79 5.25 5.25-3.43.46-4.8 1.83-5.25 5.25-.46-3.42-1.83-4.79-5.25-5.25C8.17 7.04 9.54 5.67 10 2.25Z" />
      <path d="M15.3 12.2c.2 1.52.81 2.13 2.33 2.33-1.52.21-2.13.82-2.33 2.34-.2-1.52-.81-2.13-2.33-2.34 1.52-.2 2.13-.81 2.33-2.33Z" />
    </svg>
  );
}

function CloseIcon() {
  return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15" /></svg>;
}

function ClearIcon() {
  return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 6h12M8 3h4l1 3H7l1-3Zm-2 3 1 11h6l1-11M9 9v5M11 9v5" /></svg>;
}

export function ResearchAssistantProvider({ children, initialSection = "report-summary" }: { children: ReactNode; initialSection?: ResearchSectionId }) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentSection, setCurrentSection] = useState<ResearchSectionId>(initialSection);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ConversationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const openForSection = useCallback((sectionId: ResearchSectionId) => {
    if (currentSection !== sectionId) {
      setMessages([]);
      setQuestion("");
      setError(null);
    }
    setCurrentSection(sectionId);
    setIsOpen(true);
  }, [currentSection]);

  useEffect(() => {
    if (!isOpen) return;
    const timer = window.setTimeout(() => inputRef.current?.focus(), 120);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [isOpen]);

  const ask = async (value: string) => {
    const normalized = value.trim();
    if (!normalized || loading) return;
    const userMessage: ConversationItem = { id: crypto.randomUUID(), role: "user", content: normalized };
    const priorMessages = messages.slice(-4).map((message) => ({ role: message.role, content: message.content }));
    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setError(null);
    setLoading(true);
    try {
      const response = await fetch("/api/research-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: normalized, sectionId: currentSection, history: priorMessages }),
      });
      const payload = await response.json().catch(() => null) as AssistantResponse | { error?: string } | null;
      if (!response.ok || !payload || !("answer" in payload)) {
        throw new Error(payload && "error" in payload && payload.error ? payload.error : "The answer could not be loaded.");
      }
      const assistantMessage: ConversationItem = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: payload.answer,
        response: payload,
      };
      setMessages((current) => [...current, assistantMessage]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The answer could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void ask(question);
  };

  const clearConversation = () => {
    setMessages([]);
    setQuestion("");
    setError(null);
    inputRef.current?.focus();
  };

  const focusCitation = (citation: Citation) => {
    document.getElementById(citation.sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const section = RESEARCH_SECTIONS[currentSection];

  return (
    <ResearchAssistantContext.Provider value={{ openForSection, currentSection, isOpen }}>
      {children}
      <button
        type="button"
        className={`research-assistant-tab ${isOpen ? "is-hidden" : ""}`}
        onClick={() => setIsOpen(true)}
        aria-expanded={isOpen}
        aria-controls="research-assistant-panel"
        aria-label="Open the evidence-bounded research assistant"
        data-tooltip="Ask the report"
      >
        <img src="/brands/wildfire-evidence-logo.svg" alt="" />
      </button>
      <aside id="research-assistant-panel" className={`research-assistant-panel ${isOpen ? "is-open" : ""}`} aria-label="Accountable research assistant" aria-hidden={!isOpen} inert={!isOpen}>
        <header className="research-assistant-header">
          <div className="research-assistant-brand">
            <img src="/brands/wildfire-evidence-logo.svg" alt="" />
            <div><span>Evidence-bounded assistant</span><strong>Ask the report</strong></div>
          </div>
          <div className="assistant-header-actions">
            <button type="button" onClick={clearConversation} aria-label="Clear conversation" title="Clear conversation"><ClearIcon /></button>
            <button type="button" onClick={() => setIsOpen(false)} aria-label="Minimize research assistant" title="Minimize"><CloseIcon /></button>
          </div>
        </header>

        <div className="assistant-accountability-bar">
          <span className="assistant-status-dot" />
          <span>Only this report</span>
          <span>No web access</span>
          <span>Citations checked</span>
        </div>

        <div className="assistant-context-card">
          <span>Current evidence pack</span>
          <strong>{section.shortTitle}</strong>
          <small>Changing section clears the conversation so evidence cannot bleed across topics.</small>
        </div>

        <div className="assistant-conversation" aria-live="polite" aria-busy={loading}>
          {!messages.length && !loading && (
            <div className="assistant-empty-state">
              <AskIcon />
              <h2>Ask for an explanation, not a new conclusion.</h2>
              <p>Kimi can restate and connect validated evidence in this section. It cannot browse, inspect raw coordinates, or fill research gaps. Answers follow the language of your question.</p>
              <div className="assistant-suggestions" aria-label={`Suggested questions for ${section.shortTitle}`}>
                <span className="assistant-suggestions-label">Suggested questions for <strong>{section.shortTitle}</strong></span>
                {section.suggestions.map((suggestion) => (
                  <button type="button" key={suggestion} onClick={() => void ask(suggestion)}>{suggestion}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((message) => message.role === "user" ? (
            <article className="assistant-message is-user" key={message.id}>
              <span>You</span>
              <p>{message.content}</p>
            </article>
          ) : (
            <article className="assistant-message is-assistant" key={message.id}>
              <span>Research explanation</span>
              <p>{message.content}</p>
              {message.response.citations.length > 0 && (
                <div className="assistant-citations" aria-label="Validated citations">
                  {message.response.citations.map((citation) => (
                    <button type="button" key={citation.id} onClick={() => focusCitation(citation)} title={`Open ${citation.label}`}>
                      <span>{citation.id}</span>
                      <small>{citation.label}</small>
                    </button>
                  ))}
                </div>
              )}
              {message.response.limitations.length > 0 && (
                <details className="assistant-limitations">
                  <summary>Evidence boundaries</summary>
                  <ul>{message.response.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
                </details>
              )}
              <details className="assistant-audit">
                <summary>Accountability receipt</summary>
                <dl>
                  <div><dt>Validator</dt><dd>{message.response.audit.validator.replaceAll("_", " ")}</dd></div>
                  <div><dt>Model</dt><dd>{message.response.audit.model}</dd></div>
                  <div><dt>Evidence</dt><dd>{message.response.audit.citation_ids.length || "bounded refusal"}</dd></div>
                  <div><dt>Latency</dt><dd>{(message.response.audit.latency_ms / 1000).toFixed(1)} s</dd></div>
                  <div><dt>Request</dt><dd>{message.response.audit.request_id.slice(0, 8)}</dd></div>
                  <div><dt>Stored by this app</dt><dd>No</dd></div>
                </dl>
              </details>
            </article>
          ))}
          {loading && (
            <div className="assistant-loading" aria-label="Validating research answer">
              <span /><span /><span />
              <p>Kimi is reasoning; the server will check citations and numbers before showing the answer.</p>
            </div>
          )}
          {error && <div className="assistant-error" role="alert"><strong>Could not validate an answer.</strong><span>{error}</span></div>}
        </div>

        <form className="assistant-composer" onSubmit={submit}>
          <label htmlFor="research-assistant-question">Question about {section.shortTitle}</label>
          <textarea
            id="research-assistant-question"
            ref={inputRef}
            value={question}
            onChange={(event) => setQuestion(event.target.value.slice(0, 600))}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                if (question.trim()) void ask(question);
              }
            }}
            rows={3}
            maxLength={600}
            placeholder="Ask what the evidence means…"
            disabled={loading}
          />
          <div className="assistant-composer-footer">
            <span>{question.length}/600</span>
            <button type="submit" disabled={loading || !question.trim()}>Ask with evidence</button>
          </div>
        </form>
        <p className="assistant-disclosure">Your question and the selected evidence pack are processed by Moonshot&apos;s Kimi API. This app does not add the question to the research dataset. Statistical outputs remain the source of record.</p>
      </aside>
    </ResearchAssistantContext.Provider>
  );
}

export function AskResearchButton({ sectionId, label = "Ask AI" }: { sectionId: ResearchSectionId; label?: string }) {
  const context = useContext(ResearchAssistantContext);
  if (!context) throw new Error("AskResearchButton must be used inside ResearchAssistantProvider");
  const section = RESEARCH_SECTIONS[sectionId];
  return (
    <button
      type="button"
      className="ask-research-button"
      onClick={() => context.openForSection(sectionId)}
      aria-label={`Ask AI to explain ${section.shortTitle}`}
      data-tooltip="Ask or explain with evidence-bounded AI"
    >
      <AskIcon />
      <span>{label}</span>
    </button>
  );
}
