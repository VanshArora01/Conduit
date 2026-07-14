# Conduit Memory

## Project Vision
Conduit is a production-grade AI workspace platform that connects to third-party services (Google Drive, GitHub, Notion, Gmail, etc.) and allows users to search and retrieve information across all their connected knowledge sources from a single interface using AI.

## Tech Stack
* **Backend:** Python 3.13+ / FastAPI / uv
* **Database:** PostgreSQL (Neon) via SQLAlchemy 2.x & AsyncPG
* **Migrations:** Alembic
* **Quality:** Ruff, Black, Pytest
* **Deployment:** Docker & Docker Compose
* **Frontend:** (To be decided - React anticipated based on structure)
* **Authentication:** (To be decided)
* **Vector Database:** (To be decided)

## Architecture Decisions

### ADR-001
* **Decision:** Use a Monorepo.
* **Reason:** Allows unified versioning, easier cross-stack changes, and simplified developer setup for a tightly coupled AI SaaS product.
* **Tradeoffs:** Repository size can grow large, CI/CD pipelines need to be carefully configured to avoid redundant builds.
* **Status:** Accepted

### ADR-002
* **Decision:** Use `uv` as the Python package manager and FastAPI application factory pattern.
* **Reason:** `uv` provides fast, reliable, and reproducible dependency management without pip's historical baggage. The factory pattern makes testing and configuration of the production application simpler.
* **Tradeoffs:** Team needs to be familiar with `uv` instead of standard `pip`.
* **Status:** Accepted

### ADR-003
* **Decision:** Implement Async Database Foundation (SQLAlchemy 2.x + AsyncPG).
* **Reason:** Modern FastAPI applications perform best with non-blocking async operations, specifically for heavily I/O bound tasks like database queries in an AI platform.
* **Tradeoffs:** Async SQLAlchemy is more complex to mock and debug compared to synchronous SQLAlchemy.
* **Status:** Accepted

### ADR-006
* **Decision:** Core Domain Schema Design.
* **Reason:** Isolate chunks away from documents to enable 1-to-many chunk embedding relationships for vector retrieval in RAG. Introduce a centralized `Workspace` table acting as a multi-tenant isolation boundary, allowing documents, chats, and integrations to be rigorously segmented by user organization.
* **Tradeoffs:** Increased relational complexity compared to a flatter schema, requiring more granular cascading deletion rules.
* **Status:** Accepted

### ADR-008
* **Decision:** Decouple OAuth flow from Connectors.
* **Reason:** Connectors should only be responsible for interacting with external APIs using valid credentials. The OAuth lifecycle (redirects, token exchange, CSRF protection, and credential storage) is handled centrally by a dedicated `OAuthService`. This prevents connectors from being entangled with web concerns and keeps them focused on data retrieval.
* **Tradeoffs:** Requires the `OAuthService` to be aware of provider-specific token exchange endpoints, though this can be abstracted later if needed.
* **Status:** Accepted

### ADR-009
* **Decision:** Introduce `NormalizedDocument` schema.
* **Reason:** Create a provider-independent data model to represent files discovered from external providers. This decouples the rest of the application (like syncing and UI) from provider-specific formats like Google Drive's raw JSON, ensuring uniform handling of documents across any future integration (e.g., Notion, GitHub).
* **Tradeoffs:** Requires a mapping layer for every new connector to translate provider-specific data into the `NormalizedDocument` schema.
### ADR-010
* **Decision:** Replace PostgreSQL LargeBinary document storage with Local Filesystem storage.
* **Reason:** Storing large binary files (PDFs, DOCX) directly inside the database `raw_content` column severely degrades database performance, bloats backups, and increases memory consumption during queries. We now save raw bytes to `storage/documents/` and only persist the `storage_path`, `file_size`, and `checksum` inside the `Document` model.
* **Tradeoffs:** Requires managing local filesystem persistence and ensuring storage volumes are correctly mapped in Docker, adding slight operational complexity compared to pure database storage.
* **Status:** Accepted

### ADR-015
* **Decision:** Consolidate AI processing components into a unified `app/ai` package with a Document Cleaner stage.
* **Reason:** Restructuring the AI Indexing Pipeline (Classifier, Cleaner, Chunker, Embedder, VectorStore) under an `app/ai` package prevents scattered top-level modules. Introducing the Document Cleaner stage (stripping repeated headers, fixing OCR artifacts, normalizing whitespace) ensures higher-quality chunking and embedding outputs.
* **Tradeoffs:** Adds an extra processing step, increasing indexing time slightly, but drastically improves the precision of vector retrieval.
* **Status:** Accepted

### ADR-016
* **Decision:** Enrich Vector Store payloads with document metadata during indexing.
* **Reason:** Eliminates the need for secondary SQL queries during the RAG retrieval flow to fetch citation data, significantly reducing database load and retrieval latency.
* **Tradeoffs:** Slight increase in vector store storage size per chunk.
* **Status:** Accepted

### ADR-017
* **Decision:** Expose an isolated Retrieval-Only endpoint (`/api/v1/search`) alongside the full Chat endpoint (`/api/v1/chat/query`).
* **Reason:** Decoupling semantic search from LLM generation allows for independent testing. Returning the `retrieved_chunks` directly from the search endpoint ensures retrieval quality can be debugged independently of LLM summarization.
* **Tradeoffs:** Increased API surface area and slightly larger response payloads when debugging.
* **Status:** Accepted

## Folder Structure
* `backend/`: Backend application and API
  * `pyproject.toml` / `uv.lock`: Dependency management (uv)
  * `Dockerfile`: Multi-stage build for the FastAPI application
  * `alembic/`: Database migrations folder
  * `app/core/`: Configuration, logging, exception handlers
  * `app/db/`: Database session management, declarative base, and BaseModel mixin
  * `app/models/`: SQLAlchemy models (`User`, `Workspace`, `Document`, `Chunk`, `Chat`, `Message`, `Integration`, `SyncJob`)
  * `app/schemas/`: Pydantic schemas (`UserCreate`, `Token`, etc.)
  * `app/repositories/`: Database abstraction layer (`UserRepository`)
  * `app/services/`: Business logic layer (`AuthService`)
  * `app/middleware/`: FastAPI middlewares (Request ID, Logging, placeholders)
  * `app/api/`: Versioned API routers and dependencies (`deps.py`)
* `docker-compose.yml`: Root Docker orchestration
* `frontend/`: Frontend application
* `docs/`: Project documentation and architecture records

## Current Progress

### Milestone 1, 2, 3, & 4
* Repository initialized and Project skeleton created
* Complete backend production foundation implemented:
  * Robust `pydantic-settings` implementation for all secrets and configs.
  * Production-grade middleware (RequestID, Logging) and Exception Handling.
  * Application factory and Lifespan setup.
  * Dockerfile and docker-compose.yml established.
* Production Database Infrastructure implemented:
  * Database foundation configured with AsyncPG and SQLAlchemy 2.x.
  * Connection pooling configured (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`).
  * `BaseModel` mixin created for standardized UUIDs and timestamps.
  * Alembic configured with dynamic database URL binding.
* Authentication and User System implemented:
  * `User` model created and migration generated.
  * `pwdlib[argon2]` configured for modern password hashing.
  * JWT access and refresh token lifecycle implemented using `PyJWT`.
  * Fully layered Repository -> Service -> Route architecture established.
  * Automated integration testing suite created with `pytest` and `aiosqlite`.
* Core Domain Models Implemented:
  * `Workspace`, `Integration`, `Document`, `Chunk`, `Chat`, `Message`, and `SyncJob` SQLAlchemy models created.
  * 1-to-many relationships configured with strict cascading deletes.
  * RAG-ready chunk separation and vector DB mapping architecture prepared.
  * Core Domain Alembic migration successfully generated.

## Next Milestone
Implement Workspaces and initial Business Logic.

## Future Roadmap
* Configure frontend foundation
* Develop knowledge source connectors

## QA & Validations Completed
* **Milestone 1-4 Auth QA:** Completed authentication module validation.
  * Fixed Pydantic V2 deprecation warnings in User schemas.
  * Enforced strong password validation requiring uppercase, lowercase, and numeric characters.
  * Secured JWT configuration by establishing 32-byte secret keys for test and default environments.
  * Verified Swagger UI workflow utilizing HTTPBearer for end-to-end token validation without manual header injection.
  * Cleaned up unused middleware placeholders (auth, metrics, rate_limit).
* **Schema Modernization QA:** Fixed a startup crash caused by outdated `typing` module usage before FastAPI could boot.
  * Audited and modernized `app/schemas/` to use Python 3.13 built-in generics (`list`, `dict`, `T | None`).
  * Removed mutable defaults in Pydantic models in favor of `Field(default_factory=...)`.
  * Validated that the Uvicorn application successfully starts without `NameError`.

## Milestone 5A Completed
* **Google Drive OAuth & Connection Lifecycle**:
  * Implemented `OAuthService` to handle Google OAuth 2.0 Authorization Code Flow.
  * Created `/api/v1/integrations/google/connect` and `/callback` endpoints.
  * Secured OAuth state parameter using a signed JWT encoding the user ID to prevent CSRF.
  * Modified the `Integration` model to belong directly to the `User` instead of `Workspace` (ADR-008 impact).
  * Updated `GoogleDriveConnector` to use stored credentials for its `connect()` and `health_check()` methods.
  * Successfully integrated `httpx` to facilitate server-to-server token exchange.

## Milestone 5B Completed
* **Google Drive File Discovery**:
  * Introduced `NormalizedDocument` schema for provider-independent file representation.
  * Updated `BaseConnector` and `GoogleDriveConnector` to implement `fetch_documents()` with pagination support.
  * Implemented `refresh_google_token` in `OAuthService` to automatically refresh expired access tokens using the stored refresh token.
  * Created `IntegrationService` to orchestrate file fetching and token refreshing without leaking database concerns into the connector layer.
  * Exposed `GET /api/v1/integrations/google/files` endpoint returning paginated `NormalizedDocument` objects.

## Milestone 6A Completed
* **Document Import Pipeline**:
  * Implemented a Canonical `Document` model that acts as the strict boundary between provider-specific external integrations and internal AI processing. This guarantees downstream RAG pipelines never have to handle provider nuances.
  * Extracted physical file storage out of PostgreSQL `LargeBinary` and into local disk storage under `storage/documents/` to improve database performance and scalability.
  * Built an extensible Parser Engine (`app/parsers/`) integrating `pymupdf` and `python-docx` for reliable extraction, ensuring binary files are never incorrectly decoded as UTF-8.
  * Implemented `DocumentImportService` which coordinates fetching, downloading, parsing, and saving both to disk and the database.
  * Added `POST /api/v1/integrations/google/import` API to trigger batch document imports gracefully.
  * **Document Ownership Architecture Update**: Successfully migrated the `Document` ownership model from `Workspace` to `User`. Cleaned up stale relationships (`Workspace.documents`) and ensured SQLAlchemy mapper configures correctly.

## Milestone 7 Completed
* **AI Knowledge Engine Foundation**:
  * **Package Reorganization (ADR-015)**: Consolidated all AI components (`chunking`, `embeddings`, `vectorstore`, `classifier`, `indexing`, `retrieval`, `models`, `prompts`) into a unified `app/ai/` package, utilizing interface-driven design.
  * **Parser Improvements**: Extended parser engine to support CSV, XLSX, and Google Sheets using standard `csv` module and `openpyxl`. Explicitly added support to block legacy `.doc` files gracefully.
  * **Document Classification & Cleaning**: Implemented `DocumentClassifier` to route documents dynamically. Introduced `TypeSpecificCleaner` classes (`PDFCleaner`, `MarkdownCleaner`, `CodeCleaner`, `SpreadsheetCleaner`) to normalize raw text prior to chunking.
  * **Chunking Engine (ADR-011)**: Built a provider-agnostic, pluggable `Chunking Engine` (`RecursiveChunker`, `MarkdownChunker`, `CodeChunker`, `SpreadsheetChunker`). Employs `tiktoken` to capture accurate token counts mapped in `chunk.metadata_`.
  * **Embedding Engine (ADR-012)**: Implemented an abstract `EmbeddingProvider` with `GeminiEmbeddingProvider` as the first implementation, using the `google-genai` SDK and the `text-embedding-004` model.
  * **Vector Store Integration (ADR-013)**: Abstracted `VectorStore` operations and implemented `QdrantVectorStore` connecting to a local Qdrant container for local storage. Included methods for search and deletion.
  * **Indexing Pipeline (ADR-014)**: Created `IndexingService` to unify the pipeline (Parse -> Classify -> Clean -> Chunk -> Embed -> Insert Qdrant -> Insert DB). Uses an asynchronous state machine updating document states (`IMPORTED` -> `PARSING` -> `CHUNKING` -> `EMBEDDING` -> `INDEXED`).
  * **API Support**: Added `POST /api/v1/documents/{id}/index` and `GET /api/v1/documents/{id}/status` for triggering asynchronous processing and fetching progress.

## Milestone 8 Completed
* **Retrieval Engine & LLM Chat**:
  * **Vector Store Enrichment (ADR-016)**: Updated `IndexingService` to embed rich metadata (`document_title`, `provider`, `mime_type`, `source_url`, `user_id`, `integration_id`) directly into Qdrant payloads, avoiding SQL lookups on every chat request.
  * **Retrieval Engine**: Created `RetrievalService` connecting `GeminiEmbeddingProvider` and `QdrantVectorStore` for semantic search, supporting metadata filters and confidence thresholds.
  * **Prompt Builder**: Implemented `PromptBuilder` to format a structured context window and enforce strict rules against hallucination, requiring explicit citations based on the retrieved context.
  * **LLM Engine**: Created `BaseLLMProvider` and implemented `GeminiProvider` utilizing the `google-genai` SDK. Supports both synchronous (`generate`) and streaming (`generate_stream`) text generation.
  * **Chat Service & API (ADR-017)**: Orchestrated the full RAG pipeline through `ChatService`. Exposed `POST /api/v1/chat/query` for standard JSON responses (including citations, scores, and retrieved chunks), `POST /api/v1/chat/stream` using Server-Sent Events (SSE), and a dedicated `POST /api/v1/search` endpoint for testing pure retrieval capabilities.

## Milestone 9 Completed â€” AI Engine Stabilization & Production Hardening
* **Objective**: Completely stabilize the AI pipeline, remove silent failures, implement retry policies, and enable robust logging, health checks, execution recorders, and a collapsible Developer Panel.
* **Architecture Decisions**:
  - Implement a centralized `PipelineExecution` recorder logging the entire execution state (planner output, retrieval explanations, token counts, timings, errors) per request.
  - Implement a fallback mechanism so that the Planner is never a single point of failure (reverting to a default plan: intent=DOCUMENT, response_mode=AUTO, knowledge_mode=AUTO, rewritten_query=query, tools=["retrieval"]).
* **Files Added**:
  - [recorder.py](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/backend/app/ai/pipeline/recorder.py)
* **Files Modified**:
  - [config.py](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/backend/app/ai/config.py)
  - [health.py](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/backend/app/ai/pipeline/health.py)
  - [health.py](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/backend/app/api/v1/health.py)
  - [manager.py](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/backend/app/ai/pipeline/manager.py)
  - [debugger.py](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/backend/app/ai/pipeline/debugger.py)
  - [reasoning.py](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/backend/app/ai/reasoning.py)
  - [builder.py](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/backend/app/ai/prompts/builder.py)
  - [groq_provider.py](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/backend/app/ai/llm/groq_provider.py)
  - [conversation.py](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/backend/app/services/conversation.py)
  - [conversations.py](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/backend/app/api/v1/conversations.py)
  - [use-chat-stream.ts](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/frontend/src/hooks/use-chat-stream.ts)
  - [page.tsx](file:///c:/Users/vansh/OneDrive/Desktop/Conduit/frontend/src/app/(app)/chat/[id]/page.tsx)
* **Files Deleted**: None.
* **Pipeline Flow**:
  1. REQUEST_RECEIVED
  2. VALIDATING (verify conversation ownership and pre-flight health parameters)
  3. PLANNING (route simple queries heuristics or execute LLM planner; falls back to default plan on failure)
  4. RETRIEVING (Qdrant search; retried once; triggers action_required if 0 filtered results in AUTO mode)
  5. OPTIMIZING (Context Optimizer token compression; generates chunk selection/dropped explanations)
  6. PROMPT_BUILDING (calculates tokens for system, context, history, and user; verifies prompt is not empty)
  7. GENERATING / STREAMING (streams chunks via SSE; validates stream sequence is started -> chunks sent -> done/error/action_required)
  8. SAVING (saves query & response messages to Postgres)
  9. COMPLETED / FAILED
* **Debugging Improvements**:
  - Implemented `AI_DEBUG=true` saving logs to request-specific subdirectories under `logs/<date>/pipeline_<id>/` (preventing request logs from overwriting each other).
  - Exposes the `/api/v1/conversations/debug/pipeline/{pipeline_id}` endpoint to query the in-memory execution recorder directly.
* **Error Handling**:
  - Bubbled up timeouts and component failures rather than swallowing them.
  - Implemented 1-retry policy for all major external calls (embeddings, Qdrant search, Groq generation).
  - Exceptions are formatted with stack traces and correlation IDs: `pipeline_id`, `request_id`, `conversation_id`, `user_id`.
* **Streaming Changes**:
  - Periodic heartbeats every 3 seconds to communicate active state (e.g., "Still thinking about your plan...", "Still searching...").
  - Stream integrity assertions confirming the complete SSE stream contract is verified before closure.
* **Configuration**: Added `AI_DEBUG` and `MAX_RETRIES` to `AIConfig` settings.
* **Testing Steps**: Verified backend `pytest` suite runs cleanly. Emitted manual queries to test default planner fallbacks, retrieval explanations, heartbeats, and debug panels.
* **Known Issues**: None.
* **Future Improvements**: Add pricing tracking databases for individual users.
* **Breaking Changes**: `/api/v1/conversations/{id}/query` now expects `user_id` context to enforce document filters.

## Next Milestone
Frontend UI Development and Workspace Management.

## Milestone 10 Completed â€” Production Readiness Audit & Zero-Trust Verification
* **Objective**: Enforce strict Zero-Trust architectural boundaries across all API endpoints, prevent resource leaks in background tasks, ensure pipeline idempotency, and provide exhaustive integration tests for verification.
* **Architecture Decisions**:
  - Bound all conversation and retrieval endpoints strictly to the authenticated `user_id` inside the `ConversationService` (resolving an authorization bypass vulnerability).
  - Explicitly decoupled background job sessions from FastAPI request lifecycles. Introduced `AsyncSessionLocal` wrapper around indexing pipelines (preventing `Transaction Closed` and `MissingGreenlet` errors).
  - Implemented exact mapping for TimingMetrics to overcome silent caching property mismatches.
* **Idempotency & Deduplication**:
  - Updated `DocumentImportService` to match documents on `external_id` and `provider`. Prevents duplicates from Google Drive recursively fetched folders.
  - Re-indexing automatically purges stale chunks in PostgreSQL and explicitly clears matching payloads in Qdrant Vector Store prior to re-processing.
* **Resource Leak Mitigations**:
  - Implemented strict `try...finally` boundaries in `generate_stream` endpoints. Unclean client disconnections now explicitly invoke `worker_task.cancel()` blocking ghost GPU generation loops.
* **Component Testing**:
  - Fixed test database connection mismatches by explicitly overriding the application `AsyncSessionLocal` during pytest runs. 
  - Wrote robust tests (`test_audit.py`) validating strict isolation boundaries for document viewing, querying, and hard-deletion cascade actions.
* **Verification Status**:
  - All test suites (Unit, Database, End-to-End API Routes) successfully pass.
  - Zero bugs identified across the streaming matrix, upload handlers, authentication refreshing, or token scaling algorithms.
  - Production verification complete.


## Milestone 10 (New) Completed — Internal Planner + Executor Architecture (AI OS)
* **Objective**: Redesign Conduit's AI engine into an AI Operating System with strict separation between planning and execution.
* **Architecture Contract**: Frontend NEVER knows about Planner/Executor/Tools. Planner ONLY produces ExecutionPlan JSON. Executor ONLY reads from plan.
* **New Modules**: app/ai/planner/ (PlannerService + schemas + prompt), app/ai/executor/ (Executor + schemas), app/ai/tools/ (BaseTool, ToolRegistry, 4 core tools).
* **Modified**: conversation.py (replaced ReasoningEngine), config.py (new flags), pipeline/recorder.py (extended).
* **Tests**: 38 new AI tests + 9 existing = 47 total, all passing.
* **Extensibility**: New tools require ONLY adding to ToolRegistry — zero Executor changes.

## Milestone 11 Completed — Production Readiness Audit & Overhaul
* **Objective**: Stabilize Conduit into a production-grade AI Knowledge OS: deterministic intent routing, retrieval banding, token budgets, streaming UX, and Developer Panel observability.
* **Planner & Routing**:
  - Intent-based heuristics (not naive prefixes): Document Transformation ? `document_reader`; Fact Lookup ? `document_search`; Comparison ? multi-doc reader; Conversation Memory / Follow-up ? `conversation_memory`; clear world-knowledge ? `general_llm`.
  - Answer length modes: `short` | `medium` (default) | `detailed`, inferred from query cues.
  - Planner version bumped to `2.1.0`.
* **Executor Validation**:
  - `_validate_and_correct_plan` overrides obvious Planner mistakes (summary+search?reader, QA+reader?search, doc tools without docs?GENERAL).
  - Applied on both sync `run` and streaming conversation path.
* **Retrieval**:
  - Similarity bands: High ?0.75, Medium 0.55–0.74, Low 0.35–0.54, Noise <0.35 (always dropped).
  - Normal QA admits Medium+; summaries/comparisons admit Low for coverage.
  - Optimizer merges adjacent chunks and preserves band tags for Developer Panel.
* **Token Budgets**:
  - Max history 6, max chunks 5, max context 3000 tokens (tiktoken-enforced).
  - Compressed citations; debug fields never sent to the LLM.
  - Concise Medium-mode system instruction by default.
* **Chat UX**:
  - Input clears instantly on Enter; optimistic user message; type-ahead while streaming.
  - Visible **Cancel** button aborts the stream and clears partial assistant state.
  - Pipeline stage bubbles (Planning / Searching / Generating) with micro-animations.
  - Minimal **Sources Used** list (document + section count); chunk/similarity detail only in Dev Panel.
* **Developer Panel**:
  - Fixed broken `TABS` declaration; bottom drawer with Overview, Planner, Execution Plan, Tools, Retrieval, Chunks, Prompt, Tokens (budget dashboard), Latency, Logs, Timeline, Errors.
* **Verification**:
  - Unit coverage for intent matrix, determinism, executor overrides, tools — all passing (`tests/ai/`).
  - Scenario matrix covered in tests: greeting, summarize, rewrite/improve, compare, fact lookup, general knowledge (capital of France), conversation memory, follow-up, no-docs fallback.
* **Performance Targets (design constraints)**:
  - Heuristic planner <500ms; retrieval timeout 5s; streaming first-token target <2.5s; ?40% prompt reduction via budgets vs unbounded context.
* **Files Modified**:
  - `backend/app/ai/planner/planner.py`, `schemas.py`, `prompt.py`
  - `backend/app/ai/executor/executor.py`
  - `backend/app/ai/config.py`
  - `backend/app/ai/tools/document_search.py`
  - `backend/app/ai/retrieval/optimizer.py`
  - `backend/app/services/conversation.py`
  - `backend/tests/ai/test_planner.py`, `test_executor.py`
  - `frontend/src/components/chat/composer.tsx`, `message-bubble.tsx`, `dev-panel.tsx`
  - `frontend/src/hooks/use-chat-stream.ts`
* **Breaking Changes**: None for API clients. Frontend Sources UI is intentionally minimal.
* **Known Issues**: Live E2E latency/token metrics should be captured against a warm LLM/Qdrant stack during deploy validation.
* **Next Milestone**: Workspace management UI polish and connector expansion.

