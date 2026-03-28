# Dependency Map

Monorepo for the Dependency Map OS MVP: **Next.js** (`frontend/`), **FastAPI** (`backend/`), and **Supabase** (SQL in `supabase/migrations`).

## Prerequisites

- Node 20+
- [uv](https://docs.astral.sh/uv/) (Python 3.11+)
- A Supabase project (Auth + Postgres)

## Environment

- `frontend/.env.example` — Supabase anon key + API URL for the dashboard.
- `backend/.env.example` — Supabase service role, JWT secret (verify user tokens), optional GitHub webhook secret.

Apply migrations in the Supabase SQL editor or via `supabase db push` when using the Supabase CLI.

## Run locally

**API**

```bash
cd backend && cp .env.example .env
uv sync --extra dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Web**

```bash
cd frontend && cp .env.example .env
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Protected routes: `/dashboard`, `/orgs/...`, `/repos/...`.

## CI

From the repo root: `npm install`, `npm run lint`, `npm run build` (web); `cd backend && uv sync --extra dev && uv run ruff check app` (API).
