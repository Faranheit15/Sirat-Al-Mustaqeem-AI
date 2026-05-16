# Sirat Al Mustaqeem AI Context

Sirat Al Mustaqeem AI is an Islamic AI chatbot focused on careful, referenced guidance. The product should help users ask questions and receive clear answers grounded in Islamic sources, while making boundaries explicit when a qualified scholar or local authority is needed.

## Product Direction

- Build a conversational Islamic assistant that can cite Qur'an, hadith, and trusted scholarly material.
- Prioritize accuracy, humility, source transparency, and user safety over answer speed or breadth.
- Keep religious guidance reviewable and avoid pretending model output is a fatwa.

## Tech Stack

- Monorepo: Turborepo with Bun workspaces.
- Web: Next.js 15, App Router, TypeScript strict mode, Tailwind CSS v4, shadcn/ui conventions.
- API: FastAPI on Python 3.12, async SQLAlchemy 2.0, Pydantic v2, uvicorn, uv package management.
- Auth decision: Supabase Auth.
- Primary LLM decision: Groq.
- Shared packages: TypeScript types, typed API client, shared UI, and shared config packages.
- Integration state: the web app uses `@sirat/api-client` for authenticated FastAPI calls and SSE chat streaming. The API persists conversations and messages through Supabase.

## Repository Structure

```text
apps/
  web/       Next.js App Router application.
  api/       FastAPI backend service.
  mobile/    Phase 3 placeholder.
packages/
  api-client/     Typed TypeScript fetch client for backend routes.
  config/         Shared TypeScript, ESLint, Prettier, and Tailwind/PostCSS config.
  shared-types/   Shared TypeScript contracts.
  ui/             Shared UI package placeholder.
docs/
  services/       Service-specific engineering conventions.
```

## Local Workflow

- Install JavaScript dependencies with `bun install`.
- Run all development tasks with `bun run dev`.
- Run the web app with `bun run dev:web`.
- Run the API with `bun run dev:api` after `uv sync` has been run in `apps/api`.
- Run repository checks with `bun run lint`, `bun run typecheck`, and `bun run build`.
- The API package scripts use a workspace-local uv cache at `apps/api/.uv-cache` to avoid relying on user-level cache permissions.

## Engineering Principles

- TypeScript strict mode is required for every TypeScript package.
- Python code should remain typed and async-first where I/O is involved.
- Shared contracts live in `packages/shared-types`; frontend fetch logic lives in `packages/api-client`.
- `packages/api-client` owns the typed API surface for health, chat streaming, conversation list/create/delete, and authenticated request headers.
- Keep generated secrets and real environment values out of git. Use `.env.example` only for placeholders.
