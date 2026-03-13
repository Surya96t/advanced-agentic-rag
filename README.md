# Advanced RAG System

A production-grade Retrieval-Augmented Generation system with multi-stage chunking, hybrid search, and agentic workflows.

## 🚀 Features

- **Multi-Stage Chunking**: RecursiveCharacter, Semantic, Parent-Child, Contextual, and Code-Aware strategies
- **Hybrid Search**: Dense vector embeddings + sparse text search with Reciprocal Rank Fusion (RRF)
- **Agentic RAG**: LangGraph-powered workflows with query expansion and conversational memory
- **Smart Re-ranking**: FlashRank and Cohere re-rankers for precision
- **Enterprise Security**: Row-Level Security (RLS) with JWT validation
- **Blazing Fast**: HNSW index for sub-second vector search

## 🛠️ Tech Stack

- **Frontend:** Next.js 15, TypeScript, Tailwind CSS, Clerk Auth
- **Backend:** FastAPI, LangGraph, LangChain
- **Database:** Supabase (PostgreSQL + pgvector)
- **AI/ML:** OpenAI (embeddings + LLM), FlashRank, Cohere

## 📦 Getting Started

### Prerequisites

- Node.js 18+ and pnpm
- Python 3.12+
- Docker (for Redis — used by Celery background worker)
- Supabase account
- OpenAI API key
- Clerk account (for authentication)

### Clone the Repository

```bash
git clone https://github.com/yourusername/advanced-agentic-rag.git
cd advanced-agentic-rag
```

### Backend Setup

1. **Navigate to backend directory:**

   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your Supabase, OpenAI, and other credentials
   ```

5. **Run database migrations:**

   ```bash
   # Follow instructions in backend/migrations/ACTUAL_SCHEMA.md
   ```

6. **Start the development server:**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

7. **Start Redis (required for background ingestion):**
   ```bash
   docker compose up -d
   ```

8. **Start the Celery worker (in a separate terminal):**
   ```bash
   cd backend
   source .venv/bin/activate
   celery -A app.ingestion.background worker --loglevel=info
   ```

   > The worker processes document ingestion (parse → chunk → embed → store) in the background.
   > The FastAPI server returns `202 Accepted` immediately on upload; the frontend polls for completion.

### Frontend Setup

1. **Navigate to frontend directory:**

   ```bash
   cd frontend
   ```

2. **Install dependencies:**

   ```bash
   pnpm install
   ```

3. **Set up environment variables:**

   ```bash
   cp .env.example .env.local
   # Add your Clerk and backend API credentials
   ```

4. **Start the development server:**

   ```bash
   pnpm dev
   ```

5. **Open your browser:**
   ```
   http://localhost:3000
   ```

## License

MIT

## 🤝 Contributing

This is a personal portfolio project. Feel free to fork and adapt for your own use!
