# Frontend Service

The frontend will live in `frontend/`. It has not been scaffolded yet in the backend-first reset.

The current plan is to complete and test the FastAPI backend through Swagger UI first. The Next.js frontend should begin only after the backend API contracts are stable.

## Planned Stack

- Next.js 15 with App Router.
- TypeScript strict mode.
- Tailwind CSS v4.
- shadcn/ui for interface primitives.
- Supabase Auth for email and Google OAuth.
- Backend API calls to the standalone FastAPI service.

## Planned App Shape

Expected structure when frontend work begins:

```text
frontend/
|-- app/
|-- components/
|-- lib/
|-- public/
|-- package.json
`-- README.md
```

Expected route groups:

- Public landing page.
- Auth pages for login and signup.
- Chat pages for new and existing conversations.
- Admin shell after backend admin needs are real.

## Backend Integration Rules

- The frontend should never call LLM providers directly.
- All chat, conversation, auth verification, and future RAG interactions should go through the FastAPI backend.
- Browser requests should pass the Supabase access token as `Authorization: Bearer <token>`.
- Chat streaming should consume `POST /chat/stream` as `text/event-stream`.
- Conversation history should use the backend conversation endpoints rather than Supabase directly.

## Component Guidelines

When implementation begins:

- Keep Server Components as the default.
- Move Client Components as low in the tree as possible.
- Keep auth components under `components/auth`.
- Keep chat components under `components/chat`.
- Keep shadcn/ui primitives under `components/ui`.
- Keep Supabase helpers under `lib/supabase`.
- Keep backend API helpers under `lib/api` until a separate generated or shared client is justified.
- Build the actual chat experience first; avoid a marketing-heavy landing page.

## Current Status

- `frontend/` exists as a placeholder directory.
- No frontend dependencies or source files have been scaffolded yet.
- Frontend work is intentionally paused until the backend is complete.
