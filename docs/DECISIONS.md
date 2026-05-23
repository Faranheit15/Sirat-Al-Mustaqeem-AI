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

## Initial Platform Decisions (deprecated, ignore)

- Use Turborepo for the monorepo so the web app, API service, and shared TypeScript packages can evolve together with cached task orchestration.
- Use Bun as the JavaScript package manager and command runner.
- Use Supabase Auth for authentication because it pairs well with hosted Postgres and supports web and future mobile clients.
- Use Groq as the primary LLM provider for fast inference.
- Use FastAPI for the backend to keep the AI, retrieval, auth integration, and database boundaries explicit.
- Use Next.js 15 App Router for the web app.
- Use TypeScript strict mode across all TypeScript apps and packages.
