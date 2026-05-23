# Sirat Al Mustaqeem AI Backend

FastAPI backend for the Islamic research assistant. This app is intentionally independent from the future frontend and mobile apps.

## Install

```bash
cd backend
uv sync
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

Swagger UI:

```text
http://localhost:8000/docs
```

Health check:

```text
GET http://localhost:8000/health
```

## Required Supabase Tables

Run these SQL migrations in your Supabase project before using the ingestion routes:

```sql
-- Enable pgvector
create extension if not exists vector;

-- Documents table
create table documents (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  file_path text,
  file_type text not null,
  file_size integer,
  language text,
  page_count integer,
  is_ocr boolean default false,
  status text not null default 'pending',
  chunk_count integer default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  metadata jsonb
);

-- Document chunks with pgvector embeddings
create table document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  embedding vector(768),
  doc_type text,
  language text,
  metadata jsonb,
  created_at timestamptz default now()
);
create index on document_chunks using ivfflat (embedding vector_cosine_ops);

-- Ingestion jobs
create table ingestion_jobs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  status text not null default 'pending',
  progress integer default 0,
  error_log text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz default now()
);
```

Also create a Supabase Storage bucket named `documents` (or the value of `SUPABASE_STORAGE_BUCKET`).

## Environment Variables

Create `backend/.env` from `backend/.env.example`.

Required for authenticated chat routes:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_AUDIENCE`

LLM provider configuration:

- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`

Runtime configuration:

- `ENVIRONMENT`
- `DEBUG`
- `API_TITLE`
- `API_VERSION`
- `API_CORS_ORIGINS`
- `AUTH_REQUIRED`
- `LOCAL_DEV_USER_ID`
- `LOCAL_DEV_USER_EMAIL`
- `RATE_LIMIT_REQUESTS_PER_MINUTE`
- `JWKS_CACHE_TTL_SECONDS`
- `HTTP_TIMEOUT_SECONDS`

Document ingestion configuration:

- `SUPABASE_STORAGE_BUCKET` (default `documents`)
- `GEMINI_EMBEDDING_MODEL` (default `models/text-embedding-004`)
- `INGESTION_CHUNK_SIZE` (default `500` tokens)
- `INGESTION_CHUNK_OVERLAP` (default `50` tokens)

Protected routes require a Supabase bearer token. For local Swagger chat testing without a JWT, set `DEBUG=true` and use `POST /chat/stream/test`.

Deployed environments should set:

- `ENVIRONMENT=production`
- `DEBUG=false`
- `AUTH_REQUIRED=true`

The legacy local auth bypass is only available when `ENVIRONMENT=local` or `ENVIRONMENT=test` and `AUTH_REQUIRED=false`.

## API Routes

- `GET /health`: public health check with request/client details visible to the backend server.
- `GET /health/db`: public DB connectivity check — returns Supabase status and table names; errors visible in Swagger UI.
- `POST /chat/stream`: authenticated SSE chat stream.
- `POST /chat/stream/test`: unauthenticated debug-only SSE chat stream.
- `GET /chat/conversations`: authenticated conversation list.
- `POST /chat/conversations`: authenticated conversation create.
- `GET /chat/conversations/{conversation_id}`: authenticated conversation detail with messages.
- `GET /chat/conversations/{conversation_id}/messages`: authenticated message history.
- `DELETE /chat/conversations/{conversation_id}`: authenticated conversation delete.
- `POST /admin/documents/upload`: admin — upload PDF/DOCX/TXT (max 50 MB), queues ingestion job.
- `GET /admin/documents`: admin — list all documents with status.
- `GET /admin/documents/{id}`: admin — document detail with chunk count.
- `DELETE /admin/documents/{id}`: admin — delete document, chunks, and stored file.
- `POST /admin/documents/{id}/reprocess`: admin — re-run ingestion pipeline on existing file.
- `GET /admin/ingestion-jobs`: admin — list all ingestion jobs with progress.
- `GET /admin/status`: admin — admin health check.

For `POST /chat/stream`, omit `conversation_id` or set it to `null` when starting a new conversation. Swagger UI may show `"string"` as a placeholder; the backend normalizes that placeholder to `null`.

### SSE event format

Each SSE response contains three event types:

```
event: delta
data: {"content": "<token>", "provider": "groq"}

event: done
data: {"done": true, "provider": "groq", "conversation_id": "<uuid>"}

event: error
data: {"error": "<message>"}
```

### Provider failover

Providers are tried in order: **Groq → Gemini → OpenRouter**. Before each attempt the router checks whether the cached rate-limit headers from the previous response on that provider show quota exhausted. On failure (429 or connection error) the router waits 1 s before the second provider and 2 s before the third.

## Architecture Overview

- `app/main.py`: FastAPI app factory, lifespan, CORS, middleware, router includes.
- `app/config.py`: Pydantic Settings loaded from `.env`.
- `app/dependencies.py`: shared auth and service dependencies.
- `app/middleware/auth.py`: Supabase JWT verification with cached JWKS.
- `app/middleware/rate_limit.py`: in-memory sliding window limiter.
- `app/routers`: HTTP route modules.
- `app/services/llm`: OpenAI-compatible Groq, Gemini, OpenRouter, and provider failover.
  - `prompts.py`: Islamic system prompt constant.
  - `base.py`: `LLMProvider` protocol (`stream_chat`, `complete`, `check_rate_limit`).
  - `openai_compatible.py`: shared implementation — streaming, non-streaming, rate-limit header caching, connection-error handling.
  - `router.py`: `ProviderRouter` — quota pre-check, exponential back-off (1 s / 2 s / 4 s), failover across Groq → Gemini → OpenRouter.
- `app/services/supabase.py`: async `httpx` wrapper for Supabase REST.
- `app/services/conversation.py`: conversation and message CRUD.
- `app/models/schemas.py`: Pydantic request/response models.
- `app/utils/streaming.py`: SSE helpers and assistant response persistence.

## Local Auth Behavior

Protected routes use `get_current_user`, which verifies Supabase JWTs against the Supabase JWKS endpoint. The dependency checks token expiration, audience, and issuer, then extracts `sub` as `user_id`, `email`, and `role`.

Role resolution order:

1. JWT `app_metadata.role` or `user_metadata.role`.
2. `profiles.role` from Supabase REST.
3. Default `user`.

Use Swagger's **Authorize** button with:

```text
Bearer <supabase-access-token>
```

When `ENVIRONMENT=local` and `AUTH_REQUIRED=false`, requests without a bearer token are treated as the configured local development user. If a bearer token is supplied, the backend still verifies it against Supabase.

Production and staging environments should set:

```text
ENVIRONMENT=production
DEBUG=false
AUTH_REQUIRED=true
```

Supabase configuration is still required for conversation and message persistence.

## Rate Limiting

Chat and conversation routes use a dependency-based sliding-window rate limiter keyed by `user_id`.

- Limit: 30 requests per minute per user.
- Response on limit: `429 Too Many Requests`.
- Includes a `Retry-After` response header.

## Conversation Management

Conversation persistence uses the Supabase REST client, not raw SQL.

Supported operations:

- Create a conversation with an optional title.
- List conversations with `limit` and `offset`.
- Fetch a conversation with its messages.
- Delete a conversation by id.
- Add user and assistant messages after chat streaming completes.

If `POST /chat/stream` omits `conversation_id`, the backend auto-creates a conversation and asks the LLM for a title of five words or fewer based on the first user message.

## Debug Chat Testing

`POST /chat/stream/test` is available only when `DEBUG=true`. It skips JWT auth so Swagger UI can verify LLM streaming before frontend auth exists. It uses `LOCAL_DEV_USER_ID` for persistence, so set that value to a real Supabase auth user UUID if your tables enforce user foreign keys.

## Health Response

`GET /health` returns the standard API envelope with service status plus client details available to the backend server:

- request method, URL, path, query, and scheme
- connection host, port, server, and HTTP version
- request headers with sensitive values redacted
- common proxy headers such as `x-forwarded-for`

## Document Ingestion

Admin routes accept PDF, DOCX, and TXT files up to 50 MB. The pipeline runs in a FastAPI `BackgroundTasks` task with progress tracked in the `ingestion_jobs` table:

1. **Extract** — `pypdf` for text PDFs; pytesseract OCR fallback for scanned PDFs (Arabic + Urdu + English); `python-docx` for DOCX; chardet encoding detection for TXT.
2. **Chunk** — Islamic-aware: Quran text split at ayah boundaries, hadith kept as complete units (isnad + matn), general text chunked by token count with configurable overlap.
3. **Embed** — Gemini `text-embedding-004` via the REST `batchEmbedContents` endpoint in batches of 100.
4. **Store** — chunk rows with 768-dim pgvector embeddings written to `document_chunks`.

For OCR of scanned PDFs, pytesseract must be installed along with the `tesseract-ocr` system binary and the `ara`, `urd`, and `eng` language packs.

## Current Scope

Implemented now:

- Authenticated chat streaming directly to LLM providers.
- Conversation and message persistence through Supabase REST.
- Provider failover: Groq, then Gemini, then OpenRouter.
- Document ingestion pipeline with admin management routes.
- pgvector embeddings stored in Supabase for future RAG.

Not implemented yet:

- RAG/vector search (embeddings are stored; query pipeline is next).
- Admin functionality beyond document management.
