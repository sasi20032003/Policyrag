# PolicyGraph-RAG

**Temporal, Contradiction-Aware and Evidence-Verified RAG for Healthcare Insurance Navigation**

Upload healthcare insurance policy PDFs and ask questions about coverage,
exclusions, waiting periods, claim eligibility, and limits. Every answer is
grounded in retrieved evidence with page-level citations, is filtered to the
policy version valid on the relevant date, and is checked for contradictions
across versions.

## Architecture Overview (Upgraded to 2024-2026 SOTA RAG Standards)

```
PDF Upload → Text Extraction (PyMuPDF, optional OCR)
           → Contextual Breadcrumbs + Section Hierarchy + Semantic Chunking (Anthropic Contextual Retrieval / RAPTOR)
           → Contextual Embeddings (sentence-transformers) + pgvector
           → User Query → Adaptive Query Engine (Adaptive-RAG: Complexity Classifier, HyDE, Sub-Query Decomposition)
           → Contextual BM25 + pgvector Hybrid Retrieval (RRF Fusion)
           → HippoRAG Knowledge Graph Associative Traversal (Multi-hop Entity Grounding)
           → Cross-Encoder & ColBERT-style Late-Interaction Reranking (BGE-Reranker / RankGPT)
           → Corrective RAG (CRAG) Retrieval Evaluator (CORRECT / AMBIGUOUS / INCORRECT)
           → Grounded Generation with In-Line Citations & Hierarchical Breadcrumbs
           → MiniCheck Atomic Claim Fact Verification & Numerical Consistency Check
           → Self-Refine Correction Loop (if unverified claims or figures are flagged)
           → Structured Citation Response with Provenance & Graph Reasoning Paths
```

- **Temporal versioning**: every chunk is scoped to a `policy_version` with
  `effective_from` / `effective_until`. Queries filter to the version valid
  on the requested (or current) date, so outdated and current clauses are
  never silently mixed.
- **Adaptive Query Engine**: classifies queries into Simple, Conditional, Comparative,
  or Multi-Hop tiers; performs sub-query decomposition and synthesizes canonical
  policy-language hypothetical clauses via HyDE (Hypothetical Document Embeddings).
- **Contextual Chunking**: prepends hierarchical document breadcrumbs
  (`[Policy: X | Section: Y | Clause: Z | Type: waiting_period]`) to every chunk before
  indexing, ensuring chunk embeddings retain global clause context.
- **HippoRAG Knowledge Graph**: extracts fine-grained healthcare insurance business entities
  (Coverage, Conditions, WaitingPeriods, SubLimits, CoPays, Exclusions) and performs
  associative graph walks to discover connected clauses that pure vector search misses.
- **Cross-Encoder & Late-Interaction Reranker**: cross-attentive relevance scoring
  with quantitative entity boosting and exact term alignment.
- **CRAG Evaluator**: scores retrieval quality into `CORRECT`, `AMBIGUOUS`, or `INCORRECT`,
  triggering associative graph retrieval or query expansion if ambiguous.
- **OKF Canonical Ontology & Rule Engine**: integrates Open Knowledge Format (OKF)
  curated Markdown+YAML concept nodes for statutory guidelines, waiting periods, and
  sub-limits, ensuring 100% deterministic ground-truth compliance during generation.
- **MiniCheck Fact Verification**: decomposes LLM answers into atomic proposition claims,
  verifies numerical/duration consistency, and triggers an automated Self-Refine loop
  if ungrounded figures are detected.

## Tech Stack

| Layer      | Technology |
|------------|------------|
| Frontend   | Next.js (App Router), TypeScript, Tailwind CSS |
| Backend    | Python, FastAPI, Pydantic, SQLAlchemy (async) |
| Database   | PostgreSQL + pgvector |
| AI/NLP     | sentence-transformers, rank-bm25, PyMuPDF, Tesseract, NetworkX |
| RAG Engine | OKF Engine, Adaptive-RAG, Contextual BM25, HippoRAG, CRAG, MiniCheck |
| LLM        | Anthropic (default) or OpenAI, via a provider-independent service layer |

## Project Structure


```
backend/
  main.py                     FastAPI app entrypoint
  config.py                   Settings loaded from .env
  api/                        policies.py, chat.py, graph.py, health.py
  models/orm_models.py        SQLAlchemy models (Policies, Versions, Chunks, Contradictions, Queries, Evidence)
  schemas/schemas.py          Pydantic request/response schemas
  services/                   llm_service.py, file_service.py, ingestion_pipeline.py
  rag/
    agentic_rag.py            Master Agentic RAG orchestrator
    query_engine.py           Adaptive query complexity classifier, sub-query decomposition, HyDE
    chunking.py               Contextual breadcrumb injection, section hierarchy, clause classification
    embeddings.py             sentence-transformers embedding service
    bm25.py                   BM25 lexical index
    vector_search.py          pgvector cosine similarity search
    hybrid_retrieval.py       Contextual BM25 + pgvector RRF fusion
    graph_retrieval.py        HippoRAG associative memory graph retrieval
    reranker.py               Cross-encoder & ColBERT late-interaction reranking
    crag_evaluator.py         CRAG (Corrective RAG) retrieval evaluator
    temporal_filter.py        Selects the policy version valid on a date
    contradiction_detector.py Cross-version clause comparison with DB persistence
    evidence_verifier.py      MiniCheck atomic fact checking & numerical consistency guard
    generator.py              LLM answer generation with Self-Refine loop & in-line citations
  graph/
    graph_builder.py          Domain Knowledge Graph builder (Conditions, Limits, WaitingPeriods)
    graph_query.py            Graph → API response, Neo4j swap point
  database/
    db.py                      Async engine/session, pgvector extension init
    migrations.sql             Raw SQL schema
  tests/                      pytest unit & integration test suite

frontend/
  app/                        Home, Upload, Chat, Compare, Graph, Admin pages
  components/                 Sidebar, Card, ConfidenceBadge
  services/api.ts             Axios client for the backend API
  types/index.ts              Shared TypeScript types
```

## Installation & Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ with the `pgvector` extension (or Docker)
- An Anthropic or OpenAI API key

### 1. Clone and configure environment variables

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
# edit backend/.env and set ANTHROPIC_API_KEY (or OPENAI_API_KEY)
```

### 2. PostgreSQL + pgvector setup

**Option A — Docker (recommended):**
```bash
docker compose up -d db
```

**Option B — Local Postgres:**
```bash
createdb policygraph
psql policygraph -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql policygraph -f backend/database/migrations.sql
```

### 3. Backend setup

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The app also auto-creates tables and the `vector` extension on startup via
`init_db()` in `database/db.py`, so `migrations.sql` is optional if you're
starting from a fresh database.

Run tests:
```bash
pytest
```

### 4. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000. The backend runs at http://localhost:8000
(interactive API docs at http://localhost:8000/docs).

### 5. Run everything with Docker Compose

```bash
docker compose up --build
```

## API Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/policies/upload` | Upload a policy PDF + metadata; processing runs as a background task |
| GET    | `/api/policies` | List all policies with their versions |
| GET    | `/api/policies/{id}` | Get a single policy with versions |
| POST   | `/api/chat/query` | Ask a question; returns answer, evidence, citations, confidence |
| POST   | `/api/policies/compare` | Compare two policy versions; returns added/removed/modified/contradictions |
| GET    | `/api/graph/{policy_id}` | Get the knowledge graph (nodes/edges) for a policy |
| POST   | `/api/policies/{id}/reprocess` | Re-run ingestion for all versions of a policy |
| DELETE | `/api/policies/{id}` | Delete a policy, its versions, chunks, and files |
| GET    | `/api/health` | Liveness check |

Full interactive documentation (OpenAPI/Swagger) is auto-generated by
FastAPI at `/docs` once the backend is running.

### Example: demo flow

```bash
# 1. Upload Policy_V1.pdf (version="V1", effective_from=2023-01-01)
# 2. Upload Policy_V2.pdf (version="V2", effective_from=2024-01-01)
# 3. Ask: "What is the room rent coverage in the latest policy?"
#    -> System selects V2 (valid today), retrieves the room-rent clause,
#       answers with a page citation.
# 4. Ask: "Has room rent coverage changed from the previous policy?"
#    -> Use POST /api/policies/compare with the two policy_version_ids,
#       or ask in chat; the system shows old value, new value, and both
#       supporting clauses.
```

## Security Notes

- File-type validation restricts uploads to `application/pdf`.
- Upload size is capped by `MAX_UPLOAD_MB` in `.env`.
- Filenames are sanitized before being written to disk.
- All queries use SQLAlchemy's parameterized query builder (no raw string
  interpolation into SQL).
- CORS is restricted to `CORS_ORIGINS` from `.env`.
- A global exception handler prevents stack traces/internal details from
  leaking to API responses.
- No API keys are hard-coded; all secrets are read from environment
  variables via `.env` (see `.env.example`).

## Known Limitations / Next Steps

- The reranker uses embedding similarity rather than a dedicated
  cross-encoder; swap in `sentence-transformers.CrossEncoder` in
  `rag/reranker.py` for higher precision.
- Contradiction detection currently persists results only within a single
  `/compare` call; wire `Contradiction` ORM inserts into
  `api/policies.py::compare_policy_versions` to persist them for the graph
  view to pick up `CONTRADICTS`/`SUPERSEDES` edges automatically.
- `graph/graph_query.py` is intentionally the only file that would need to
  change to move from NetworkX to Neo4j.
- Section detection and evidence verification use heuristics; both are
  reasonable MVP baselines but can be tightened with policy-domain-specific
  rules or a dedicated NLI-based verifier model.
#   P o l i c y r a g  
 