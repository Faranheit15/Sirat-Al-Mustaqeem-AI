# Backend Service

The backend lives in `apps/api` and uses FastAPI, Python 3.12, async SQLAlchemy 2.0, Pydantic v2, uvicorn, uv, Supabase, PyJWT, httpx, and multi-provider LLM clients.

## Conventions

- Keep route modules under `app/routers`.
- Register routers in `app/main.py`.
- Keep application setup in `app/main.py`.
- Keep environment parsing in `app/config.py` using Pydantic settings.
- Keep shared FastAPI dependencies in `app/dependencies.py`.
- Prefer async SQLAlchemy sessions for database I/O.
- Define explicit Pydantic response models for public routes.
- Keep request/response schemas in `app/models/schemas.py`.
- Keep provider integrations and persistence logic in `app/services`.

## Middleware

- Configure CORS in `create_app`.
- `AuthContextMiddleware` reads bearer tokens, verifies Supabase JWTs with cached JWKS, and attaches `request.state.user` when valid.
- `RateLimitMiddleware` applies a sliding-window in-memory limit to `/chat` and `/conversations`.
- The default rate limit is 20 requests per minute per user, with unauthenticated requests falling back to client IP.
- Keep middleware small and avoid database calls unless unavoidable.

## Route Structure

```text
app/routers/health.py
app/routers/chat.py
app/routers/auth.py
```

Routes should validate inputs with Pydantic models, delegate business logic to service modules, and return typed response models.

## Routes

- `GET /health`: returns service health.
- `POST /chat`: authenticated SSE endpoint for chat completion streaming.
- `GET /conversations`: authenticated conversation list endpoint.
- `POST /conversations`: authenticated conversation creation endpoint.
- `DELETE /conversations/{conversation_id}`: authenticated conversation deletion endpoint.
- `POST /auth/callback`: authenticated Supabase webhook/callback handler for profile upsert.

## LLM Routing

`app/services/llm_router.py` defines an `LLMProvider` protocol and concrete providers:

- Groq through the OpenAI SDK with `https://api.groq.com/openai/v1`.
- Gemini through `google-generativeai`.
- OpenRouter through the OpenAI SDK with `https://openrouter.ai/api/v1`.

`ProviderRouter` tries providers in order: Groq, then Gemini, then OpenRouter. It catches provider unavailability and rate-limit errors, records remaining rate-limit headers when exposed by OpenAI-compatible providers, and falls back to the next provider.

## Persistence

`app/services/conversation.py` coordinates conversation CRUD and message persistence. `app/services/supabase.py` wraps `supabase-py` behind async methods by running the sync SDK calls in worker threads.

Expected Supabase tables for the current scaffold:

- `profiles`
- `conversations`
- `messages`
