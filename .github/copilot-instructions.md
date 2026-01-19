# GitHub Copilot Instructions for "Integration Forge"

## Project Overview
**Integration Forge** is a production-grade advanced RAG (Retrieval-Augmented Generation) system that helps developers synthesize integration code from siloed API documentation.

**Tech Stack:**
- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind CSS, Clerk Auth
- **Backend:** FastAPI (Python), LangGraph, LangChain
- **Database:** Supabase (PostgreSQL + pgvector)
- **AI/ML:** OpenAI (embeddings + LLM), FlashRank/Cohere (re-ranking)

**Core Features:**
- Multi-stage chunking (RecursiveCharacter, Semantic, Parent-Child, Contextual, Code-Aware)
- Hybrid search (dense vector + sparse text + RRF fusion)
- Re-ranking with FlashRank and Cohere
- LLM-based query expansion
- Agentic workflows with LangGraph
- Row-Level Security (RLS) with JWT validation
- Rate limiting and observability (LangSmith)

**Key Architecture:**
- FastAPI backend exposes REST + SSE streaming endpoints
- Supabase handles auth, data storage, vector search
- LangGraph orchestrates agentic RAG workflows
- Next.js frontend provides upload and chat interface

---

## General Coding Rules

### **Documentation**
- ❌ **DO NOT create documentation files** (README, docs, architecture diagrams, etc.) unless explicitly asked
- ✅ **DO add inline code comments** for complex logic
- ✅ **DO add docstrings** to functions and classes
- ✅ **DO add JSDoc/TSDoc** for TypeScript code

### **Code Style**
- Use TypeScript for all frontend code (strict mode)
- ❌ **NEVER use `any` type** - use proper types, `unknown`, or generics
- ✅ **DO use** Next.js route-aware type helpers (`PageProps`, `LayoutProps`, `RouteContext`)
- ✅ **DO use** statically typed links with `Route<T>` for type-safe navigation
- ✅ **DO use** TypeScript 5.1.3+ for async Server Components
- ✅ **DO enable** `incremental` type checking in `tsconfig.json`
- Use Python type hints for all backend code
- Follow existing patterns in the codebase
- Prefer composition over inheritance
- Keep functions small and focused

### **Project-Specific Guidelines**
- All database operations must respect RLS policies
- All API endpoints must validate JWT tokens
- All chunking strategies must store metadata in `document_chunks.metadata` JSONB column
- All vector searches must use hybrid approach (dense + sparse)
- All LLM calls must be traced with LangSmith

---

## Next Steps
See `/docs/README.md` for full technical specifications and implementation plan.
