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
- `API_TITLE`
- `API_VERSION`
- `API_CORS_ORIGINS`
- `AUTH_REQUIRED`
- `LOCAL_DEV_USER_ID`
- `LOCAL_DEV_USER_EMAIL`
- `RATE_LIMIT_REQUESTS_PER_MINUTE`
- `JWKS_CACHE_TTL_SECONDS`
- `HTTP_TIMEOUT_SECONDS`

Local development defaults to `AUTH_REQUIRED=false` through `backend/.env.example`, which lets Swagger UI call protected routes without a Supabase bearer token. In that mode, the backend uses `LOCAL_DEV_USER_ID` and `LOCAL_DEV_USER_EMAIL` as the authenticated user. Set `AUTH_REQUIRED=true` to force Supabase JWT verification locally.

If your Supabase tables enforce a foreign key to `auth.users`, set `LOCAL_DEV_USER_ID` to an existing Supabase user UUID.

Deployed environments should set:

- `ENVIRONMENT=production`
- `AUTH_REQUIRED=true`

The backend will not allow local auth bypass unless `ENVIRONMENT=local` or `ENVIRONMENT=test`.

## API Routes

- `GET /health`: public health check with request/client details visible to the backend server.
- `POST /chat/stream`: authenticated SSE chat stream.
- `GET /chat/conversations`: authenticated conversation list.
- `POST /chat/conversations`: authenticated conversation create.
- `GET /chat/conversations/{conversation_id}/messages`: authenticated message history.
- `DELETE /chat/conversations/{conversation_id}`: authenticated conversation delete.
- `GET /admin/status`: authenticated placeholder admin route.

For `POST /chat/stream`, omit `conversation_id` or set it to `null` when starting a new conversation. Swagger UI may show `"string"` as a placeholder; the backend normalizes that placeholder to `null`.

## Architecture Overview

- `app/main.py`: FastAPI app factory, lifespan, CORS, middleware, router includes.
- `app/config.py`: Pydantic Settings loaded from `.env`.
- `app/dependencies.py`: shared auth and service dependencies.
- `app/middleware/auth.py`: Supabase JWT verification with cached JWKS.
- `app/middleware/rate_limit.py`: in-memory sliding window limiter.
- `app/routers`: HTTP route modules.
- `app/services/llm`: OpenAI-compatible Groq, Gemini, OpenRouter, and provider failover.
- `app/services/supabase.py`: async `httpx` wrapper for Supabase REST.
- `app/services/conversation.py`: conversation and message CRUD.
- `app/models/schemas.py`: Pydantic request/response models.
- `app/utils/streaming.py`: SSE helpers and assistant response persistence.

## Local Auth Behavior

Protected routes use `get_current_user`. When `ENVIRONMENT=local` and `AUTH_REQUIRED=false`, requests without a bearer token are treated as the configured local development user. If a bearer token is supplied, the backend still verifies it against Supabase.

For Supabase schemas with user foreign keys, `LOCAL_DEV_USER_ID` should be set to a real auth user UUID before testing conversation writes.

Production and staging environments should set:

```text
ENVIRONMENT=production
AUTH_REQUIRED=true
```

Supabase configuration is still required for conversation and message persistence.

## Health Response

`GET /health` returns the standard API envelope with service status plus client details available to the backend server:

- request method, URL, path, query, and scheme
- connection host, port, server, and HTTP version
- request headers with sensitive values redacted
- common proxy headers such as `x-forwarded-for`

## Current Scope

Implemented now:

- Authenticated chat streaming directly to LLM providers.
- Conversation and message persistence through Supabase REST.
- Provider failover: Groq, then Gemini, then OpenRouter.

Not implemented yet:

- RAG/vector search.
- Document ingestion.
- Admin functionality beyond a protected placeholder.
