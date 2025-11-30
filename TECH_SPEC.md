# Technical Specification: Project Later (Production MVP)

## 1. System Architecture & Consolidation
-   **Project Name:** Later
-   **Core Goal:** Autonomous ingestion, research, and continuous learning for AI tool knowledge.
-   **Model Stack (Consolidated):** **OpenAI-First** commitment.
    -   **Primary LLM:** **GPT-4o** (Vision, Complex Synthesis, Chat).
    -   **Light LLM:** **GPT-4o-mini** (Routing, Partial Verification, Simple Extraction).
    -   **STT:** **Whisper/Realtime STT** (for Audio-First).
-   **Search & Scrape:** **Tavily API** (Search) + **Firecrawl/Playwright** (Clean Document Fetching) + OCR (GPT‑4o vision or OCR engine) for screenshots.
-   **Backend:** Single **FastAPI** service (API + Webhook incl. Telegram) deployed on a platform like Railway/Render.
-   **Database:** **Supabase (PostgreSQL)** + `pgvector` extension.
-   **Task Queue (Durability):** **ARQ** using **Redis** (Broker/Backend) for all long-running/background jobs. A separate ARQ worker process handles background tasks with Redis env vars configured.

## 2. Database Schema (Supabase)
The schema is extended for **Provenance, Audit, and High-Quality RAG**.

### Table: `tools`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | Primary Key. |
| `name` | `Text` | Tool Name. |
| `canonical_url` | `Text` | **Unique Index.** Normalized URL for deduplication. |
| `one_pager` | `JSONB` | **The Living Research Report.** Includes features, pricing, etc. |
| `embedding` | `vector(3072)` | Summary vector for RAG (OpenAI `text-embedding-3-large`). |
| `category_tags` | `Text[]` | MVP tags (e.g., #Video, #RAG). |
| `watchlist` | `Boolean` | Flag for daily update checks. |
| `status` | `Enum` | `pending_research`, `partially_verified`, `fully_verified`, `archived`. |

### Table: `documents` (New: RAG Source Data)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | Primary Key. |
| `tool_id` | `UUID` | Foreign Key to `tools.id`. |
| `source_url` | `Text` | URL of the raw data scraped. |
| `chunk_index` | `Int` | Zero-based index within the source. One row per chunk. |
| `chunk_hash` | `Text` | Hash of `chunk_text` for deduplication. |
| `chunk_text` | `Text` | The specific chunk of text for RAG. |
| `chunk_embedding` | `vector(3072)` | Vector for RAG similarity search. |
| `raw_content` | `Text` | Optional; store only when `chunk_index = 0` to avoid repetition. |
| `last_crawled` | `Timestamptz` | Timestamp for scrape freshness. |

### Table: `tool_updates` (New: Audit Log)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | Primary Key. |
| `tool_id` | `UUID` | Foreign Key to `tools.id`. |
| `field_changed` | `Text` | The `JSONB` path changed (e.g., `pricing.free_tier`). |
| `new_value` | `Text` | The fact that was added/changed. |
| `citation_source` | `Text` | **Mandatory:** The URL/Chat Transcript ID that led to the change. |
| `source_agent` | `Enum` | `user_chat`, `harvester`, `initial_research`. |
| `timestamp` | `Timestamptz` | When the change was applied. |

### Table: `conversations` (New: Harvester Input)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | Primary Key. |
| `user_id` | `UUID` | User identifier (single-user MVP acceptable). |
| `tool_context_id` | `UUID` | Nullable FK to `tools.id` for tool-specific chats. |
| `transcript` | `Text` | Full chat history for the Insight Harvester. |
| `last_activity_at` | `Timestamptz` | Used to trigger the Harvester timeout. |

### Table: `jobs` (New: Durability, Idempotency, Dead-Letter)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | Primary Key. |
| `job_type` | `Text` | `ingest`, `verify_partial`, `verify_full`, `watchlist_refresh`, etc. |
| `tool_id` | `UUID` | Optional FK to `tools.id`. |
| `payload` | `JSONB` | Parameters required to execute the job. |
| `status` | `Text` | `queued`, `running`, `done`, `failed`, `dead_letter`. |
| `run_at` | `Timestamptz` | Optional schedule time. |
| `dedupe_key` | `Text` | For idempotency; ensure only one identical job runs. |
| `attempts` | `Int` | Retry count. |
| `error_message` | `Text` | Last error (if any). |
| `created_at` | `Timestamptz` | Default `now()`. |

### Indexes & Constraints
-   `tools (canonical_url) UNIQUE`
-   `documents (tool_id, source_url, chunk_index) UNIQUE`
-   Create an **IVFFLAT** index on `documents.chunk_embedding` (cosine) once the table has sufficient rows (e.g., lists=100).
-   Provide a Postgres RPC for similarity search (top-k) on `documents.chunk_embedding` to keep app code simple.

## 3. LangGraph Workflows and Orchestration

### 3.1 Model Selection for Specialized Tasks
| Node Name | Core Task | Recommended Model | Rationale |
| :--- | :--- | :--- | :--- |
| **RouterNode** | Intent Classification, Traffic Control | **GPT-4o-mini** | Optimal for speed and low cost for the initial routing decision. |
| **IngestNode** | OCR, Vision Analysis, Document Chunking | **GPT-4o** | Best-in-class vision for screenshot parsing and complex text analysis. |
| **ResearchNode** | Synthesis, Fact Aggregation | **GPT-4o** | Superior reasoning for generating the structured `one_pager` JSON. |
| **ChatNode** | RAG Conversation, Answer Generation | **GPT-4o** | Balanced model for RAG and natural dialogue. |
| **JurorNode** | Verification, Fact-Checking | **GPT-4o-mini** | Low-cost model to parse search results (Tavily) for rapid verification. |

### 3.2 Primary Workflow: Capture $\rightarrow$ Research $\rightarrow$ Partial Write
**Goal:** Deliver a partially verified report under 2 minutes.

| Node | Description | Edge Type | Logic/Condition | Next Node |
| :--- | :--- | :--- | :--- | :--- |
| **START** | User input received (Web/Telegram). | Fixed Edge | N/A | **RouterNode** |
| **RouterNode** | Dedupe check on `canonical_url` (normalize URL: strip UTM/tracking, follow redirects, lowercase host, remove fragments). Detect article links about a tool; map to tool entity. | Conditional Edge | `return 'IMAGE'` | **IngestNode** |
| | | | `return 'URL/NAME/ARTICLE'` | **IngestNode** |
| | | | `return 'DUPLICATE'` | **ErrorNode** (Log merge attempt) |
| | | | `return 'QUESTION'` | **ChatNode** |
| **IngestNode** | Fetches raw content (Firecrawl/Playwright); for images, OCR first; Chunks, Embeds, saves to `documents`. | Fixed Edge | N/A | **ResearchNode** |
| **ResearchNode** | Synthesizes a rich `one_pager` JSON from multi-source inputs (overview_long, features, how_to_use, use_cases, competitors, integrations, user_feedback, pricing). | Fixed Edge | N/A | **JurorNode** |
| **JurorNode** | **(Partial Verification)** Checks 5 Critical Claims against Tavily search. | Conditional Edge | If `status == 'VERIFIED'` | **DatabaseWriteNode** |
| | | | If `status == 'FLAGGED'` | **ErrorNode** |
| **DatabaseWriteNode**| Writes `tools` record, creates `tool_updates` audit log. | Fixed Edge | N/A | **END** / **ARQTaskQueue** |
| **ARQTaskQueue** | **ASYNC:** Enqueue Full Verification/Watchlist job with `dedupe_key` to the ARQ worker. | Fixed Edge | N/A | **END** |

### 3.3 Secondary Workflow: The Insight Harvester Loop
**Goal:** Run in the background via the persistent Task Queue for durability.

1.  **Task Queue Trigger:** The Harvester is triggered by platform cron (or queue-scheduled job) for daily Watchlist checks, or by the `DatabaseWriteNode` for full background verification.
2.  **EntityScannerNode:** Scans the `conversations` table or the full document set for update opportunities.
3.  **Fan-Out (LangGraph Send API):** Uses `Send()` to spawn parallel sub-graphs for each detected tool update or watchlist item.
4.  **InsightNode:** (Runs in Parallel) Extracts new facts from the source (chat transcript or scrape diff).
5.  **JurorNode (Full Check):** Verifies all claims. If verified, passes to **`UpdateProcessorNode`**.
6.  **UpdateProcessorNode:** Formats the verified fact for `JSONB` merge and creates the **`tool_updates`** audit record.
7.  **DatabaseWriteNode (Merge):** Performs the atomic `JSONB` merge operation on the `tools.one_pager` column.

### 3.4 Multi-Source Research (Phase 1)
- Augment Research with Tavily-sourced docs/blog/pricing/news and social platforms (X/LinkedIn/YouTube/Reddit). Extract and summarize user feedback (short quotes + platform/source_url). Merge verified facts into `one_pager` with citations.

### 3.5 Versioning Strategy (MVP → Post-MVP)
- MVP now creates a new `tool_version` on each full write and enforces a freshness gate:
  - If a latest version exists within the last 6 hours and the request is not `force`, skip heavy processing and reuse the latest version.
  - Force re-ingest bypasses this gate.
- Post‑MVP enhancements:
  - Versioned summaries per tool: `tool_versions(tool_id, version_no, is_latest, base_version_id, one_pager, diff_from_prev, last_checked_at)`.
  - Track user links: `user_tool_versions(user_id, tool_version_id, linked_at, last_viewed_at)`.
  - Snapshot inputs: `tool_version_documents(tool_version_id, document_id)` and `media_items(tool_version_id, platform, url, title, author, handle, is_influencer, metrics, published_at, thumbnail_url)`.
  - Freshness window (default 6h): run quick diff first; if unchanged, re‑link to latest; if changed, create new version and set is_latest.
  - Concurrency: dedupe keys per (tool_id, quick_diff, window) and (tool_id, deep_research).

## 4. RAG and Retrieval Quality
-   **Embedding Model:** `text-embedding-3-large` (3,072 dimensions) for quality; deployment may use 1536-d for index limits.
-   **Chunking Strategy:** Recursive Character Text Splitter with overlapping chunks (e.g., 1024 chars, 100 overlap) must be applied to cleaned source text before storage into `documents`.
-   **Retrieval Algorithm:** **MMR (Maximum Marginal Relevance)** must be used in the Chat endpoint to retrieve relevant and diverse context from the `documents` table, improving citation quality (top-k ≈ 8, λ ≈ 0.7). Blend concise `one_pager` facts with selected snippets.
-   **Similarity RPC:** Provide a Postgres function (RPC) to return top-k similar `documents` using cosine similarity, to be called by the API layer.

## 5. Observability and Guardrails
-   **Tracing:** **Mandatory integration of LangSmith** from Day 1 to trace the entire LangGraph run, logging node inputs/outputs, token usage, and latency.
-   **Retry:** All scraping and external API calls (Tavily) must implement **jittered exponential backoff** to handle rate limits and transient network errors.
-   **Deduplication:** A unique index on `tools.canonical_url` will enforce integrity. The **RouterNode** must handle the merge/reject decision gracefully and leverage fuzzy name+domain similarity to propose merges.
-   **Scrape Hygiene:** Respect `robots.txt`, cache responses via `ETag`/`Last-Modified`, and fall back to **Playwright** for JS-heavy or blocked pages.
-   **Jobs & Idempotency:** Use `jobs.dedupe_key` to avoid duplicate work; log a `job_id` across all node spans; move unrecoverable failures to `dead_letter`.
-   **Security:** Verify Telegram webhook signatures, configure CORS for FastAPI, and add basic rate limiting on ingest endpoints and Telegram.
-   **Audio:** The FastAPI Webhook must include an **FFmpeg** step to transcode Telegram's OGG/Opus voice notes into a format readable by the Whisper API. Enforce max duration (e.g., 90s) and per-user STT rate limits.

## 6. UI Integration Notes
-   Rich `one_pager` fields (overview_long, key_features_detailed, how_to_use, use_cases, competitors, integrations, user_feedback, pricing, tech_stack, sources) available for rendering in the Detail View.
-   **Updates Badge:** Provide `COUNT(tool_updates WHERE tool_id = ? AND timestamp > last_seen)` for a "New updates" badge.
-   **Sources Panel:** Surface `documents.source_url` and `last_crawled` with snippet previews for transparency.