# Sirat Al Mustaqeem AI

An Islamic knowledge chatbot that answers queries with structured, citation-backed
responses referencing the Quran, Hadith, and scholarly works.

## Tech stack
- **Backend:** FastAPI (Python 3.12), async, uv for package management
- **Frontend:** Next.js 15 (App Router), Tailwind CSS v4, shadcn/ui, Bun
- **Database:** Supabase (PostgreSQL + pgvector + Auth)
- **LLM providers:** Groq (primary), Gemini (fallback), OpenRouter (tertiary)
- **Hosting:** FastAPI Cloud (backend), Vercel (frontend)
- **Auth:** Supabase Auth (email + Google OAuth)

## Architecture
- Backend and frontend are independent apps in the same repo
- Backend exposes a REST + SSE API, frontend consumes it
- All LLM calls go through the backend (never from frontend)
- Vector search (RAG) will run in backend via Supabase pgvector later
- Auth: Frontend handles login via Supabase client SDK,
  backend verifies Supabase JWTs on protected endpoints
- Backend development comes first and is tested through Swagger UI before frontend work begins
- Docker Compose will be used to run independent services together once more services are implemented

## Current state
- [x] Backend: scaffolded with FastAPI, Supabase auth, rate limiting, LLM failover, chat SSE, and conversation persistence
- [ ] Frontend: not started
- [ ] Mobile: not planned yet

## Conventions
- Python: snake_case, type hints everywhere, Pydantic v2 models
- TypeScript: camelCase, strict mode, Zod for validation
- API responses: { data, error, message } envelope pattern
- Local backend env uses `ENVIRONMENT=local`; deployed backend env should use `ENVIRONMENT=production`
- All env vars in .env (backend) and .env.local (frontend), never committed
