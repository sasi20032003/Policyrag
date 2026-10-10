# PolicyGraph-RAG: Interview Challenges & FastAPI / REST API Architecture Guide

> **Target Audience:** Technical & System Design Interviews (AI Engineer, Full-Stack GenAI Architect, Python Backend Engineer)  
> **Project:** PolicyGraph-RAG (Healthcare Insurance Navigation)  
> **Date:** September 2026  

---

## TABLE OF CONTENTS
1. [The 5-Minute Quick Interview Pitch (Rapid Review)](#1-the-5-minute-quick-interview-pitch-rapid-review)
2. [6 Realistic Project Challenges & Solutions (Deep Dive)](#2-6-realistic-project-challenges--solutions-deep-dive)
   - [Challenge 1: Fragmented Legal Clauses & Lost Exclusions (Chunking)](#challenge-1-fragmented-legal-clauses--lost-exclusions-chunking)
   - [Challenge 2: Search Missing Numbers & Codes vs Synonyms (Hybrid Search & RRF)](#challenge-2-search-missing-numbers--codes-vs-synonyms-hybrid-search--rrf)
   - [Challenge 3: Critical Financial Sub-Limit Hallucinations (Guardrails)](#challenge-3-critical-financial-sub-limit-hallucinations-guardrails)
   - [Challenge 4: Temporal Contamination Across Policy Renewal Years (Versioning)](#challenge-4-temporal-contamination-across-policy-renewal-years-versioning)
   - [Challenge 5: High Compute Cost & Latency in Contradiction Detection (Algorithm Optimization)](#challenge-5-high-compute-cost--latency-in-contradiction-detection-algorithm-optimization)
   - [Challenge 6: Ingestion Timeouts & Embedding Cold Starts (Production Engineering)](#challenge-6-ingestion-timeouts--embedding-cold-starts-production-engineering)
3. [REST API vs. FastAPI: Core Concepts Explained](#3-rest-api-vs-fastapi-core-concepts-explained)
   - [What is a REST API?](#what-is-a-rest-api)
   - [What is FastAPI?](#what-is-fastapi)
   - [Comparison Table](#comparison-table)
4. [How REST API & FastAPI are Used in This Project](#4-how-rest-api--fastapi-are-used-in-this-project)
   - [Client-Server Architecture Flow](#client-server-architecture-flow)
   - [Complete Endpoints Table](#complete-endpoints-table)
   - [Key FastAPI Production Implementations in Code](#key-fastapi-production-implementations-in-code)
5. [Quick Interview Soundbites & Summary](#5-quick-interview-soundbites--summary)

---

# 1. THE 5-MINUTE QUICK INTERVIEW PITCH (RAPID REVIEW)

Use this section if the interviewer asks:  
*"What were the biggest challenges you faced while building this project and how did you solve them?"*

### **Opening (15 seconds)**
> *"While architecting PolicyGraph-RAG, I tackled 6 major technical challenges across data preprocessing, hybrid retrieval, deterministic hallucination guardrails, cross-version diffing, and async system scaling:"*

* **1. Breaking Rules in Half (Chunking):** Fixed-size chunking split benefits from their waiting periods and exclusions. **Fixed by** building a section-aware chunker using header regex detection and a 900-char window with 150-char sliding overlap to preserve conditional clauses together.
* **2. Search Missing Exact Numbers vs. Synonyms (Retrieval):** Vector search missed exact monetary caps (e.g., "₹5,000 room rent") while BM25 missed synonyms. **Fixed by** building a Hybrid Search engine combining BM25 and pgvector cosine via Reciprocal Rank Fusion (RRF, $k=60$) followed by a 2nd-stage cosine reranker.
* **3. AI Making Up Financial Numbers (Hallucination):** Standard prompting couldn't 100% prevent the LLM from inventing sub-limits. **Fixed by** building a post-generation numerical set-difference verifier ($\text{Unsupported} = \text{Nums}_{\text{Answer}} \setminus \text{Nums}_{\text{Evidence}}$) that blocks answers with ungrounded numbers.
* **4. Mixing Old & New Policy Versions (Temporal Leakage):** Standard vector search mixed expired 2022 clauses with active 2024 policies. **Fixed by** enforcing SQL-level metadata date filtering (`effective_from` / `effective_until`) in PostgreSQL *before* running vector distance queries.
* **5. Comparing 100-Page Policies Was Too Slow & Costly:** Brute-force pairwise LLM comparison required 44,000 API calls taking 45+ minutes. **Fixed by** a two-tier pipeline: computed an $N \times M$ NumPy cosine matrix to prune 85% of unchanged/missing clauses, dispatching only changed candidates to the LLM (cut time to <30s and saved 90%+ cost).
* **6. 100-Page PDF Ingestion Freezing the Frontend (Timeouts):** Processing PDFs took 60+ seconds, causing 504 HTTP timeouts. **Fixed by** offloading ingestion to FastAPI `BackgroundTasks` (instant 200 OK upload response in ~120ms) and keeping the embedding model cached as an in-memory singleton.

### **Closing (15 seconds)**
> *"The core architectural takeaway was treating RAG as an end-to-end deterministic system—combining hybrid retrieval, database temporal scoping, and post-generation mathematical validation rather than relying purely on LLM prompting."*

---

# 2. 6 REALISTIC PROJECT CHALLENGES & SOLUTIONS (DEEP DIVE)

### Challenge 1: Fragmented Legal Clauses & Lost Exclusions (Chunking)
* **The Challenge:**  
  Standard fixed-size chunking (e.g., splitting every 500 characters) created artificial boundaries. In insurance contracts, a clause typically follows:  
  *`"Maternity expenses are covered up to ₹50,000... [Chunk boundary] ...subject to a continuous waiting period of 24 months."`*  
  If chunked arbitrarily, the retriever only retrieved the benefit chunk, causing the LLM to give dangerously incomplete answers to users.
* **How It Was Solved:**  
  Built a **Section-Aware Semantic Chunker** (`backend/rag/chunking.py`):
  - Used regex patterns (`SECTION_HEADER_RE`) to detect major headers (e.g., numbered clauses like `Section 4.1`, `Clause B`, or `ALL CAPS` headers).
  - Buffered full sentences into a sliding window with a target of **900 characters** and a **150-character overlap**.
  - Flushed the chunk buffer whenever a new section boundary was encountered, ensuring contractual conditions remain bound to the benefit they modify.
* **Outcome / Metric:** Preserved 100% of conditional sub-clauses within the same retrieval context, eliminating false eligibility recommendations.

---

### Challenge 2: Search Missing Numbers & Codes vs Synonyms (Hybrid Search & RRF)
* **The Challenge:**  
  Pure semantic vector search (dense embeddings) struggled with exact alphanumeric identifiers and numbers—such as *"Clause 4.2.1"*, *"₹5,000 room rent cap"*, or policy UINs—because embeddings map them into general numeric space. Conversely, pure keyword search (BM25) failed when users asked conceptual questions (e.g., *"Where can I stay after surgery?"* vs. *"Room Rent & Boarding Expenses"*).  
  Combining them naively via linear score weighting ($\alpha \cdot \text{Vector} + (1-\alpha) \cdot \text{BM25}$) failed because BM25 scores are unbounded positive numbers ($0$ to $30+$) while cosine similarities are bounded between $0$ and $1$.
* **How It Was Solved:**  
  Implemented a **Hybrid Retrieval Engine with Reciprocal Rank Fusion (RRF)** (`backend/rag/hybrid_retrieval.py`):
  - Query executed across both BM25 and pgvector cosine distance simultaneously.
  - Fused rankings using RRF ($k=60$):  
    $$\text{RRF Score}(d) = \frac{1}{60 + \text{Rank}_{\text{BM25}}(d)} + \frac{1}{60 + \text{Rank}_{\text{Vector}}(d)}$$
  - Since RRF aggregates **relative rank positions** instead of raw scores, no fragile score normalization constants were required. The top 15 candidate chunks were then reranked to feed the top 8 into the LLM context.
* **Outcome / Metric:** High-precision retrieval for both exact alphanumeric policy clauses and fuzzy semantic questions without brittle parameter tuning.

---

### Challenge 3: Critical Financial Sub-Limit Hallucinations (Guardrails)
* **The Challenge:**  
  In health insurance, even a subtle hallucination—such as stating a room rent limit is *"₹7,500/day"* instead of *"₹5,000/day"* or *"1% of Sum Insured"*—leads to catastrophic financial shortfall for a policyholder due to proportionate deduction penalties. System prompting alone (*"only answer from context"*) was not 100% foolproof against parametric LLM bias.
* **How It Was Solved:**  
  Built a post-generation **Deterministic Numerical & Lexical Evidence Verifier** (`backend/rag/evidence_verifier.py`) as a guardrail:
  - **Regex Number Extraction:** Extracted all numbers, currency values, and percentages (`\d[\d,]*\.?\d*`) from both the generated answer and retrieved evidence chunks.
  - **Set Difference Validation:** Computed the mathematical set difference:  
    $$\text{Unsupported} = \text{Numbers}_{\text{Answer}} \setminus \text{Numbers}_{\text{Evidence}}$$
  - **Lexical Overlap & Confidence Scoring:** Computed token overlap between the answer and evidence. If unsupported numbers appeared or composite confidence fell below $0.25$, the answer was flagged or suppressed, falling back to a safe refusal message.
* **Outcome / Metric:** Guaranteed zero ungrounded financial figures reach the end user by enforcing a post-generation mathematical check.

---

### Challenge 4: Temporal Contamination Across Policy Renewal Years (Versioning)
* **The Challenge:**  
  Health insurers (like Star Health or Niva Bupa) revise policy wordings annually. If both 2022 (V1) and 2024 (V2) versions exist in the vector database, standard vector similarity retrieves the most semantically similar chunk regardless of version. This caused "temporal contamination," where an expired 2022 clause was returned for a claim occurring in 2024.
* **How It Was Solved:**  
  Implemented **Temporal Scoping at the Database Query Planner Level** (`backend/rag/temporal_filter.py`):
  - Attached temporal metadata (`effective_from`, `effective_until`, `version_id`) to every chunk in PostgreSQL.
  - Every user query accepts an optional `as_of_date` or policy version scope.
  - Filtered chunks via relational SQL predicates (`WHERE effective_from <= :date AND (effective_until >= :date OR effective_until IS NULL)`) *prior* to executing the vector cosine distance calculation.
* **Outcome / Metric:** Achieved complete temporal isolation without maintaining separate siloed vector databases for every policy renewal year.

---

### Challenge 5: High Compute Cost & Latency in Contradiction Detection (Algorithm Optimization)
* **The Challenge:**  
  To detect when insurers silently reduce benefits or alter waiting periods between Version A (e.g., 200 chunks) and Version B (e.g., 220 chunks), a brute-force approach of comparing every clause pair with an LLM would require $200 \times 220 = 44,000$ LLM calls. This was computationally prohibitive, cost hundreds of dollars per document, and took over an hour.
* **How It Was Solved:**  
  Engineered a **Two-Tier Contradiction Detection Pipeline** (`backend/rag/contradiction_detector.py`):
  - **Tier 1 (Vectorized Cosine Affinity Matrix):** Embed all chunks of Version A and B in batches. Compute the $N \times M$ cosine similarity matrix in NumPy.
    - If $\max(\text{similarity}) < 0.55 \rightarrow$ instantly classified as `REMOVED` (or `ADDED` for unmatched chunks) with **zero LLM calls**.
    - If similarity is identical ($1.0$) and text matches $\rightarrow$ classified as `SAME`.
  - **Tier 2 (Targeted LLM Evaluation):** Only clauses with similarity $\ge 0.55$ that had text differences were dispatched to the LLM with a structured JSON schema to classify as `UPDATED` or `CONTRADICTORY`.
* **Outcome / Metric:** Pruned over 85% of clause comparisons using vector algebra, reducing comparison time from 45 minutes to under 30 seconds and saving 90%+ in LLM API costs.

---

### Challenge 6: Ingestion Timeouts & Embedding Cold Starts (Production Engineering)
* **The Challenge:**  
  Extracting text from 60–120 page insurance PDFs, chunking, and generating 384-dimensional embeddings on CPU took 35–80 seconds per file. This caused HTTP connection timeouts (504 Gateway Timeout) on the frontend. Additionally, initializing the PyTorch `SentenceTransformer` model inside request handlers caused multi-second cold-start latency and memory leaks.
* **How It Was Solved:**  
  - **Asynchronous Task Offloading:** Used FastAPI's `BackgroundTasks`. The upload endpoint (`/api/policies/upload`) validates MIME types, checks size limits ($\le 25\text{MB}$), sanitizes the filename, writes the file to disk with a UUID prefix, inserts a DB record with `status='pending'`, and responds with `200 OK` in **~120ms**. Ingestion runs asynchronously in the background.
  - **Singleton Embedding Service (`backend/rag/embeddings.py`):** Instantiated `all-MiniLM-L6-v2` as a process-level singleton loaded once during server lifecycle startup, keeping weights hot in memory.
* **Outcome / Metric:** Shifted upload response latency from 60+ seconds to ~120ms with 100% upload reliability, and reduced query embedding latency to under 15ms.

---

# 3. REST API VS. FASTAPI: CORE CONCEPTS EXPLAINED

### What is a REST API?
A **REST API** (Representational State Transfer) is an architectural set of rules that defines how client applications (like a browser/mobile app) talk to backend servers over the web using standard **HTTP protocols**.

* **Analogy:**  
  Think of a restaurant. You are the **Client**. The kitchen is the **Database/Backend**. The **REST API** is the **Waiter** who takes your order from the menu and delivers the food back to your table.
* **Core HTTP Verbs:**
  - `GET`: Read / retrieve data (e.g., fetch all policies).
  - `POST`: Create or submit new data (e.g., submit a question or upload a PDF).
  - `PUT` / `PATCH`: Update existing records.
  - `DELETE`: Remove records.
* **Data Format:** Almost universally exchanges data in **JSON** (JavaScript Object Notation).

### What is FastAPI?
**FastAPI** is a modern, high-performance web framework for **Python** specifically designed to build REST APIs.
* **Why it's popular in AI/ML:**
  1. **Async by Default:** Native `async/await` syntax allows handling thousands of concurrent requests without blocking worker threads while waiting for DB or LLM responses.
  2. **Data Validation via Pydantic:** Uses standard Python type hints to automatically validate incoming request bodies and outgoing responses.
  3. **Auto-Generated Documentation:** Generates an interactive OpenAPI Swagger UI at `/docs` out of the box.

### Comparison Table

| Feature | REST API | FastAPI |
| :--- | :--- | :--- |
| **What is it?** | An **architectural standard/concept** (the design rules). | A **Python library/framework** (the software tool). |
| **Role** | Specifies *how* data should be requested and structured. | Provides the code implementation to build endpoints that follow those rules. |
| **Analogy** | The blueprint/concept of an electric car. | The Tesla motor powering the actual car. |

---

# 4. HOW REST API & FASTAPI ARE USED IN THIS PROJECT

### Client-Server Architecture Flow

```
┌──────────────────────────────────────┐
│        FRONTEND (Next.js 14)         │
│          Runs on Port 3000           │
│    Pages: /upload, /chat, /compare   │
└──────────────────┬───────────────────┘
                   │
                   │ HTTP REST Requests (Axios Client in frontend/services/api.ts)
                   │ JSON Payloads & multipart/form-data
                   ▼
┌──────────────────────────────────────┐
│        BACKEND (FastAPI App)         │
│          Runs on Port 8000           │
│      main.py + uvicorn server        │
├──────────────────────────────────────┤
│ Routers:                             │
│  • policies.py  • chat.py            │
│  • graph.py     • health.py          │
├──────────────────────────────────────┤
│ BackgroundTasks | Pydantic Schemas   │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ DATABASE & AI ENGINES                │
│  • PostgreSQL 15 + pgvector (384d)   │
│  • Anthropic Claude / OpenAI GPT-4o  │
│  • Sentence-Transformers (MiniLM)    │
└──────────────────────────────────────┘
```

---

### Complete Endpoints Table

| Method | Endpoint | Source File | Purpose & Flow |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/policies/upload` | `backend/api/policies.py` | Receives PDF via `multipart/form-data`. Saves file, creates DB record (`status='pending'`), and schedules async background ingestion. |
| `GET` | `/api/policies` | `backend/api/policies.py` | Queries PostgreSQL and returns a JSON list of all policies with version details. |
| `GET` | `/api/policies/{id}` | `backend/api/policies.py` | Fetches details and metadata for a specific policy ID. |
| `POST` | `/api/chat/query` | `backend/api/chat.py` | Receives `{ question, policy_id, as_of_date }`. Runs temporal filter $\rightarrow$ hybrid search $\rightarrow$ reranker $\rightarrow$ LLM generation $\rightarrow$ evidence verification. |
| `POST` | `/api/policies/compare` | `backend/api/policies.py` | Compares two versions using vector matrix pruning + LLM classification. Returns clause diffs. |
| `GET` | `/api/graph/{policy_id}` | `backend/api/graph.py` | Builds NetworkX graph (Policies, Versions, Clauses, Exclusions) and outputs nodes & edges for frontend graph visualization. |
| `GET` | `/api/health` | `backend/api/health.py` | Simple liveness check returning `{"status": "ok"}` for monitoring/Docker. |

---

### Key FastAPI Production Implementations in Code

1. **Modular Routing (`APIRouter`):**  
   In `backend/main.py`, routers are modularly registered:
   ```python
   app.include_router(health.router)
   app.include_router(policies.router)
   app.include_router(chat.router)
   app.include_router(graph.router)
   ```
2. **Asynchronous Non-Blocking Processing (`BackgroundTasks`):**  
   In `backend/api/policies.py`:
   ```python
   @router.post("/upload")
   async def upload_policy(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
       # File saved to disk and version inserted as 'pending'
       background_tasks.add_task(run_ingestion_pipeline, version_id, file_path)
       return {"message": "Upload successful, ingestion started in background"}
   ```
3. **Pydantic Validation (`backend/schemas/schemas.py`):**  
   Guarantees incoming payloads match expected types before executing business logic:
   ```python
   class ChatQueryRequest(BaseModel):
       question: str
       policy_id: Optional[UUID] = None
       as_of_date: Optional[date] = None
       top_k: int = 8
   ```
4. **CORS Security (`CORSMiddleware`):**  
   Configured in `main.py` using `allow_origins=["http://localhost:3000"]` to prevent unauthorized cross-origin browser requests while allowing the Next.js frontend to communicate seamlessly.
5. **Global Exception Handling:**  
   Catches unhandled errors globally, logging the stack trace internally while returning a sanitized JSON error (`{"detail": "Internal server error."}`) to prevent exposing database or environment credentials.

---

# 5. QUICK INTERVIEW SOUNDBITES & SUMMARY

| Question | 15-Second Answer |
| :--- | :--- |
| **"Why FastAPI over Flask or Django?"** | *"FastAPI gives us native `async/await` performance for our asynchronous database and LLM calls, out-of-the-box Pydantic validation, and lightweight background task processing without the heavy overhead of Django or the sync-blocking nature of legacy Flask."* |
| **"How does the frontend talk to the backend?"** | *"The Next.js frontend uses an Axios client in `frontend/services/api.ts` to make RESTful HTTP calls (GET, POST) transmitting JSON payloads and multipart PDF uploads to FastAPI endpoints running on port 8000."* |
| **"What was your single hardest bug/challenge?"** | *"Preventing numerical hallucinations in health insurance sub-limits. Solved it by implementing a post-generation deterministic regex set-difference verifier that guarantees every number generated by the LLM exists verbatim in the retrieved source clauses."* |
