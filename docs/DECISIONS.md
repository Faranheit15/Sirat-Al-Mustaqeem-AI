# Decisions

# Architecture Decisions

## 2026-05-23: No monorepo
- **Context:** Started with Turborepo, got messy fast
- **Decision:** Separate backend/ and frontend/ directories, no workspace linking
- **Reason:** Solo developer, sequential build order, Docker Compose for local dev

## 2026-05-23: Supabase Auth over Clerk
- **Context:** Need auth for web + mobile + FastAPI
- **Decision:** Supabase Auth with JWT verification in FastAPI
- **Reason:** Already using Supabase for DB, free RLS integration, no per-user pricing

## 2026-05-23: Backend-first development
- **Context:** Need to decide build order
- **Decision:** Build and fully test backend from Swagger UI before touching frontend
- **Reason:** Backend is the core product (RAG + LLM). Frontend is a skin on top.

## 2026-05-23: Multi-provider LLM failover
- **Context:** Can't afford a single paid API
- **Decision:** Groq primary → Gemini fallback → OpenRouter tertiary
- **Reason:** Combined free tiers give ~16K+ requests/day

## 2026-05-23: Stdlib logging with JSON formatter
- **Context:** Need global logging for auditing and debugging post-deployment
- **Decision:** Use Python's stdlib `logging` module with a custom JSON formatter for production and human-readable format for development
- **Reason:** Zero new dependencies, works natively with container log drivers (CloudWatch, Datadog, GCP Logging), configurable via `LOG_LEVEL` env var, and all loggers inherit from a single `app` namespace

## 2026-05-23: GitHub Actions for CI/CD to FastAPI Cloud
- **Context:** Need automated deployment to FastAPI Cloud on every push to main
- **Decision:** Single workflow file `.github/workflows/backend.yml` with two jobs: `lint` (always) and `deploy` (main only, gated on lint)
- **Reason:** Lint must pass before any deploy reaches production; PRs get CI feedback without triggering deploys; path filters prevent the workflow from running on frontend-only changes; `cancel-in-progress` is true only for PRs so production deploys are never interrupted by a following push

## 2026-05-23: Embedding via Gemini REST API (not SDK)
- **Context:** Need async embeddings for pgvector storage in the ingestion pipeline
- **Decision:** Call `generativelanguage.googleapis.com/v1beta/{model}:batchEmbedContents` via httpx instead of using the `google-generativeai` SDK
- **Reason:** The SDK's `embed_content` is synchronous — running it in an async FastAPI handler requires `run_in_executor`, adding thread-pool overhead. The REST call is natively async and produces identical results.

## 2026-05-23: Ingestion in BackgroundTasks, not a job queue
- **Context:** Need to run multi-step extract→chunk→embed→store pipeline without blocking the upload response
- **Decision:** Use FastAPI's built-in `BackgroundTasks` for now; progress tracked in `ingestion_jobs` table
- **Reason:** Simplicity — no Redis, Celery, or worker processes needed initially. Migrating later requires only swapping the `background_tasks.add_task(...)` call.

## 2026-05-23: Islamic-aware text chunking
- **Context:** Splitting Islamic texts naively (by character count) damages RAG quality
- **Decision:** Auto-detect Quran vs hadith vs general prose, apply different chunking strategies per type; Quran splits at ayah boundaries, hadith kept as full units
- **Reason:** Semantic integrity of the retrieved context is essential for accurate fatwa/citation responses. A split-ayah or isnad-without-matn would be meaningless to the LLM.

## 2026-05-23: /health/db with no auth
- **Context:** Need to verify DB connectivity from Swagger UI and uptime monitors
- **Decision:** Endpoint returns status, table names, and full error text in the response body; no auth required
- **Reason:** Auth would defeat the purpose. No sensitive data is exposed — only connection status and table names. Errors land in the response body so Swagger always shows the full message.

## 2026-05-24: Switched default embedding to local sentence-transformers
- **Context:** Gemini embedding API (gemini-embedding-001) kept returning 429 Too Many Requests on the free tier — even with 13 s inter-batch delays and exponential backoff retries, a 100-chunk batch regularly exhausted the quota.
- **Decision:** Replace the Gemini embedding call with a local `sentence-transformers` model (`all-MiniLM-L12-v2`, 384 dims). The model is loaded once at startup and cached at module level. Encoding runs in `asyncio.to_thread` so it never blocks the async event loop. Gemini is kept as an optional fallback via `EMBEDDING_PROVIDER=gemini`.
- **Reason:** Local inference has zero API cost, no rate limits, and encodes 1000 chunks in a few seconds on CPU. The tradeoff is a ~90 MB model download at first startup and a dimension change from 768 to 384. The `match_chunks` pgvector function and `document_chunks.embedding` column are updated in migration `004_resize_embedding.sql`. The main tradeoff is Docker image size: `sentence-transformers` pulls in PyTorch (~2 GB on disk); if image size is a hard constraint, switching to `EMBEDDING_PROVIDER=gemini` avoids that dependency.

## Initial Platform Decisions (deprecated, ignore)

- Use Turborepo for the monorepo so the web app, API service, and shared TypeScript packages can evolve together with cached task orchestration.
- Use Bun as the JavaScript package manager and command runner.
- Use Supabase Auth for authentication because it pairs well with hosted Postgres and supports web and future mobile clients.
- Use Groq as the primary LLM provider for fast inference.
- Use FastAPI for the backend to keep the AI, retrieval, auth integration, and database boundaries explicit.
- Use Next.js 15 App Router for the web app.
- Use TypeScript strict mode across all TypeScript apps and packages.
