# Backend Service

The backend lives in `backend/` and is the first active implementation target for Sirat Al Mustaqeem AI. It is a standalone FastAPI service using Python 3.12, uv, Pydantic v2, async httpx, Supabase Auth/REST, and multi-provider LLM routing.

## Current Scope

Implemented:

- FastAPI app scaffold with CORS, lifespan, routers, dependencies, and middleware.
- Public health check.
- Supabase JWT verification using PyJWT and cached JWKS.
- Local-development auth bypass for Swagger UI testing.
- Dependency-based in-memory sliding-window rate limiting keyed by user id.
- Conversation and message CRUD through Supabase REST.
- SSE chat streaming directly to the configured LLM providers.
- Debug-only unauthenticated chat streaming route for local Swagger testing.
- LLM provider failover: Groq, then Gemini, then OpenRouter.
- Dockerfile for the backend service.
- Swagger UI testing through FastAPI docs.
- Document ingestion pipeline: PDF/DOCX/TXT extraction, Islamic-aware chunking, Gemini embedding, and Supabase vector storage.
- Admin document management routes (`POST /admin/documents/upload`, list, detail, delete, reprocess) and ingestion job listing.
- Startup recovery: on every boot, jobs stuck mid-run (`extracting`, `chunking`, `embedding`, `storing`) from a previous crash or restart are automatically re-queued.
- CPU-bound extraction and chunking run in a thread pool via `asyncio.to_thread` so they never block the async event loop.
- RAG pipeline: `app/services/search.py` embeds queries with Gemini `RETRIEVAL_QUERY`, calls the `match_chunks` pgvector RPC, and injects a formatted context block into the LLM system prompt.
- Citation extractor: `app/utils/citations.py` parses `[Quran X:Y]`, `[Hadith Collection, N]`, and `[Author, Book]` patterns from LLM responses and stores them in `messages.citations`.

Not implemented yet:

- Islamic source retrieval pipeline (re-ranking, multi-hop reasoning).

## Conventions

- Keep route modules under `backend/app/routers`.
- Register routers in `backend/app/main.py`.
- Keep environment parsing in `backend/app/config.py` using `pydantic-settings`.
- Keep shared FastAPI dependencies in `backend/app/dependencies.py`.
- Keep request and response schemas in `backend/app/models/schemas.py`.
- Keep persistence and provider integrations in `backend/app/services`.
- Keep all network I/O async with `httpx` or async SDK clients.
- Use the API response envelope pattern for JSON routes: `{ data, error, message }`.
- Use SSE for streamed chat responses.
- Do not add RAG or ingestion code until the core backend API is stable.

## RAG Architecture

The RAG stack is built from scratch with direct API calls and pure Python. No LangChain, LlamaIndex, or similar framework is used.

**Why no framework:**
LangChain and LlamaIndex abstract over the parts that matter most here. Their splitters have no concept of ayah or hadith boundaries; their retrieval chains assume generic Q&A. For an Islamic knowledge base the chunk boundaries, metadata per doc type, and citation structure are domain-specific enough that framework abstractions fight you more than they help.

**What this means in practice:**

- `embedder.py` calls Gemini `batchEmbedContents` directly via `httpx`. No SDK wrapper.
- `chunker.py` is hand-written Islamic-aware logic: Quran splits at ayah boundaries, hadith kept as full units, general text uses a sliding-window by word count.
- `supabase.py` inserts chunks via Supabase REST and will query via a raw `rpc()` call to a pgvector `match_documents` function.
- Retrieval query (`semantic_search` in `app/services/search.py`) calls `match_chunks` via Supabase RPC, builds a formatted context block, and injects it into the LLM system prompt before every chat request.
- Citation extraction (`app/utils/citations.py`) parses the completed LLM response and stores structured citations in `messages.citations`.
- Re-ranking and multi-hop reasoning are not yet built.

The tradeoff is more code to write, but full control over every decision that affects answer quality and citation accuracy.

## Route Structure

```text
backend/app/routers/health.py
backend/app/routers/chat.py
backend/app/routers/admin.py
```

Routes should validate inputs with Pydantic models, delegate business logic to service modules, and avoid direct provider or database logic inside route handlers.

## Routes

- `GET /health`: public health check with request/client details.
- `POST /chat/stream`: authenticated SSE chat stream.
- `POST /chat/stream/test`: unauthenticated debug-only SSE chat stream.
- `GET /chat/conversations`: authenticated conversation list.
- `POST /chat/conversations`: authenticated conversation create.
- `GET /chat/conversations/{conversation_id}`: authenticated conversation detail with messages.
- `GET /chat/conversations/{conversation_id}/messages`: authenticated message history.
- `DELETE /chat/conversations/{conversation_id}`: authenticated conversation delete.
- `GET /chat/search?q=...`: authenticated semantic search over indexed documents; returns ranked chunks with similarity scores and source labels.
- `GET /admin/ingestion-jobs/{job_id}/stream`: authenticated SSE stream that pushes job + document status every 2 s until the job reaches `completed` or `failed`.
- `GET /admin/status`: authenticated placeholder admin status route.

## Auth

`backend/app/middleware/auth.py` verifies Supabase access tokens using the Supabase JWKS endpoint. JWKS responses are cached for one hour by default and both RSA (`RS256`) and elliptic-curve (`ES256`) keys are supported.

Authenticated routes should use `get_current_user` from `backend/app/middleware/auth.py` or its compatibility re-export in `backend/app/dependencies.py`. The dependency returns `UserContext(user_id, email, role, claims)`.

Role resolution order:

1. JWT `app_metadata.role` or `user_metadata.role`.
2. `profiles.role` from Supabase REST.
3. Default `user`.

For local Swagger UI testing, `AUTH_REQUIRED=false` allows protected routes to run without a bearer token. Requests without a token use `LOCAL_DEV_USER_ID` and `LOCAL_DEV_USER_EMAIL` as the authenticated user. If a bearer token is supplied, it is still verified normally.

The bypass is only available when `ENVIRONMENT=local` or `ENVIRONMENT=test`. Deployed environments should set `ENVIRONMENT=production` and `AUTH_REQUIRED=true`.

If Supabase tables enforce a foreign key to `auth.users`, set `LOCAL_DEV_USER_ID` to an existing Supabase user UUID before testing conversation writes.

For deployed Swagger testing, use the Swagger Authorize button with a real Supabase access token instead of relying on local bypass.

Production-like environments should set `ENVIRONMENT=production` and `AUTH_REQUIRED=true`.

## Swagger Chat Testing

When starting a new chat through Swagger, omit `conversation_id` or send `null`. The backend normalizes Swagger's placeholder value `"string"` to `null` so it creates a new conversation instead of trying to save messages to a fake id.

## Health Details

`GET /health` returns the standard API envelope and includes client/request details available to the backend server:

- request method, URL, path, query, and scheme
- connection host, port, server, and HTTP version
- request headers with sensitive values redacted
- common proxy headers

## Rate Limiting

`backend/app/middleware/rate_limit.py` exposes `check_rate_limit`, a FastAPI dependency that applies an in-memory sliding-window limiter keyed by authenticated `user_id`.

- Limit: 30 requests per minute per user.
- Response: `429 Too Many Requests`.
- Header: `Retry-After`.

This is intentionally simple for local development and Swagger UI testing. Redis or another distributed limiter should replace it before multi-instance production deployment.

## LLM Routing

Provider files live under `backend/app/services/llm`:

- `base.py`: provider protocol and shared exceptions.
- `openai_compatible.py`: shared OpenAI-compatible streaming transport.
- `groq.py`: Groq through the OpenAI-compatible async SDK.
- `gemini.py`: Gemini through the OpenAI-compatible async SDK.
- `openrouter.py`: OpenRouter through the OpenAI-compatible async SDK.
- `router.py`: provider orchestration and failover.

The router injects the Sirat Al Mustaqeem AI system prompt into every LLM request and tries providers in this order:

1. Groq
2. Gemini
3. OpenRouter

Provider failures and rate-limit failures fall through to the next configured provider.

## Persistence

The backend currently uses Supabase REST through `backend/app/services/supabase.py` instead of direct SQLAlchemy models. Conversation workflows are coordinated by `backend/app/services/conversation.py`.

Supported operations:

- `create_conversation(user_id, title?)`
- `get_conversations(user_id, limit=20, offset=0)`
- `get_conversation(conversation_id, user_id)`
- `delete_conversation(conversation_id, user_id)`
- `add_message(conversation_id, role, content, citations?)`

When `POST /chat/stream` omits `conversation_id`, the backend creates a conversation automatically and uses the LLM to summarize the first user message into a title of five words or fewer.

Expected Supabase tables:

- `conversations`
- `messages`

The backend verifies user ownership through authenticated user IDs and the Supabase rows returned by the REST API.

## Local Workflow

Install dependencies:

```bash
cd backend
uv sync
```

Run the API:

```bash
uv run uvicorn app.main:app --reload
```

Use Swagger UI for manual backend testing:

```text
http://localhost:8000/docs
```
