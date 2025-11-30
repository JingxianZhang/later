# Project Name: Later
**"Don't just save it for later. Know it for later."**

## Executive Summary
**Project Later** is an autonomous, opinionated research agent designed to continuously scout, ingest, and maintain up-to-date, structured information on AI tools and developer products. It transforms unstructured input (screenshots, links) into a "Living One-Pager" of verified facts.

| Detail | Specification |
| :--- | :--- |
| **MVP Goal** | Autonomous ingestion, partial verification (<2 min), and RAG chat. |
| **Target User** | Developers, Founders, and VCs tracking competitive or emerging tech. |
| **Core Technology** | **LangGraph** (Orchestration) + **GPT-4o/4o-mini** (Reasoning/Vision) + **Supabase** (Postgres/pgvector). |
| **Unique Feature** | **The Insight Harvester** - An autonomous loop that learns new facts from user conversations, verifies them (The Juror), and updates the database without human intervention. |

## Key Features & Value Proposition
1.  **Audio-First Capture:** Users can send a voice note or drop a screenshot/link via Telegram or web. Screenshots are OCR‑processed; voice notes are transcribed.
2.  **Structured Fact Sheet:** Input is converted into a comprehensive, searchable JSON (`one_pager`) report with rich fields (overview_long, detailed features, how_to_use, use_cases, competitors, integrations, user_feedback).
3.  **Audit & Provenance:** Every fact includes a **citation source** and an **update history** (audit log).
4.  **Instant Q&A (RAG):** Ask complex questions like "How does Tool X's pricing compare to Tool Y?" and get cited answers.
5.  **Durability:** Uses a **Persistent Task Queue (ARQ/Redis)** for reliable background work like scraping and full verification.

## Monetization Strategy (Future)
* **Tier 1 (Free):** Personal tool storage, limited RAG chat queries.
* **Tier 2 (Pro):** Unlimited storage, **Watchlist** feature (daily auto-refresh), full conversation audit log, Telegram integration.
* **Tier 3 (Enterprise):** Team accounts, normalized tagging/taxonomy, private instance deployment.

## MVP Metrics
| Metric | Target |
| :--- | :--- |
| Research Completion Time (Partial Verify) | **< 2 minutes** |
| Knowledge Retrieval Accuracy (RAG) | **> 90%** (via internal RAG tests) |
| Harvester Update Frequency | **Daily** for Watchlist items. |

## One-Pager Fields (Phase 1)
- Core (Phase 1):
  - overview_long (2–3 paragraphs)
  - key_features_detailed (5–10 bullets)
  - how_to_use (5–8 steps)
  - use_cases (4–6)
  - pricing (normalized tiers)
  - competitors (with differentiators)
  - integrations
  - user_feedback (quotes + platform + source_url)
  - tech_stack
  - sources
  - last_updated
- Post-MVP: creator/team, funding, notable customers, security/compliance, roadmap signals

## Highlights (Videos & Social) - Post-MVP
- Store and display top videos/posts from YouTube/TikTok/X/LinkedIn when they meet quality criteria:
  - Prefilter thresholds (platform-specific; configurable), influencer whitelist
  - Agent scoring to ensure topical relevance and diversity
- Display in the Detail View as “Highlights” with thumbnail, title, author/handle, metric pill, and clickable source URLs.

## Orchestration Flow (Phase 1 LangGraph)

```mermaid
flowchart TD
  A[resolve_tool\nInputs: url? name? article_url? image? force?\nOutputs: tool_id, canonical_url, url_official, status]\n  note right of A: LLM-assisted official site; alias dedupe;\n  article detection → tool binding
  B[ingest\nFetch->OCR if image->Chunk->Embed\nInsert documents]\n  note right of B: robots.txt, ETag/LM, retries, caps
  C[augment_sources\nDocs/Blog/Pricing/News + Social (X/LinkedIn/YouTube/Reddit)\nScore + cap]
  D[research\nSynthesize rich one_pager\n(overview_long, features, how_to_use, etc.)]
  E[juror (light)\nVerify key claims (fast)\nTavily-backed checks]
  F[dbwrite\nUpdate tools + versions\nSnapshot sources/media]
  A --> B --> C --> D --> E --> F
```

Node transitions and conditions:
- resolve_tool:
  - If `url` present: canonicalize; else search candidates; LLM picks the most notable official homepage (rejects social profiles). Sets `canonical_url`/`url_official`. Detect when a link is an article about a tool and map to the tool entity; treat the article as a source.
  - Re-uses existing tool by `canonical_url` or `tool_aliases`; `force` clears old doc rows for the original URL. Freshness gate skips heavy processing when latest version is within window.
- ingest:
  - Uses `url || url_official || canonical_url`; for images, OCR first; fetches, chunks, embeds; inserts document chunks with provenance.
- augment_sources:
  - Queries docs/blog/pricing/news and social/video (X/LinkedIn/YouTube/Reddit); filters support/community; indexes up to N document sources; selects up to M social/video as highlights with metadata.
- research:
  - Aggregates homepage + prioritized snippets (pricing/competitors/updates/how_to/use_cases/integrations); synthesizes rich one_pager with sources.
- juror:
  - Verifies a handful of key claims in parallel to keep total time < 2 min (partial verification).
- dbwrite:
  - Writes one_pager; creates next tool_version; snapshots informing documents; stores media items (title/author/thumbnail where available).

### Freshness Policy
- Phase 1 behavior: if a latest `tool_version` exists within the last 6 hours (configurable) and the request is not `force`, the flow skips heavy processing and returns the current latest version.
- Post‑MVP (planned): add a quick diff mode within the window; only run deep steps and create a new version when meaningful changes are detected.