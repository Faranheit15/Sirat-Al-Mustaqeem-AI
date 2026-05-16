# Changelog

All notable changes to Sirat Al Mustaqeem AI will be documented in this file.

## [Unreleased]

### Added

- FastAPI backend structure with `config`, `dependencies`, middleware, routers, services, models, and SSE utilities.
- Supabase JWT verification with JWKS caching and authenticated user dependency.
- In-memory sliding-window rate limiter for chat and conversation routes.
- Multi-provider LLM router with Groq, Gemini, and OpenRouter failover.
- Supabase conversation/profile service wrappers and chat SSE persistence flow.
- Backend route documentation and environment placeholders.
- Next.js App Router web structure for landing, auth, chat, and admin shell routes.
- Supabase SSR auth clients, protected chat middleware, and provider setup.
- Zustand chat store with SSE streaming client for the FastAPI backend.
- Chat components for message thread, markdown/RTL message bubbles, input, sidebar, and streaming indicator.
- shadcn-style UI primitives for button, input, textarea, card, avatar, scroll area, separator, dropdown menu, dialog, and toast.
- Dark mode support through `next-themes`.
- Shared Supabase-aligned `User`, `Message`, `Conversation`, chat, and LLM provider TypeScript types.
- Typed `@sirat/api-client` functions for chat SSE streaming and conversation list/create/delete.
- FastAPI conversation create and delete routes backed by Supabase.

### Changed

- Replaced the initial versioned API scaffold with the requested `app/routers` backend structure.
- Updated the TypeScript API client route paths to match the backend routes.
- Updated web service documentation with actual route structure and chat/auth architecture.
- Replaced the web app's raw chat fetch helper with the shared `@sirat/api-client` package.
- Updated API package scripts to use a workspace-local uv cache for sandbox-friendly verification.

### Fixed

- Avoided uv global cache permission failures during monorepo lint, typecheck, and build.
- Fixed Supabase JWT verification for ES256 elliptic-curve JWKS keys so authenticated API requests do not fail with RSA-only key parsing.
- Fixed SSE parsing for CRLF-framed event streams so streamed assistant tokens render in the chat window.
- Fixed message persistence for Supabase schemas where `messages` does not include a `user_id` column.
- Added saved conversation message loading so selecting a sidebar conversation hydrates the chat window.
- Added the Sirat Al Mustaqeem AI Islamic research assistant system prompt to every LLM request.
