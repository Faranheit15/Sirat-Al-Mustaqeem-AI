# Sirat Al Mustaqeem AI

Sirat Al Mustaqeem AI is an Islamic knowledge chatbot designed to answer questions with structured, citation-backed responses from the Quran, authentic Hadith, and recognized scholarly works.

The project is currently being rebuilt with a backend-first approach. The FastAPI backend will be completed and tested through Swagger UI before the Next.js frontend is scaffolded. Mobile is deferred until the backend and frontend are stable.

## Project Status

- Backend: scaffolded and active.
- Frontend: placeholder only.
- Mobile: Phase 3 placeholder.
- RAG/vector search: planned, not implemented.
- Document ingestion: planned, not implemented.

## Tech Stack

Backend:

- FastAPI
- Python 3.12
- uv for dependency management
- Pydantic v2 and pydantic-settings
- httpx for async HTTP
- PyJWT and cryptography for Supabase JWT verification
- Supabase Auth and Supabase REST
- OpenAI SDK for OpenAI-compatible LLM providers
- Groq as primary LLM provider
- Gemini as fallback LLM provider
- OpenRouter as tertiary LLM provider

Frontend planned:

- Next.js 15 with App Router
- TypeScript strict mode
- Tailwind CSS v4
- shadcn/ui
- Supabase Auth
- Bun for package management

Infrastructure direction:

- Docker Compose for local multi-service orchestration
- FastAPI Cloud or equivalent backend hosting
- Vercel for frontend hosting
- Supabase PostgreSQL with pgvector for future RAG

## Repository Layout

```text
backend/    FastAPI backend service
frontend/   Future Next.js frontend
mobile/     Future mobile app, optional
docs/       Project context, decisions, changelog, and service docs
```

Important docs:

- [Project context](docs/CONTEXT.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Changelog](docs/CHANGELOG.md)
- [Backend service docs](docs/services/backend.md)
- [Frontend service docs](docs/services/frontend.md)
- [Backend README](backend/README.md)

## Backend Quick Start

Install dependencies:

```bash
cd backend
uv sync
```

Create local environment:

```bash
cp .env.example .env
```

Run the API:

```bash
uv run uvicorn app.main:app --reload
```

Open Swagger UI:

```text
http://localhost:8000/docs
```

Health check:

```text
GET http://localhost:8000/health
```

## Backend API

Current routes:

- `GET /health`
- `POST /chat/stream`
- `GET /chat/conversations`
- `POST /chat/conversations`
- `GET /chat/conversations/{conversation_id}/messages`
- `DELETE /chat/conversations/{conversation_id}`
- `GET /admin/status`

Protected routes require a Supabase access token:

```text
Authorization: Bearer <token>
```

For local Swagger UI testing, the backend can run with `AUTH_REQUIRED=false`, which uses a configured local development user when no bearer token is supplied.

Non-streaming JSON routes use this response envelope:

```json
{
  "data": null,
  "error": null,
  "message": null
}
```

Chat streaming uses Server-Sent Events from `POST /chat/stream`.

## Environment

Backend environment variables live in `backend/.env`. Start from `backend/.env.example`.

Required for authenticated backend routes:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_AUDIENCE`

LLM configuration:

- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`

Never commit real secrets.

## Development Principles

- Complete and verify the backend before starting the frontend.
- Keep frontend and backend as independent apps.
- Do not reintroduce Turborepo unless there is a clear, documented reason.
- Keep LLM calls on the backend only.
- Keep future RAG and ingestion work out of the codebase until the core API is stable.
- Update docs when implementation changes.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
