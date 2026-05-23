# Backend Service

The backend lives in `backend/` and is the first active implementation target for Sirat Al Mustaqeem AI. It is a standalone FastAPI service using Python 3.12, uv, Pydantic v2, async httpx, Supabase Auth/REST, and multi-provider LLM routing.

## Current Scope

Implemented:

- FastAPI app scaffold with CORS, lifespan, routers, dependencies, and middleware.
- Public health check.
- Supabase JWT verification using PyJWT and cached JWKS.
- Local-development auth bypass for Swagger UI testing.
- In-memory sliding-window rate limiting for chat routes.
- Conversation and message CRUD through Supabase REST.
- SSE chat streaming directly to the configured LLM providers.
- LLM provider failover: Groq, then Gemini, then OpenRouter.
- Dockerfile for the backend service.
- Swagger UI testing through FastAPI docs.

Not implemented yet:

- RAG/vector search.
- Document ingestion.
- Islamic source retrieval pipeline.
- Real admin functionality beyond a protected placeholder.

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
- `GET /chat/conversations`: authenticated conversation list.
- `POST /chat/conversations`: authenticated conversation create.
- `GET /chat/conversations/{conversation_id}/messages`: authenticated message history.
- `DELETE /chat/conversations/{conversation_id}`: authenticated conversation delete.
- `GET /admin/status`: authenticated placeholder admin status route.

## Auth

`backend/app/middleware/auth.py` verifies Supabase access tokens using the Supabase JWKS endpoint. JWKS responses are cached for one hour by default and both RSA (`RS256`) and elliptic-curve (`ES256`) keys are supported.

Authenticated routes should use `get_current_user` from `backend/app/dependencies.py`. The dependency returns a typed user object derived from JWT claims.

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

`backend/app/middleware/rate_limit.py` applies an in-memory sliding-window limiter to chat routes. The default limit is configured by `RATE_LIMIT_REQUESTS_PER_MINUTE`.

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
