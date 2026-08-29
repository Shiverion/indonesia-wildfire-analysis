# Chatbot security controls

The research assistant is a public, evidence-bounded explanation endpoint. It is not an authenticated general chatbot and it has no tools, browsing, raw-data retrieval, file access, or database access.

## Controls enforced by the application

- The Moonshot API key is read only on the server and may be sent only to the approved HTTPS `api.moonshot.ai` host in production. Redirects are rejected.
- Browser requests must be same-origin, use JSON, and stay below 8 KiB. Questions are normalized, stripped of control and bidirectional-override characters, and capped at 600 characters.
- Known prompt-injection, credential-extraction, hidden-prompt, tool-call, private-coordinate, and out-of-research requests are rejected before the model is called.
- The model receives one compact coordinate-free evidence pack. The system prompt treats the question and conversation history as untrusted data.
- The upstream response has time, byte, event, token, and text limits. Hidden reasoning is discarded.
- Output must match a strict JSON schema. The server rejects unknown citations, unsupported numeric claims, links/markup, control characters, and unsupported claims attributing intent, responsibility, profit, illegality, government conduct, or palm-oil actors.
- Answers are rendered as React text, not HTML. Rejected output becomes a bounded “insufficient evidence” response.
- The endpoint emits `no-store`, anti-sniffing, clickjacking, referrer, browser-permission, and opener-isolation headers. Raw questions and hidden reasoning are not logged.
- A privacy-preserving per-instance fallback allows 10 requests per IP-derived hash per 10 minutes, exposes standard rate-limit headers, and caps concurrent model calls at two.

## Required Vercel edge rule

The in-code limiter is a fallback only: separate serverless instances do not share memory. Before a public launch, configure one Vercel Firewall rate-limit rule for this endpoint:

1. Match path `/api/research-chat` and method `POST`.
2. Use a fixed 10-minute window with a limit of 10 requests.
3. Group by IP and, when the dashboard offers it, JA4 fingerprint.
4. Return HTTP 429 when the limit is exceeded.

This edge rule is deliberately not claimed as active until it is visible in the Vercel project dashboard. Review Vercel's current included usage and any pricing notice before enabling it.

## Operational response

If abuse occurs, pause the assistant by removing `KIMI_API_KEY` from the Vercel Production environment or disable the route at the edge, inspect aggregate Vercel request metrics, then tighten the WAF rule. Do not log raw questions or add raw fire coordinates for debugging.
