# Shared Packages

Shared TypeScript packages live in `packages`.

## Packages

- `packages/shared-types`: API and domain contracts shared by the web app and API client.
- `packages/api-client`: Typed fetch wrappers for API routes.
- `packages/ui`: Placeholder for shared UI components.
- `packages/config`: Shared ESLint, Prettier, TypeScript, and Tailwind/PostCSS config.

## Conventions

- Keep packages app-agnostic unless the package name says otherwise.
- Export from `src/index.ts` and publish compiled output from `dist`.
- Avoid importing from apps inside packages.
- Treat `packages/shared-types` as the source of truth for frontend API contracts until backend OpenAPI generation is added.
- Keep TypeScript strict mode enabled in every package.
