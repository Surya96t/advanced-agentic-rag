# GitHub Copilot Instructions for Advanced RAG System

## Project Overview

Production-grade RAG system for intelligent document retrieval and question answering.

**Tech Stack:**
- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind CSS, Clerk Auth
- **Backend:** FastAPI (Python 3.12), LangGraph, LangChain, Supabase (PostgreSQL + pgvector)
- **AI/ML:** OpenAI gpt-4o-mini (LLM + embeddings), FlashRank (re-ranking)
- **Package managers:** `uv` (backend), `pnpm` (frontend)

---

## Commands

### Backend (`cd backend` first)
```bash
uv run uvicorn app.main:app --reload      # dev server
uv run ruff check app/                    # lint
uv run ruff format app/                   # format (run before committing)
uv run ruff format --check app/           # format check (what CI runs)
uv run pytest tests/                      # all tests
uv run pytest tests/test_retrieval_integration.py  # single file
uv run mypy app/                          # type check
uv run scripts/ingest_test_data.py        # ingest sample docs
```

### Frontend (`cd frontend` first)
```bash
pnpm dev        # dev server
pnpm lint       # ESLint
pnpm build      # production build (requires Clerk env vars)
```

### Pre-commit (installed in backend venv)
```bash
# Hook runs automatically on git commit — blocks commits with ruff failures
# To run manually:
cd backend && uv run pre-commit run --all-files
```

---

## Architecture

### Agent Graph (LangGraph, `backend/app/agents/`)
Node pipeline: `context_loader → classifier → [simple_answer | router → query_rewriter → query_expander → retriever → generator → validator]`

Key state fields in `AgentState` (`state.py`):
- `original_query` — never modified after set
- `retrieval_query` — format-stripped version for search (set by router)
- `expanded_queries` — decomposed sub-queries (set by query_expander)
- `retrieved_chunks`, `sources`, `citation_map`, `generated_response`

**Critical:** `create_initial_state()` must explicitly set ALL fields to reset values. LangGraph's PostgreSQL checkpointer merges new state onto the persisted checkpoint — unset fields survive from the previous turn.

### Hybrid Search (`backend/app/retrieval/`)
- Vector search (OpenAI embeddings, 1536d) + Text search (pgFTS) run in parallel
- Combined via RRF (k=60) with configurable alpha (0.7 = favour semantic)
- `SearchConfig` has separate `top_k` (vector) and `text_top_k` (text) fields
- Re-ranked with FlashRank via `FlashRankReranker` singleton (pre-warmed at startup)
- All searches filtered by `user_id` via Supabase RLS — never bypass this

### Key Config (`backend/app/core/config.py` → `settings`)
| Setting | Default | Notes |
|---|---|---|
| `rerank_model` | `ms-marco-TinyBERT-L-2-v2` | 4MB, Railway-safe. To upgrade: `ms-marco-MiniLM-L-12-v2` (33MB) on Pro tier |
| `vector_search_top_k` | `10` | Candidate pool for vector search |
| `text_search_top_k` | `10` | Candidate pool for text search |
| `rerank_top_k` | `5` | Final results after re-ranking |
| `cors_origins` | — | Railway: use plain comma-separated string, NOT JSON array |

All settings are overridable via env vars.

---

## Coding Rules

### Workflow
- ✅ **Implement changes directly** — don't just suggest; use tools to read code, then edit
- ✅ **Present options** when multiple approaches exist
- ❌ **Do NOT create documentation files** (README, docs, plans) unless explicitly asked

### Code Style
- Python: type hints everywhere, `mypy --strict` must pass
- TypeScript: strict mode, ❌ never use `any` — use `unknown` or generics
- Line length: 100 (ruff enforced)
- ❌ Never use `print()` in backend — use `logger = get_logger(__name__)`

### Project Conventions
- All DB ops must respect RLS (`user_id = auth.uid()`)
- All API endpoints validate JWT tokens
- Chunking strategies store metadata in `document_chunks.metadata` (JSONB)
- All vector searches use hybrid approach (dense + sparse)
- All LLM calls traced with LangSmith

---

## Common Pitfalls

### FlashRank model names (flashrank==0.2.10)
Valid names: `ms-marco-TinyBERT-L-2-v2`, `ms-marco-MiniLM-L-12-v2`, `rank-T5-flan`, `ms-marco-MultiBERT-L-12`, `ce-esci-MiniLM-L12-v2`, `rank_zephyr_7b_v1_full`
❌ `ms-marco-MiniLM-L-6-v2` does NOT exist — HuggingFace cross-encoder/ms-marco-MiniLM-L6-v2 is raw Sentence Transformers, incompatible with FlashRank

### CORS on Railway
`CORS_ORIGINS` env var must be comma-separated plain string: `http://localhost:3000,https://example.vercel.app`
❌ Not JSON array `["http://..."]` — pydantic-settings 2.12.0 calls `json.loads()` before validators, causing `JSONDecodeError` at startup. The `NoDecode` annotation + `parse_cors_origins` validator handles both formats.

### LangGraph checkpointer (PostgreSQL)
Fields not set in `create_initial_state()` survive from previous conversation turns. Always reset fields explicitly. This bug only manifests with the live PostgreSQL checkpointer — invisible locally with `MemorySaver` or `ENABLE_CHECKPOINTING=false`.

### CI formatting failures
Run `uv run ruff format app/` in `backend/` before every commit. The pre-commit hook does this automatically but must be installed: `cd backend && uv run pre-commit install`.

### Railway memory limits (~512MB hobby tier)
FlashRank is pre-warmed at startup (in `main.py` lifespan) to avoid mid-request OOM spikes. Keep `rerank_model=ms-marco-TinyBERT-L-2-v2` and `top_k ≤ 10` on hobby tier.

---

## Environment & Execution

### Backend
- **Never** run `python script.py` — always `uv run script.py` (from `backend/`)
- **Never** activate the venv manually for commands — `uv run` handles it
- To add dependencies: `uv add <package>` or `uv add --dev <package>`

### Git
- `main` branch is **protected** — always branch and PR
- CI runs on PR to main: ruff lint + format check (backend), ESLint + build (frontend)
- ClickUp workspace: `9013416053` | Advanced Agentic RAG list: `901325927502`
