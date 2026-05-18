# OnePilot AI — Frontend

A production-grade SaaS UI for OnePilot AI, the AI operations workspace for
small businesses. Built with Next.js 16 (App Router), TypeScript, Tailwind v4,
shadcn-style components, lucide icons, TanStack Query, react-hook-form, and
Zod.

## Quick start

```bash
pnpm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL to the FastAPI URL
pnpm dev                            # http://localhost:3000
```

The backend FastAPI server must be running at `NEXT_PUBLIC_API_URL` (default
`http://localhost:8000`). Spin it up from the repo root with
`uvicorn onepilot.api.main:app --reload` (see `backend/README.md`).

## Scripts

| Script           | Purpose                                  |
|------------------|------------------------------------------|
| `pnpm dev`       | Local dev server with Turbopack          |
| `pnpm build`     | Production build                         |
| `pnpm start`     | Run the production build                 |
| `pnpm lint`      | ESLint (Next + React rules)              |
| `pnpm typecheck` | `tsc --noEmit` strict type check         |
| `pnpm test`      | Vitest unit/component tests              |
| `pnpm test:watch`| Vitest in watch mode                     |

## Architecture

```
src/
├── app/
│   ├── (public)/        # Login, register, marketing pane
│   ├── (app)/           # Authenticated app: dashboard, workspace, ...
│   ├── layout.tsx       # Wraps everything in Providers (Query, Auth, Toaster)
│   └── globals.css      # Tailwind v4 + theme tokens
├── components/
│   ├── ui/              # Reusable primitives: Button, Card, Modal, ...
│   └── domain/          # OnePilot-specific badges, panels, cards
├── lib/
│   ├── api-client.ts    # Central fetch wrapper, typed verbs, file uploads
│   ├── auth.tsx         # AuthProvider context, token + /me handling
│   ├── providers.tsx    # QueryClient + AuthProvider + sonner Toaster
│   ├── queries.ts       # Typed TanStack Query hooks for every endpoint
│   └── utils.ts         # cn(), formatters, etc.
├── test-utils/          # Render helpers, fetch mock, Next.js navigation mocks
└── types/api.ts         # TypeScript mirrors of every backend response
```

## Pages

- `/login` and `/register` — JWT auth via existing FastAPI endpoints.
- `/dashboard` — Metric cards, recent conversations, provider mode, quota
  progress, and quick actions.
- `/workspace` — Three-column AI Workspace: conversations sidebar, chat with
  user/assistant bubbles, intent + confidence badges, optimistic messages,
  approval banners, and a details panel with citations and tool trace.
- `/knowledge` — Upload documents, list with status, document detail modal,
  and a grounded-answer form using `POST /knowledge/answer`.
- `/leads` — Filterable table (status, urgency), row click opens a detail
  drawer with intent / pain point / next action, plus a "New lead" modal.
- `/approvals` — Pending-approval inbox with filters, JSON payload preview,
  risk badge, and Approve / Reject / Needs more info actions (admin-only).
- `/memory` — Persistent agent memory with scope badges (user, organization,
  agent), create form with optional TTL, and delete.
- `/usage` — Quota progress, cost / token / latency aggregates, feature and
  provider breakdowns. Admin-only audit log and usage event tables (members
  see an "admin access required" notice).
- `/settings` — Organization, role, plan with limits, provider status, and
  security notes.

## Design

- Dark sidebar with org name, plan badge, navigation, pending-approvals
  count, and sign out. Topbar shows provider mode (live vs deterministic
  fallback) and a user menu.
- Restrained palette (slate + indigo accent), rounded cards with subtle
  borders, and consistent spacing.
- Every async surface implements **loading skeleton → data → empty state →
  error state with retry**.
- AI transparency is surfaced through intent and confidence badges,
  citation cards, tool trace panels, weak-evidence warnings, and approval
  banners.

## Backend contract

All HTTP calls go through `lib/api-client.ts`. The client:

- Reads the JWT from `localStorage` and adds it to `Authorization`.
- Returns parsed JSON typed against `types/api.ts`.
- Throws `ApiRequestError(status, error, message)` for non-2xx responses.

TanStack Query hooks (`lib/queries.ts`) wrap each endpoint with cache keys
and invalidations so that, for example, sending a chat message refreshes
the conversation list, the active conversation, the usage summary, and the
approvals badge.

## Testing

`pnpm test` runs Vitest in jsdom mode and exercises:

- `LoginPage` renders the form and validates required fields.
- `DashboardPage` renders metric cards and the provider mode card against
  mocked `/health`, `/conversations`, `/documents`, `/leads`, `/approvals`,
  and `/usage/summary` responses.
- `WorkspacePage` submits a message against a mocked `/chat` and shows the
  optimistic user bubble plus assistant citation.
- `ApprovalsPage` renders the inbox with the high-risk badge for a pending
  approval (with mocked `/me` and `/approvals`).
- `LeadsPage` renders the table with status and urgency badges.

Tests use the helpers in `src/test-utils/` to mock `fetch`, the Next.js
navigation hooks, and `next/link`.
