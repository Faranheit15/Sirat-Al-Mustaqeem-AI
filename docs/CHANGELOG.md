# Changelog

All notable changes to Sirat Al Mustaqeem AI will be documented in this file.

## [Unreleased]

### Added

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

### Changed

- Restarted the project direction from a Turborepo monorepo to independent `backend/`, `frontend/`, and `mobile/` folders.
- Updated backend documentation to match the new standalone FastAPI architecture.
- Updated service docs to describe the backend-first standalone app direction instead of the old monorepo packages.
- Updated agent guide files to reference app READMEs for `backend/`, `frontend/`, and `mobile/`.
- Renamed frontend service documentation from `web.md` to `frontend.md`.
- Updated backend docs for local auth behavior and detailed health responses.
- Replaced the deprecated `google-generativeai` Gemini transport with the OpenAI-compatible Gemini endpoint through the OpenAI SDK.

### Removed

- Old `apps/` monorepo implementation after the backend-first reset.
- Turborepo/package workspace files from the previous scaffold.
- Obsolete shared package service documentation.

### Verified

- `uv sync --cache-dir .uv-cache`
- `uv run --cache-dir .uv-cache ruff check .`
- `uv run --cache-dir .uv-cache mypy app`
- FastAPI import and route registration smoke check.
