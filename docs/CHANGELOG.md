# Changelog

All notable changes to Sirat Al Mustaqeem AI will be documented in this file.

## [Unreleased]

### Added

- RAG search service (`app/services/search.py`): `semantic_search()` embeds the query via Gemini `RETRIEVAL_QUERY` task type, calls the `match_chunks` Supabase RPC, and returns ranked `SearchResult` objects with `source_label()` helpers for context formatting. Returns an empty list gracefully if no documents are indexed or the embedding call fails.
- `match_chunks` PostgreSQL function (`migrations/003_match_chunks.sql`): pgvector cosine similarity search over `document_chunks`, joined with `documents`, filtered to `status = 'completed'`, with configurable `match_count` and `match_threshold` parameters.
- Citation extractor (`app/utils/citations.py`): `extract_citations()` parses `[Quran X:Y]`, `[Hadith Collection, N]`, and `[Author, Book, ...]` bracket patterns from LLM response text, deduplicates, and returns structured `Citation(type, reference)` objects.
- `embed_query()` in `app/services/ingestion/embedder.py`: single-string embedding using `RETRIEVAL_QUERY` task type (asymmetric vs ingestion's `RETRIEVAL_DOCUMENT`).
- `SupabaseClient.match_chunks()`: POST to `/rpc/match_chunks` with query vector, match count, and threshold.
- `GET /chat/search`: authenticated semantic search endpoint — accepts `q`, `top_k` (1–20), and `threshold` (0–1) query params; returns ranked chunks with similarity scores and source labels. Useful for debugging RAG retrieval independently.
- RAG wired into `POST /chat/stream` and `POST /chat/stream/test`: before each LLM call the latest user message is embedded, top-k chunks are retrieved, and a context block is appended to the system prompt. If no chunks are found, chat proceeds without context (no failure).
- New `event: sources` SSE event emitted before the first `delta` event when RAG finds results: `data: [{"chunk_id", "document_id", "document_title", "source_label", "doc_type", "similarity"}, ...]`. Lets the frontend display sources before the response starts streaming.
- Extracted citations are now stored in the `messages.citations` JSONB column for the assistant message.
- `event: done` payload now includes a `citations` field: `[{"type", "reference", "source_doc_id"}, ...]`.
- `RAG_TOP_K` (default `5`) and `RAG_THRESHOLD` (default `0.7`) environment variables added to `Settings`.
- New Pydantic schemas: `SearchResult`, `Citation`, `SearchData`, `SearchResponse`.

### Fixed

- `GET /admin/ingestion-jobs/{job_id}/stream` SSE endpoint: streams job status, progress, error_log, doc_status, page_count, chunk_count, language, and is_ocr every 2 s until the job reaches `completed` or `failed`. Uses `event: progress` for intermediate ticks and `event: done` for the terminal event. Client disconnect is handled gracefully via `asyncio.CancelledError`.
- Added `SupabaseClient.get_ingestion_job(job_id)` to fetch a single ingestion job by id.

- Ingestion pipeline no longer blocks the async event loop during PDF/DOCX/TXT extraction and text chunking. Both `extract_document()` and `chunk_document()` are now offloaded to a thread pool via `asyncio.to_thread`, so large documents (e.g. the full Quran PDF) do not freeze the server while being processed.
- Startup recovery hook in `app/main.py` lifespan: on every boot, any ingestion job stuck in `extracting`, `chunking`, `embedding`, or `storing` (caused by a process restart mid-run) is automatically re-queued. Each stuck job downloads its file from Supabase Storage and re-runs the full pipeline. If the file or document is missing, the job is marked `failed` with a descriptive `error_log`.
- Added `SupabaseClient.list_stuck_ingestion_jobs()` to query the `ingestion_jobs` table for interrupted jobs by status.

- Supabase Storage upload now sends `x-upsert: true` and `cache-control: max-age=3600` headers, preventing 400 errors on re-upload of a file that already exists in the bucket.
- `SupabaseClient._request()` now logs the full Supabase response body on HTTP errors, making PostgREST failures visible in server logs instead of only surfacing the status code.
- `_require_admin` dependency now uses the `Annotated[UserContext, Depends(get_current_user)]` alias instead of the bare `UserContext` dataclass, fixing a FastAPI bug where `current_user` appeared as a multipart form field and caused 422 errors on `POST /admin/documents/upload`.

### Added

- Document ingestion pipeline: `app/services/ingestion/` package with `extractor.py` (PDF/DOCX/TXT extraction with optional pytesseract OCR for scanned PDFs), `chunker.py` (Islamic-aware chunking — Quran at ayah boundaries, hadith as full units, general semantic sliding-window), `embedder.py` (async Gemini `text-embedding-004` via REST batchEmbedContents), and `pipeline.py` (orchestrated extract→chunk→embed→store with per-step job status updates).
- Admin document management routes replacing the placeholder in `app/routers/admin.py`: `POST /admin/documents/upload`, `GET /admin/documents`, `GET /admin/documents/{id}`, `DELETE /admin/documents/{id}`, `POST /admin/documents/{id}/reprocess`, `GET /admin/ingestion-jobs`. All routes require auth and admin/local_dev role.
- File storage: raw uploads go to Supabase Storage bucket (`SUPABASE_STORAGE_BUCKET`); path stored in `documents.file_path`.
- `GET /health/db` endpoint (no auth) that pings the Supabase REST API, returns DB status, discovered table names, and error details if unreachable — visible in Swagger UI.
- New Pydantic schemas: `Document`, `IngestionJob`, `DocumentUploadData/Response`, `DocumentListData/Response`, `DocumentDetailData/Response`, `IngestionJobListData/Response`, `IngestionJobResponse`, `DbHealthData/Response`.
- New `SupabaseClient` methods: `upload_file`, `delete_file`, `create_document`, `list_documents`, `count_documents`, `get_document`, `update_document`, `delete_document`, `insert_chunks` (batched 50/request), `delete_chunks`, `create_ingestion_job`, `update_ingestion_job`, `list_ingestion_jobs`, `get_ingestion_job_by_document`, `check_db`.
- New dependencies: `pypdf`, `python-docx`, `pytesseract`, `chardet`, `google-generativeai`, `Pillow`.
- New config fields: `SUPABASE_STORAGE_BUCKET`, `GEMINI_EMBEDDING_MODEL`, `INGESTION_CHUNK_SIZE`, `INGESTION_CHUNK_OVERLAP`.
- mypy override for `pytesseract` (no `py.typed` marker) and `google.generativeai`.

- `app/services/llm/prompts.py` — Islamic system prompt extracted into its own module; `router.py` now imports from it.
- `complete()` non-streaming method and `check_rate_limit()` quota pre-check added to `LLMProvider` protocol and `OpenAICompatibleProvider`.
- `extra_headers` field on `OpenAICompatibleProvider`; `OpenRouterProvider` passes the required `HTTP-Referer` and `X-Title` headers.
- `APIConnectionError` is now caught and converted to `ProviderUnavailableError` so connection failures trigger the same failover path as rate limits.
- Both `x-ratelimit-remaining-requests` and `x-ratelimit-remaining-tokens` headers are now parsed and stored per provider.
- `ProviderRouter` skips providers whose cached quota is known-exhausted via `check_rate_limit()`, then applies exponential back-off (1 s → 2 s → 4 s) between retries.
- Model name is logged at every `llm_attempt` and `llm_success` event.
- SSE delta and done events now carry JSON payloads `{"content": "...", "provider": "groq"}` and `{"done": true, "provider": "groq", "conversation_id": "..."}`.
- Model defaults corrected: `gemini-2.5-flash`, `meta-llama/llama-3.3-70b-instruct:free`.

- Widened `requires-python` from `">=3.12,<3.13"` to `">=3.12"` and regenerated `uv.lock` to unblock FastAPI Cloud builds (build environment ships Python 3.13; the old strict upper bound caused uv to fail with `No such file or directory` when looking for `python3.12`).
- GitHub Actions workflow `.github/workflows/backend.yml` for backend CI/CD: ruff lint, ruff format check, and mypy on every PR; deploy to FastAPI Cloud on every push to main (deploy job is gated on lint passing).
- Fixed `backend/Dockerfile` to copy `uv.lock` alongside `pyproject.toml` and use `uv sync --frozen --no-dev` for reproducible production image builds.

- Independent FastAPI backend scaffold in `backend/` using Python 3.12 and uv.
- Pydantic v2 settings module with typed environment variables and validation.
- FastAPI app setup with lifespan, CORS, health, chat, and admin routers.
- Supabase JWT verification with PyJWT, async JWKS fetching, one-hour JWKS caching, and RS256/ES256 key support.
- Authenticated user dependency and async Supabase REST wrapper.
- In-memory sliding-window rate limiter for chat routes.
- Conversation and message CRUD service backed by Supabase REST.
- SSE chat streaming endpoint at `POST /chat/stream`.
- Multi-provider LLM layer with Groq, Gemini, and OpenRouter providers plus failover routing.
- Sirat Al Mustaqeem AI Islamic research assistant system prompt on every LLM request.
- Backend Dockerfile based on `python:3.12-slim`.
- Backend `.env.example` and README with install, run, env, route, and architecture documentation.
- Frontend placeholder README documenting the planned Next.js stack and backend integration.
- Mobile placeholder README marking the app as Phase 3.
- Repository-level README with project overview, stack, layout, backend quick start, API summary, and development principles.
- CONTRIBUTING guide with workflow, style, documentation, secrets, and architecture guardrails.
- Backend `.gitignore` and `.dockerignore`.
- Local-development auth bypass for Swagger UI testing through `AUTH_REQUIRED=false`.
- Expanded health response with request, connection, header, and proxy details visible to the backend.
- Production-safe auth behavior that prevents local bypass unless `ENVIRONMENT=local` or `ENVIRONMENT=test`.
- Chat request normalization for Swagger's `"string"` conversation id placeholder.
- Global structured logging system with JSON output in production and human-readable output in development.
- `RequestLoggingMiddleware` that logs every HTTP request with method, path, status code, and duration.
- Per-module loggers across all layers: routers, services, LLM providers, middleware, auth, and Supabase client.
- Configurable `LOG_LEVEL` environment variable (default `INFO`) with runtime validation.
- Security-aware logging that never exposes API keys, tokens, user emails, or message contents.
- Supabase auth dependency in `app/middleware/auth.py` with JWKS caching, exp/aud/iss validation, user id/email extraction, and role resolution from JWT metadata or `profiles.role`.
- Dependency-based sliding-window rate limiter keyed by `user_id`, limited to 30 requests per minute with `Retry-After` headers.
- Conversation detail endpoint `GET /chat/conversations/{conversation_id}` returning a conversation with messages.
- Debug-only unauthenticated chat stream endpoint `POST /chat/stream/test` for Swagger UI testing when `DEBUG=true`.
- Automatic conversation creation on chat stream requests without `conversation_id`.
- LLM-generated conversation titles of five words or fewer for new chat streams.

### Changed

- Restarted the project direction from a Turborepo monorepo to independent `backend/`, `frontend/`, and `mobile/` folders.
- Updated backend documentation to match the new standalone FastAPI architecture.
- Updated service docs to describe the backend-first standalone app direction instead of the old monorepo packages.
- Updated agent guide files to reference app READMEs for `backend/`, `frontend/`, and `mobile/`.
- Renamed frontend service documentation from `web.md` to `frontend.md`.
- Updated backend docs for local auth behavior and detailed health responses.
- Replaced the deprecated `google-generativeai` Gemini transport with the OpenAI-compatible Gemini endpoint through the OpenAI SDK.
- Documented deployed Swagger testing requirements for auth and new chat requests.
- Moved chat rate limiting from global middleware to explicit route dependencies so limits are keyed by authenticated user id.
- Expanded conversation service methods to support create, list with pagination, detail with messages, delete, and add-message operations through Supabase.

### Removed

- Old `apps/` monorepo implementation after the backend-first reset.
- Turborepo/package workspace files from the previous scaffold.
- Obsolete shared package service documentation.

### Verified

- `uv sync --cache-dir .uv-cache`
- `uv run --cache-dir .uv-cache ruff check .`
- `uv run --cache-dir .uv-cache mypy app`
- FastAPI import and route registration smoke check.
