# Contributing

Thanks for contributing to Sirat Al Mustaqeem AI. This project is being rebuilt deliberately: backend first, frontend second, mobile later if needed.

## Before You Start

1. Read [docs/CONTEXT.md](docs/CONTEXT.md).
2. Read the README for the app you are changing:
   - [backend/README.md](backend/README.md)
   - [frontend/README.md](frontend/README.md)
   - [mobile/README.md](mobile/README.md)
3. Check [docs/DECISIONS.md](docs/DECISIONS.md) for existing architecture decisions.
4. Keep changes scoped to the task.

## Current Priorities

1. Finish the FastAPI backend.
2. Test backend behavior through Swagger UI.
3. Start the Next.js frontend only after backend contracts are stable.
4. Defer mobile until backend and frontend are complete.

## Local Backend Workflow

Install dependencies:

```bash
cd backend
uv sync
```

Run the backend:

```bash
uv run uvicorn app.main:app --reload
```

Run checks:

```bash
uv run ruff check .
uv run mypy app
```

Use uv or uv pip for Python dependency changes. Do not use pip directly.

## Code Style

Backend:

- Python 3.12.
- Type hints everywhere.
- Pydantic v2 models with `model_config` where needed.
- Async network I/O with httpx or async SDK clients.
- Keep route handlers thin.
- Put business logic in services.
- Put request and response schemas in `backend/app/models/schemas.py`.

Frontend planned:

- TypeScript strict mode.
- Next.js App Router.
- Tailwind CSS v4.
- shadcn/ui conventions.
- Keep backend calls behind small API helper functions.

## Documentation Expectations

Update [docs/CHANGELOG.md](docs/CHANGELOG.md) after meaningful implementation work.

Update [docs/DECISIONS.md](docs/DECISIONS.md) when making or changing architecture decisions.

Update service docs when routes, app structure, or integration patterns change:

- [docs/services/backend.md](docs/services/backend.md)
- [docs/services/frontend.md](docs/services/frontend.md)

## Secrets And Environment

- Never commit real `.env` files or production secrets.
- Keep example values in `.env.example` files.
- Backend secrets belong in `backend/.env`.
- Future frontend public env vars belong in `frontend/.env.local`.

## Architecture Guardrails

- Keep the backend and frontend independent.
- Do not reintroduce Turborepo or shared packages without documenting the decision first.
- Do not call LLM providers from the frontend.
- Do not add RAG/vector search or document ingestion until the core backend API is stable.
- Keep API responses consistent with the `{ data, error, message }` envelope unless the endpoint streams SSE.

## Pull Request Checklist

- Relevant docs updated.
- Changelog updated.
- Backend checks pass when backend code changes.
- No real secrets committed.
- New behavior is testable from Swagger UI or documented clearly.
