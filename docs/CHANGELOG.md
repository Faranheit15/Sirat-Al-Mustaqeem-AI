# Changelog

All notable changes to Sirat Al Mustaqeem AI will be documented in this file.

## [Unreleased]

### Added

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
