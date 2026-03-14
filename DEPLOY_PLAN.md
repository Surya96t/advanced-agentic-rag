# Deployment Plan

## Branch Strategy

| Branch | Purpose |
|---|---|
| `deploy/pre-deploy-hardening` | All tasks that must be complete before the app goes live |
| `cicd/pipeline-improvements` | Code quality, cleanup, and monitoring tasks — automate in CI/CD or do post-deploy |

---

## Bucket 1 — Pre-Deploy Hardening (`deploy/pre-deploy-hardening`)

These tasks block a safe first deploy. The app won't be secure, configurable, or containerizable without them.

### [BLOCKER] `86ag60qa9` — Set `debug=False` as default in `config.py`
- **File:** `backend/app/core/config.py`
- **Problem:** `debug=True` is the current default. In production this exposes full Python stack traces in HTTP error responses — a significant information leak.
- **Fix:** Change `debug` field default to `False`. Dev environments set `DEBUG=true` via their `.env`.

---

### [SECURITY] `86ag60qbg` — Replace `REVALIDATE_SECRET` with a high-entropy random value
- **File:** `frontend/` (Next.js revalidation route)
- **Problem:** The `REVALIDATE_SECRET` is a hardcoded weak/placeholder value. Anyone who knows it can trigger on-demand ISR revalidation.
- **Fix:** Generate a proper secret (e.g. `openssl rand -hex 32`) and document it in `.env.example`. The value itself goes in the deployment environment, never in the repo.

---

### [CONFIG] `86ag60q9p` — Update `backend/.env.example` with all required variables
- **File:** `backend/.env.example`
- **Problem:** The example file is missing several variables added in recent features (Redis, LangSmith, rate limiting, Clerk, storage).
- **Fix:** Audit every `settings.*` reference in `config.py` and ensure each has a corresponding entry in `.env.example` with a description.

---

### [CONFIG] `86ag60qb8` — Add `frontend/.env.example`
- **File:** `frontend/.env.example` (does not exist yet)
- **Problem:** No template exists for frontend env vars. Any new dev or deployment environment has to reverse-engineer what's needed.
- **Fix:** Create `frontend/.env.example` covering Clerk publishable key, backend API URL, and revalidation secret.

---

### [SECURITY] `86ag60qec` — Restrict CORS `allow_methods` / `allow_headers`
- **File:** `backend/app/main.py`
- **Problem:** CORS is likely configured with `allow_methods=["*"]` and `allow_headers=["*"]`. This is overly permissive for a production API.
- **Fix:** Restrict to only the methods and headers the frontend actually uses (`GET`, `POST`, `DELETE` and `Content-Type`, `Authorization`).

---

### [CLEANUP] `86ag60qah` — Remove `__test-components.tsx` from production component directory
- **File:** `frontend/components/__test-components.tsx` (or similar path)
- **Problem:** A test/debug component file is sitting inside the production component tree. It will be included in the production build unnecessarily.
- **Fix:** Delete the file.

---

### [CLEANUP] `86ag60tag` — Remove debug scripts from repository root
- **Problem:** Scripts used during development/debugging sitting at the repo root will end up inside the Docker image.
- **Fix:** Delete or move them to a `scripts/dev/` folder and exclude from `.dockerignore`.

---

### [DEPLOY] `86ag60taj` — Add Dockerfile for FastAPI app
- **Files:** `backend/Dockerfile`, `backend/.dockerignore` ✅
- **Problem:** No Dockerfile existed. Can't containerize or deploy to any cloud provider.
- **Fix:** Multi-stage Dockerfile for the FastAPI app using `uv`. `.dockerignore` excludes `.env`, `.venv`, `tests/`, `scripts/`.
- **Note:** `Dockerfile.worker` (Celery) is deferred to Bucket 2 alongside `86aftvjpz` — no point containerizing a worker that isn't wired up yet.

---

### [DEPLOY] Supabase migration tracking (replaces Alembic — `86ag60tap`)
- **Files:** `supabase/migrations/` folder (does not exist in repo)
- **Problem:** 7 migrations exist in Supabase cloud but none are tracked in the repo. There's no way to audit schema history or apply changes to a fresh environment.
- **Fix:** 
  1. Create `supabase/migrations/` in the repo
  2. Commit the 7 existing migration SQL files (pulled from Supabase cloud)
  3. Document: all future schema changes go through a `.sql` file in this folder → reviewed in PR → applied via `mcp_supabase_apply_migration` in CI/CD
- **Note:** Uses Supabase's native migration system — Alembic is NOT used (Alembic is for SQLAlchemy ORM which this project does not use).

---

## Bucket 2 — CI/CD Pipeline / Post-Deploy (`cicd/pipeline-improvements`)

These can be automated as lint/test rules in the CI pipeline or addressed after the first deploy.

### `86ag60qbp` — Add Redis health check to `/health` endpoint
- Add a Redis ping to the existing `/health` endpoint so infrastructure monitoring can detect Redis outages.

### `86ag60qb1` — Add error monitoring (Sentry or equivalent)
- Integrate Sentry SDK in both FastAPI and Next.js. Wire DSN via environment variable.

### `86ag60qap` — Replace `print()` statements with `logger` calls in backend
- Add a `ruff` or `pylint` rule to CI that flags `print()` usage in `backend/app/`.

### `86ag60qe7` — Remove or gate `console.log` in frontend production code
- Add an ESLint rule (`no-console`) to `eslint.config.mjs` so CI fails on unguarded console statements.

### `86ag60qe9` — Migrate Pydantic V1-style `class Config` to V2 `model_config`
- Non-breaking refactor. Run as a `ruff` check in CI.

### `86ag60qe8` — Remove or implement empty `health.py` in `api/v1/`
- Either delete the file or move the `/health` endpoint there from `main.py`.

### `86ag60qeb` — Fix or remove permanently-skipped RLS enforcement test
- Re-enable the test with a proper mock, or delete it if it duplicates other coverage.

### `86ag60qea` — Remove stale Phase 5/6 TODO comments claiming auth is not implemented
- Simple grep-and-delete pass. Can be a CI lint rule.

### `86ag60qed` — Fix README inaccuracies
- Wrong install command, Next.js version, clone URL.

---

### Fix `.gitignore` `.env*` pattern to allow `.env.example` files
- **File:** `frontend/.gitignore`
- **Problem:** The pattern `.env*` matches `.env.example`, so the template file can't be committed without `git add -f`. Any future contributor doing `git add .` will silently miss it.
- **Fix:** Add a negation exception after the `.env*` line:
  ```
  .env*
  !.env.example
  ```
  Check `backend/.gitignore` for the same issue and apply the same fix if needed.

### `86ag60tak` — Document Celery worker scaling configuration
- Add scaling notes to the deployment docs or README.

### `86aftvjpz` + `86ag60taj` (worker) — Celery background processing + Dockerfile.worker
- Wire the Celery task (`background.py`) into the ingest endpoint (currently runs synchronously).
- Once wired, add `backend/Dockerfile.worker` and update `docker-compose.yml` with the worker service.
- These two are bundled: no point containerizing a worker that isn't functional.
