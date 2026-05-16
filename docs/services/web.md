# Web Service

The web app lives in `apps/web` and uses Next.js 15, App Router, TypeScript strict mode, Tailwind CSS v4, and shadcn/ui conventions.

## Conventions

- Use App Router files under `src/app`.
- Keep shared utilities under `src/lib`.
- Use route groups as features grow instead of flattening unrelated pages together.
- Keep Server Components as the default and move Client Components as low in the tree as possible.
- Use `@sirat/api-client` for backend calls instead of ad hoc fetch wrappers.
- Use shadcn/ui conventions for component organization and Tailwind CSS variables.
- Use `@supabase/ssr` for Supabase server clients, browser clients, and middleware session refresh.
- Use Zustand for local chat state.
- Use `next-themes` with Tailwind `dark:` classes for theme support.
- Use `react-markdown` with `rehype-raw` for assistant message rendering.

## Page Structure

```text
src/app/layout.tsx
src/app/page.tsx
src/app/(auth)/
src/app/(chat)/
src/app/(admin)/
```

Current public routes:

- `/`: minimal landing page with hero and CTA.
- `/login`: email magic-link and Google OAuth login.
- `/signup`: email/password signup.
- `/chat`: new chat screen.
- `/chat/[id]`: existing conversation screen shell.

Note: chat routes live under `src/app/(chat)/chat` so the URL is `/chat`. A route group page directly at `src/app/(chat)/page.tsx` would conflict with the landing page at `/`.

## Component Patterns

- Keep route-specific components near their route.
- Move reusable interface primitives into `packages/ui` when they are shared across apps.
- Use `src/lib/utils.ts` for `cn` and other lightweight frontend utilities.
- Keep environment access centralized and validated before adding production integrations.
- Keep auth forms in `src/components/auth`.
- Keep chat experience components in `src/components/chat`.
- Keep shadcn-owned primitives in `src/components/ui`.
- Keep Supabase helpers in `src/lib/supabase`.

## Auth And Middleware

`src/middleware.ts` calls the Supabase middleware client and protects `/chat/:path*`. Unauthenticated users are redirected to `/login?next=/chat...`.

Root layout wraps the app with `AppProviders`, which provides the browser Supabase client, `next-themes`, and toast rendering.

## Chat Flow

- `ConversationSidebar` loads `GET /conversations` from the FastAPI backend.
- `ChatInput` uses `@sirat/api-client` to post to `POST /chat` with the Supabase bearer token.
- SSE is read with `ReadableStream` and `TextDecoder`.
- `MessageThread` renders the scrollable transcript.
- `MessageBubble` renders markdown, RTL text, and optional citations.
- `useChatStore` tracks active conversation, messages, streaming state, and conversation summaries.
- `src/lib/chat-api.ts` only adapts Supabase session access to `@sirat/api-client`; it should not own raw backend fetch logic.
