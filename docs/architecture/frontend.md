# Frontend

The frontend is in `apps/web`, using Next.js, React and TypeScript.

## Folder layout

```
apps/web/src/
  app/          Routes only. Each page is a thin file that shows a feature
  features/     One folder per screen: overview, documents, analytics, assistant, settings
  components/   Shared parts, such as the sidebar
  lib/          Shared helpers
  styles/       tokens.css: the only file with raw colours
```

## Rules

- **Features do not import each other.** Shared code moves to `components/` or `lib/`. ESLint enforces this.
- **No raw colours.** Use Tailwind names from the tokens, such as `bg-surface` or `text-muted`. Built-in colours like `bg-green-500` are blocked too.
- **No hardcoded URLs.** The browser calls `/api/...` on its own web address.
- **Every screen has empty, loading and error states.**

## Design tokens

`src/styles/tokens.css` holds the colours sampled from the design image. `src/app/globals.css` connects them to Tailwind. To add a colour:

1. Add `--token-name` to `tokens.css`.
2. Add `--color-name: var(--token-name)` to `globals.css`.
3. Use it as `bg-name` or `text-name`.

## Talking to the backend

- The browser calls `/api/...`. Next.js forwards it during development, and Caddy in production.
- From Phase 2, TypeScript types are generated from the API, so frontend and backend cannot drift apart.
- TanStack Query will handle data loading and caching.
- `next.config.ts` reads `API_INTERNAL_URL` when the app is built.
