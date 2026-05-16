# Decisions

## Initial Platform Decisions

- Use Turborepo for the monorepo so the web app, API service, and shared TypeScript packages can evolve together with cached task orchestration.
- Use Bun as the JavaScript package manager and command runner.
- Use Supabase Auth for authentication because it pairs well with hosted Postgres and supports web and future mobile clients.
- Use Groq as the primary LLM provider for fast inference.
- Use FastAPI for the backend to keep the AI, retrieval, auth integration, and database boundaries explicit.
- Use Next.js 15 App Router for the web app.
- Use TypeScript strict mode across all TypeScript apps and packages.
