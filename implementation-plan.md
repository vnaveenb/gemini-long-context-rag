# Implementation Plan — Learning Content Compliance Intelligence System

> Derived from [prd.md](prd.md)
> Created: February 12, 2026

---

## Table of Contents

1. [Implementation Overview](#1-implementation-overview)
2. [Technology Stack](#2-technology-stack)
3. [Phase 0 — Project Setup and Foundation](#3-phase-0--project-setup-and-foundation)
4. [Phase 1 — Document Ingestion Pipeline](#4-phase-1--document-ingestion-pipeline)
5. [Phase 2 — Preprocessing and Chunking](#5-phase-2--preprocessing-and-chunking)
6. [Phase 3 — Embedding and Vector Storage](#6-phase-3--embedding-and-vector-storage)
7. [Phase 4 — Retrieval Engine](#7-phase-4--retrieval-engine)
8. [Phase 5 — DQC Evaluation Engine](#8-phase-5--dqc-evaluation-engine)
9. [Phase 6 — Orchestration Layer](#9-phase-6--orchestration-layer)
10. [Phase 7 — Reporting Module](#10-phase-7--reporting-module)
11. [Phase 8 — Audit and Traceability](#11-phase-8--audit-and-traceability)
12. [Phase 9 — Frontend and API Layer](#12-phase-9--frontend-and-api-layer)
13. [Phase 10 — Admin Features](#13-phase-10--admin-features)
14. [Phase 11 — Testing, Hardening, and Performance](#14-phase-11--testing-hardening-and-performance)
15. [Phase 12 — Deployment and Release](#15-phase-12--deployment-and-release)
16. [Timeline Summary](#16-timeline-summary)
17. [Risk Register and Contingency](#17-risk-register-and-contingency)
18. [Definition of Done per Phase](#18-definition-of-done-per-phase)

---

## 1. Implementation Overview

The project is divided into **13 sequential phases** (Phase 0–12) with clear deliverables, dependencies, and acceptance criteria. The total estimated timeline for MVP is **14–16 weeks** for a small team (2–3 engineers).

### Guiding Principles

- Build end-to-end with a single document first, then optimize
- Every phase must produce a testable artifact
- Fail fast — validate Gemini output quality in Phase 5 before investing in UI
- Local-first deployment; no cloud dependencies for MVP

### Dependency Graph

```
Phase 0 (Setup)
  └─► Phase 1 (Ingestion)
        └─► Phase 2 (Chunking)
              └─► Phase 3 (Embedding + Vector DB)
                    └─► Phase 4 (Retrieval)
                          └─► Phase 5 (DQC Engine)  ← Critical Validation Gate
                                └─► Phase 6 (Orchestration)
                                      ├─► Phase 7 (Reporting)
                                      └─► Phase 8 (Audit)
                                            └─► Phase 9 (Frontend + API)
                                                  └─► Phase 10 (Admin)
                                                        └─► Phase 11 (Testing)
                                                              └─► Phase 12 (Deployment)
```

---

## 2. Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Language | Python 3.11+ | ML/AI ecosystem, rapid development |
| **LLM Framework** | **LangChain + LangChain-Google-GenAI** | **Provider-agnostic abstraction — hot-swap LLMs without code changes** |
| LLM (Default) | Gemini 1.5 Pro (via LangChain `ChatGoogleGenerativeAI`) | Long context window (1M tokens), structured output |
| Embeddings (Default) | Gemini `text-embedding-004` (via LangChain `GoogleGenerativeAIEmbeddings`) | Consistency with LLM provider, swappable via config |
| Vector DB | ChromaDB (via LangChain `Chroma` wrapper) | Zero-config, file-based, good Python integration |
| API Framework | FastAPI | Async support, auto-docs, Pydantic validation |
| Frontend | Streamlit (MVP) → React (Phase 3 deployment) | Rapid prototyping for MVP |
| PDF Extraction | PyMuPDF (fitz) | Fast, preserves structure |
| DOCX Extraction | python-docx | Native format support |
| PPTX Extraction | python-pptx | Slide-level extraction |
| XLSX Extraction | openpyxl | Sheet and cell extraction |
| Report Generation | ReportLab (PDF), python-docx (DOCX) | Programmatic report creation |
| Orchestration | LangChain LCEL chains + Custom Python + asyncio | Composable chains with provider flexibility |
| Output Parsing | LangChain `PydanticOutputParser` / `JsonOutputParser` | Structured output with automatic retry parsing |
| Logging | structlog + SQLite + LangChain callbacks | Structured JSON logs with queryable store + LLM call tracing |
| Testing | pytest + pytest-asyncio | Standard Python testing |
| Containerization | Docker + Docker Compose | Reproducible deployment |

### LangChain Provider Abstraction Strategy

The system uses LangChain as the **universal LLM/embedding abstraction layer**. All LLM and embedding calls go through LangChain interfaces, never directly to provider SDKs. This enables:

- **Hot-swapping LLM providers** by changing a config value (no code changes)
- **Future provider support**: OpenAI, Anthropic, Azure OpenAI, Cohere, Ollama (local), HuggingFace, etc.
- **Unified callback system** for logging, token tracking, and cost monitoring across any provider
- **Consistent retry/fallback** logic regardless of underlying provider

```python
# Example: Provider swap via config — zero code changes
# config.yaml
llm:
  provider: "google_genai"        # Change to "openai", "anthropic", "ollama", etc.
  model: "gemini-1.5-pro"         # Change to "gpt-4o", "claude-3.5-sonnet", etc.
  temperature: 0.0
  max_tokens: 4096

embeddings:
  provider: "google_genai"        # Change to "openai", "huggingface", etc.
  model: "text-embedding-004"     # Change to "text-embedding-3-large", etc.

# src/llm/factory.py — LLM factory pattern
def get_llm(config) -> BaseChatModel:
    match config.llm.provider:
        case "google_genai":
            return ChatGoogleGenerativeAI(model=config.llm.model, ...)
        case "openai":
            return ChatOpenAI(model=config.llm.model, ...)
        case "anthropic":
            return ChatAnthropic(model=config.llm.model, ...)
        case "ollama":
            return ChatOllama(model=config.llm.model, ...)

def get_embeddings(config) -> Embeddings:
    match config.embeddings.provider:
        case "google_genai":
            return GoogleGenerativeAIEmbeddings(model=config.embeddings.model)
        case "openai":
            return OpenAIEmbeddings(model=config.embeddings.model)
        case "huggingface":
            return HuggingFaceEmbeddings(model_name=config.embeddings.model)
```

### LangChain Packages Required

| Package | Purpose |
|---|---|
| `langchain-core` | Base abstractions (BaseChatModel, Embeddings, Runnables, LCEL) |
| `langchain` | Chains, output parsers, text splitters, callbacks |
| `langchain-google-genai` | Gemini LLM + Embedding integration (default provider) |
| `langchain-chroma` | ChromaDB vector store wrapper |
| `langchain-openai` | *(Optional, install when needed)* OpenAI/Azure OpenAI support |
| `langchain-anthropic` | *(Optional, install when needed)* Anthropic Claude support |
| `langchain-community` | *(Optional)* Ollama, HuggingFace, and other community providers |

---

## 3. Phase 0 — Project Setup and Foundation

**Duration:** 3–4 days
**Goal:** Establish project structure, development environment, and core configuration.

### Tasks

| # | Task | Details | Output |
|---|---|---|---|
| 0.1 | Initialize repository | Git init, `.gitignore`, branch strategy (main/develop/feature) | Git repo |
| 0.2 | Create project structure | Monorepo with service modules | Directory tree |
| 0.3 | Setup virtual environment | Python 3.11+, `pyproject.toml` or `requirements.txt` | venv with pinned deps |
| 0.4 | Configure linting and formatting | Ruff, Black, mypy | Pre-commit hooks |
| 0.5 | Create configuration management | Pydantic Settings for env vars, API keys, paths, **LLM provider config** | `config.py` |
| 0.6 | Setup logging framework | structlog with JSON output, log levels, **LangChain callback handler** | `logger.py` |
| 0.6a | Setup LangChain LLM abstraction layer | LLM factory, embedding factory, provider config — **ensure all AI calls go through LangChain** | `src/llm/factory.py` |
| 0.7 | Create DQC checklist schema | JSON Schema for checklist items | `dqc_schema.json` |
| 0.8 | Seed sample DQC checklist | 10–15 checklist items for testing | `sample_dqc.json` |
| 0.9 | Collect test documents | 3–5 sample PDFs, DOCX, PPTX, XLSX | `tests/fixtures/` |

### Project Structure

```
LRA/
├── src/
│   ├── __init__.py
│   ├── config.py                  # Central configuration
│   ├── llm/                       # LangChain LLM abstraction layer
│   │   ├── __init__.py
│   │   ├── factory.py             # LLM + Embedding provider factory
│   │   ├── callbacks.py           # Custom LangChain callbacks (logging, token tracking)
│   │   └── providers.py           # Provider-specific config and initialization
│   ├── models/                    # Pydantic data models
│   │   ├── __init__.py
│   │   ├── document.py
│   │   ├── chunk.py
│   │   ├── dqc.py
│   │   └── report.py
│   ├── ingestion/                 # Phase 1: Document ingestion
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py
│   │   ├── docx_extractor.py
│   │   ├── pptx_extractor.py
│   │   ├── xlsx_extractor.py
│   │   └── extractor_factory.py
│   ├── preprocessing/             # Phase 2: Chunking
│   │   ├── __init__.py
│   │   ├── chunker.py
│   │   └── metadata_tagger.py
│   ├── vectorstore/               # Phase 3: Embeddings + storage (via LangChain Chroma)
│   │   ├── __init__.py
│   │   ├── embedder.py            # Uses LangChain Embeddings interface
│   │   └── chroma_store.py        # Uses LangChain Chroma wrapper
│   ├── retrieval/                 # Phase 4: Retrieval engine
│   │   ├── __init__.py
│   │   ├── retriever.py           # Uses LangChain VectorStoreRetriever
│   │   └── reranker.py
│   ├── evaluation/                # Phase 5: DQC evaluation (via LangChain chains)
│   │   ├── __init__.py
│   │   ├── dqc_engine.py          # Uses LangChain LCEL chains + ChatModel
│   │   ├── prompt_templates.py    # Uses LangChain PromptTemplate / ChatPromptTemplate
│   │   ├── output_parsers.py      # LangChain PydanticOutputParser for structured output
│   │   └── schema_validator.py
│   ├── orchestration/             # Phase 6: Workflow orchestrator
│   │   ├── __init__.py
│   │   └── orchestrator.py
│   ├── reporting/                 # Phase 7: Report generation
│   │   ├── __init__.py
│   │   ├── json_reporter.py
│   │   ├── pdf_reporter.py
│   │   └── templates/
│   ├── audit/                     # Phase 8: Audit logging
│   │   ├── __init__.py
│   │   └── audit_logger.py
│   ├── api/                       # Phase 9: API layer
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── documents.py
│   │   │   ├── analysis.py
│   │   │   ├── reports.py
│   │   │   └── admin.py
│   │   └── middleware/
│   │       ├── auth.py
│   │       └── error_handler.py
│   └── frontend/                  # Phase 9: Streamlit UI
│       └── app.py
├── data/
│   ├── dqc/                       # DQC checklist files
│   ├── vectordb/                  # ChromaDB persistent storage
│   ├── uploads/                   # Uploaded documents
│   └── reports/                   # Generated reports
├── tests/
│   ├── fixtures/                  # Test documents
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

### Acceptance Criteria

- [ ] `python -m src.config` loads config without errors
- [ ] Logging outputs structured JSON to stdout
- [ ] DQC schema validates sample checklist
- [ ] All test fixtures accessible
- [ ] LangChain LLM factory returns working `ChatGoogleGenerativeAI` instance
- [ ] LangChain Embedding factory returns working `GoogleGenerativeAIEmbeddings` instance
- [ ] Provider swap test: config change → different LLM class instantiated (mock test)

---

## 4. Phase 1 — Document Ingestion Pipeline

**Duration:** 5–6 days
**Goal:** Extract structured text and metadata from all four document formats.
**Depends on:** Phase 0

### Tasks

| # | Task | Details |
|---|---|---|
| 1.1 | Define `Document` and `ExtractedContent` Pydantic models | Fields: doc_id, filename, format, upload_timestamp, pages[], sections[], raw_text, metadata |
| 1.2 | Implement PDF extractor | PyMuPDF: extract text per page, detect headings, handle images-as-text (OCR flag) |
| 1.3 | Implement DOCX extractor | python-docx: extract paragraphs, heading styles → section hierarchy, tables |
| 1.4 | Implement PPTX extractor | python-pptx: extract text per slide, speaker notes, slide titles as sections |
| 1.5 | Implement XLSX extractor | openpyxl: extract sheet names, cell data, detect header rows |
| 1.6 | Build extractor factory | Route file to correct extractor based on MIME type / extension |
| 1.7 | Implement corruption detection | Try-catch extraction, validate minimum text yield, file size checks |
| 1.8 | Implement document versioning | SHA-256 hash-based dedup, version counter per filename |
| 1.9 | Write unit tests | One test per format, edge cases (empty doc, password-protected, large file) |

### Key Design Decisions

- **Section hierarchy**: Use heading levels (H1/H2/H3) for PDF/DOCX, slide numbers for PPTX, sheet names for XLSX
- **Metadata extraction**: Always capture page count, word count, creation date, author if available
- **Error handling**: Return partial extraction result + error log rather than failing entirely

### Acceptance Criteria

- [ ] All 4 formats extract text with > 95% fidelity on test docs
- [ ] Section hierarchy correctly identified for structured documents
- [ ] Corrupted file returns graceful error, not crash
- [ ] Document version stored with hash

---

## 5. Phase 2 — Preprocessing and Chunking

**Duration:** 4–5 days
**Goal:** Split extracted content into optimally-sized, metadata-tagged chunks.
**Depends on:** Phase 1

### Tasks

| # | Task | Details |
|---|---|---|
| 2.1 | Define `Chunk` Pydantic model | Fields: chunk_id, doc_id, text, section_name, page_number, chunk_index, token_count, metadata |
| 2.2 | Implement section-aware splitter | Split on detected section boundaries first, then apply size-based splitting within sections |
| 2.3 | Implement semantic boundary detection | Use sentence boundaries + paragraph breaks to avoid mid-sentence splits |
| 2.4 | Implement token counter | Use `tiktoken` or Gemini tokenizer to count tokens per chunk |
| 2.5 | Configure chunk size strategy | Target: 512–1024 tokens per chunk, 10–15% overlap between consecutive chunks |
| 2.6 | Implement metadata tagger | Auto-tag each chunk with: section_name, page_number, doc_id, upload_timestamp, chunk_index |
| 2.7 | Handle edge cases | Very short sections (< 50 tokens) → merge with adjacent; tables → keep as single chunk |
| 2.8 | Write unit tests | Verify chunk sizes, overlap, metadata accuracy, section boundary respect |

### Chunking Strategy

```
Document
  ├─ Section 1 (H1: "Introduction")
  │    ├─ Chunk 1 [tokens: 800, page: 1-2, section: "Introduction"]
  │    └─ Chunk 2 [tokens: 650, page: 2-3, section: "Introduction"]
  ├─ Section 2 (H1: "Learning Objectives")
  │    └─ Chunk 3 [tokens: 420, page: 3, section: "Learning Objectives"]
  └─ Section 3 (H1: "Module Content")
       ├─ Chunk 4 [tokens: 950, page: 4-6, section: "Module Content"]
       ├─ Chunk 5 [tokens: 880, page: 6-8, section: "Module Content"]
       └─ Chunk 6 [tokens: 500, page: 8-9, section: "Module Content"]
```

### Acceptance Criteria

- [ ] No chunk exceeds 1024 tokens
- [ ] Every chunk has complete metadata fields
- [ ] Section boundaries are respected (no cross-section chunks unless section is tiny)
- [ ] Overlap between consecutive chunks is 10–15%

---

## 6. Phase 3 — Embedding and Vector Storage

**Duration:** 4–5 days
**Goal:** Generate embeddings and store in local ChromaDB with full metadata.
**Depends on:** Phase 2

### Tasks

| # | Task | Details |
|---|---|---|
| 3.1 | Setup embedding client via LangChain | Use `get_embeddings()` factory → `GoogleGenerativeAIEmbeddings` (default), swappable to OpenAI/HuggingFace via config |
| 3.2 | Implement batch embedding | Use LangChain `embeddings.embed_documents()` in batches of 50–100, retry on rate limit |
| 3.3 | Setup ChromaDB via LangChain Chroma wrapper | `Chroma.from_documents()` with local file-based persistence at `data/vectordb/` |
| 3.4 | Design collection schema | Collection per document or single collection with doc_id filter |
| 3.5 | Implement upsert logic | Insert new chunks, update existing (by chunk_id), delete stale |
| 3.6 | Implement re-index capability | Full re-embed and replace when DQC changes or embedding model updates |
| 3.7 | Add embedding versioning | Store embedding model name + version in metadata |
| 3.8 | Performance optimization | Connection pooling, batch writes, async embedding calls |
| 3.9 | Write integration tests | Verify round-trip: chunk → embed → store → retrieve by ID |

### ChromaDB Collection Design

```
Collection: "lra_documents"
  - id: chunk_id (UUID)
  - embedding: float[768]  (Gemini embedding dimension)
  - document: chunk_text
  - metadata:
      doc_id: str
      section_name: str
      page_number: int
      chunk_index: int
      upload_timestamp: str
      embedding_model: str
      embedding_version: str
```

### Acceptance Criteria

- [ ] 100 chunks embedded and stored in < 30 seconds
- [ ] Metadata queryable via ChromaDB filters
- [ ] Re-index replaces all embeddings without duplicates
- [ ] Embedding version tracked in metadata

---

## 7. Phase 4 — Retrieval Engine

**Duration:** 4–5 days
**Goal:** Retrieve the most relevant chunks for each DQC checklist item.
**Depends on:** Phase 3

### Tasks

| # | Task | Details |
|---|---|---|
| 4.1 | Implement top-k semantic search | Use LangChain `VectorStoreRetriever` with `search_kwargs={"k": 10}` — provider-agnostic retrieval |
| 4.2 | Implement metadata filtering | Use LangChain `Chroma` filter parameter: `filter={"doc_id": id}` |
| 4.3 | Implement section reconstruction | Group retrieved `Document` objects by section metadata, reconstruct context |
| 4.4 | Implement re-ranking (optional) | Use LangChain `ContextualCompressionRetriever` with LLM-based re-ranker (swappable) |
| 4.5 | Context window optimizer | Calculate total tokens, trim/prioritize to fit Gemini context window |
| 4.6 | Implement retrieval result model | `RetrievalResult`: query, chunks[], scores[], total_tokens |
| 4.7 | Configure retrieval parameters | k, similarity threshold, max_tokens_per_query — externalized config |
| 4.8 | Write tests | Measure retrieval relevance on known test documents |

### Retrieval Flow

```
DQC Item: "Course must have clearly stated learning objectives"
    │
    ▼
Embed query text
    │
    ▼
ChromaDB similarity search (top-k=10)
    │
    ▼
Filter by document ID
    │
    ▼
Group by section
    │
    ▼
[Optional] Re-rank via Gemini
    │
    ▼
Assemble context (trim to token budget)
    │
    ▼
Return RetrievalResult
```

### Acceptance Criteria

- [ ] Retrieval returns relevant chunks for 90%+ of test DQC items
- [ ] Context fits within token budget (configurable, default 30K tokens)
- [ ] Section reconstruction preserves reading order
- [ ] Filtering by doc_id works correctly

---

## 8. Phase 5 — DQC Evaluation Engine

**Duration:** 7–8 days
**Goal:** Use Gemini to evaluate each DQC item against retrieved content and produce structured results.
**Depends on:** Phase 4

> **⚠️ CRITICAL VALIDATION GATE**: This phase determines if the core AI approach is viable. Conduct a quality review after implementation before proceeding.

### Tasks

| # | Task | Details |
|---|---|---|
| 5.1 | Design prompt templates | Use LangChain `ChatPromptTemplate` with system/human message structure, few-shot `FewShotChatMessagePromptTemplate` |
| 5.2 | Define output schema + parser | Pydantic model → LangChain `PydanticOutputParser` for type-safe structured output with format instructions |
| 5.3 | Implement single-item evaluation chain | LCEL chain: `prompt | llm | output_parser` — fully provider-agnostic, one DQC item + context → validated Pydantic result |
| 5.4 | Implement output parsing with auto-retry | LangChain `OutputFixingParser` wrapping `PydanticOutputParser` — auto-retry on malformed output using the LLM itself |
| 5.5 | Implement confidence scoring | Map Gemini confidence signals to 0.0–1.0 score |
| 5.6 | Implement risk level calculator | Rule-based: Fail + High confidence = Critical, Partial = Medium, etc. |
| 5.7 | Build aggregation logic | Combine all item results → overall compliance score, risk distribution |
| 5.8 | Implement retry with backoff | LangChain `.with_retry()` on chains for rate limits + `OutputFixingParser` for structured output retries (max 3) |
| 5.9 | Prompt versioning | Store prompt templates with version IDs, log which version was used |
| 5.10 | Quality validation | Run against 5 test documents, compare with manual review, measure accuracy |

### Prompt Template Design

```
SYSTEM PROMPT:
You are a Learning Content Quality Compliance Analyst. You evaluate educational
materials against a Data Quality Checklist (DQC). You must:
1. Base your evaluation ONLY on the provided content
2. Return structured JSON matching the exact schema
3. Provide specific evidence from the content for your findings
4. Never fabricate or assume content not present in the provided context

EVALUATION PROMPT:
## DQC Item
- ID: {dqc_item_id}
- Category: {category}
- Requirement: {requirement_text}
- Evaluation Criteria: {criteria}

## Document Content (Retrieved Sections)
{retrieved_context}

## Instructions
Evaluate whether the document content satisfies the above DQC requirement.
Return your evaluation in the following JSON format:

{
  "dqc_item_id": "{dqc_item_id}",
  "status": "Pass | Fail | Partial",
  "justification": "Detailed explanation with evidence from the content",
  "evidence_quotes": ["Direct quotes from content supporting the finding"],
  "risk_level": "Critical | High | Medium | Low",
  "recommendation": "Specific actionable recommendation if not Pass",
  "confidence_score": 0.0 to 1.0,
  "sections_reviewed": ["List of section names evaluated"]
}
```

### Risk Scoring Matrix

| Status | Confidence ≥ 0.8 | Confidence 0.5–0.8 | Confidence < 0.5 |
|---|---|---|---|
| Fail | Critical | High | Medium (flag for review) |
| Partial | High | Medium | Low (flag for review) |
| Pass | — | — | Low (flag for review) |

### Acceptance Criteria

- [ ] 95%+ of outputs are valid JSON matching schema
- [ ] Justifications reference actual content (no hallucination)
- [ ] Risk levels align with matrix above
- [ ] Accuracy within 5% of senior reviewer on test set
- [ ] **Quality gate passed — team sign-off before proceeding**

---

## 9. Phase 6 — Orchestration Layer

**Duration:** 5–6 days
**Goal:** Wire all components into an end-to-end automated pipeline.
**Depends on:** Phase 5

### Tasks

| # | Task | Details |
|---|---|---|
| 6.1 | Define pipeline state model | `PipelineState`: document_id, stage, progress, results, errors, timestamps |
| 6.2 | Implement pipeline orchestrator | Sequential: ingest → chunk → embed → [for each DQC item: retrieve → evaluate via LangChain chain] → aggregate → report |
| 6.3 | Implement parallel DQC evaluation | Use LangChain `RunnableParallel` / `chain.abatch()` to evaluate multiple DQC items concurrently (rate-limit aware) |
| 6.4 | Implement retry logic | Per-stage retry with configurable max attempts |
| 6.5 | Implement state persistence | Save pipeline state to disk/DB at each stage for recovery |
| 6.6 | Implement progress tracking | Emit progress events: 0% → ingestion → 20% → chunking → 30% → … → 100% |
| 6.7 | Implement error handling | Classify errors (retriable vs fatal), partial completion support |
| 6.8 | Add token usage tracking | Use LangChain callback handler to accumulate token usage across all LLM calls (provider-agnostic) |
| 6.9 | Write integration test | End-to-end: upload PDF → get JSON report |

### Pipeline Stages

```
Stage 1: INGESTION        [0-15%]   Extract text from document
Stage 2: PREPROCESSING    [15-25%]  Chunk and tag metadata
Stage 3: EMBEDDING        [25-40%]  Generate embeddings, store in ChromaDB
Stage 4: EVALUATION       [40-85%]  For each DQC item:
           ├─ Retrieve relevant chunks
           ├─ Send to LLM via LangChain evaluation chain
           └─ Validate and store result
Stage 5: AGGREGATION      [85-90%]  Combine results, calculate scores
Stage 6: REPORTING        [90-100%] Generate JSON + PDF report
```

### Acceptance Criteria

- [ ] Full pipeline runs end-to-end on a test document
- [ ] Pipeline state recoverable after crash (resume from last completed stage)
- [ ] Token usage tracked and logged
- [ ] 150-page document processed in < 3 minutes
- [ ] Errors logged with classification

---

## 10. Phase 7 — Reporting Module

**Duration:** 5–6 days
**Goal:** Generate structured JSON and human-readable PDF/DOCX reports.
**Depends on:** Phase 6

### Tasks

| # | Task | Details |
|---|---|---|
| 7.1 | Define report JSON schema | Complete schema with all sections from PRD 5.7 |
| 7.2 | Implement JSON report generator | Aggregate evaluation results into structured JSON |
| 7.3 | Design PDF report template | Layout: cover page, executive summary, score card, detailed findings, appendix |
| 7.4 | Implement PDF generator | ReportLab: render styled report from evaluation data |
| 7.5 | Implement risk heatmap | Visual matrix: DQC items × risk levels, color-coded |
| 7.6 | Implement executive summary generator | Use LangChain summarization chain (`prompt | llm | StrOutputParser`) to generate 3-5 sentence summary from aggregated findings |
| 7.7 | Implement recommendations section | Prioritized list of actionable items sorted by risk |
| 7.8 | Add audit metadata to report | Embed model version, prompt version, DQC version, timestamps |
| 7.9 | Write tests | Validate JSON against schema, verify PDF renders correctly |

### Report JSON Structure

```json
{
  "report_id": "uuid",
  "generated_at": "ISO-8601",
  "document": {
    "id": "uuid",
    "filename": "course_module_1.pdf",
    "pages": 120,
    "version": 2
  },
  "dqc_version": "1.3",
  "overall_compliance": {
    "score": 78.5,
    "total_items": 15,
    "passed": 10,
    "failed": 3,
    "partial": 2,
    "risk_distribution": {
      "critical": 1,
      "high": 2,
      "medium": 3,
      "low": 9
    }
  },
  "executive_summary": "The document demonstrates strong compliance...",
  "findings": [
    {
      "dqc_item_id": "DQC-001",
      "requirement": "...",
      "status": "Pass",
      "justification": "...",
      "evidence_quotes": [],
      "risk_level": "Low",
      "recommendation": null,
      "confidence_score": 0.92,
      "sections_reviewed": ["Introduction", "Objectives"]
    }
  ],
  "recommendations": [
    {
      "priority": 1,
      "dqc_item_id": "DQC-007",
      "action": "Add explicit assessment criteria for each learning objective",
      "risk_impact": "Critical"
    }
  ],
  "audit": {
    "model_version": "gemini-1.5-pro-002",
    "embedding_model": "text-embedding-004",
    "prompt_version": "v1.2",
    "dqc_version": "1.3",
    "total_tokens_used": 145230,
    "processing_time_seconds": 127,
    "user": "reviewer@org.com"
  }
}
```

### Acceptance Criteria

- [ ] JSON report validates against schema
- [ ] PDF report renders all 6 required sections
- [ ] Risk heatmap visually accurate
- [ ] Executive summary is coherent and grounded
- [ ] Report file stored with unique ID

---

## 11. Phase 8 — Audit and Traceability

**Duration:** 3–4 days
**Goal:** Implement comprehensive audit logging for every evaluation.
**Depends on:** Phase 6

### Tasks

| # | Task | Details |
|---|---|---|
| 8.1 | Design audit log schema | SQLite table: evaluation_id, doc_id, dqc_item_id, prompt_version, model_version, embedding_version, dqc_version, timestamp, user_id, retrieved_chunk_ids, result_json |
| 8.2 | Implement audit logger | Write audit record at each evaluation step |
| 8.3 | Implement chunk provenance | Log which chunks were retrieved and used for each DQC evaluation |
| 8.4 | Implement prompt version tracking | Store prompt template hash + version |
| 8.5 | Build audit query API | Query by document, date range, DQC item, user |
| 8.6 | Write tests | Verify complete audit trail for a full pipeline run |

### Audit Log Fields

| Field | Type | Description |
|---|---|---|
| audit_id | UUID | Unique audit record ID |
| evaluation_id | UUID | Links to specific pipeline run |
| doc_id | UUID | Document evaluated |
| dqc_item_id | String | Checklist item ID |
| prompt_version | String | Hash/version of prompt template used |
| model_version | String | e.g., "gemini-1.5-pro-002" |
| embedding_model_version | String | e.g., "text-embedding-004" |
| dqc_version | String | Version of DQC checklist |
| retrieved_chunk_ids | JSON Array | IDs of chunks sent to Gemini |
| result_snapshot | JSON | Full evaluation result |
| token_usage | JSON | {input_tokens, output_tokens} |
| timestamp | ISO-8601 | When evaluation occurred |
| user_id | String | Who initiated the analysis |

### Acceptance Criteria

- [ ] Every Gemini call has an audit record
- [ ] Chunk provenance traceable per evaluation
- [ ] Audit records queryable by all key fields
- [ ] No audit gaps in full pipeline run

---

## 12. Phase 9 — Frontend and API Layer

**Duration:** 7–8 days
**Goal:** Build the API and user interface for document upload, analysis, and report viewing.
**Depends on:** Phase 7, Phase 8

### Tasks

| # | Task | Details |
|---|---|---|
| 9.1 | Design REST API endpoints | See endpoint table below |
| 9.2 | Implement FastAPI application | Main app with CORS, error handling, request validation |
| 9.3 | Implement document upload endpoint | Multipart file upload with validation |
| 9.4 | Implement analysis trigger endpoint | Start pipeline, return job ID |
| 9.5 | Implement status polling endpoint | Return pipeline progress and stage |
| 9.6 | Implement report retrieval endpoints | Get JSON report, download PDF |
| 9.7 | Implement Streamlit frontend | Upload page, analysis progress, report viewer |
| 9.8 | Add WebSocket for progress | Real-time pipeline progress updates |
| 9.9 | Implement basic auth | API key-based authentication for MVP |
| 9.10 | Write API integration tests | Test all endpoints with fixtures |

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/documents/upload` | Upload a document |
| GET | `/api/v1/documents` | List uploaded documents |
| GET | `/api/v1/documents/{id}` | Get document metadata |
| POST | `/api/v1/analysis/start` | Start DQC analysis |
| GET | `/api/v1/analysis/{id}/status` | Get analysis progress |
| GET | `/api/v1/analysis/{id}/result` | Get analysis JSON result |
| GET | `/api/v1/reports/{id}/json` | Download JSON report |
| GET | `/api/v1/reports/{id}/pdf` | Download PDF report |
| GET | `/api/v1/audit/{evaluation_id}` | Get audit trail |
| WS | `/ws/analysis/{id}/progress` | Real-time progress |

### Streamlit UI Pages

1. **Dashboard** — Recent analyses, quick stats
2. **Upload** — Drag-and-drop document upload
3. **Analysis** — Select document + DQC, start analysis, view progress
4. **Report Viewer** — Interactive compliance report with drill-down
5. **Audit Log** — Searchable audit history

### Acceptance Criteria

- [ ] All API endpoints functional and documented (auto-generated FastAPI docs)
- [ ] File upload handles all 4 formats
- [ ] Analysis runs asynchronously, status trackable
- [ ] Streamlit UI usable for full workflow
- [ ] Basic auth protects all endpoints

---

## 13. Phase 10 — Admin Features

**Duration:** 4–5 days
**Goal:** Enable DQC management, historical reports, and document version comparison.
**Depends on:** Phase 9

### Tasks

| # | Task | Details |
|---|---|---|
| 10.1 | DQC checklist CRUD | Upload, edit, version, activate/deactivate DQC checklists |
| 10.2 | DQC version management | Immutable versions, track which version was used per analysis |
| 10.3 | Historical report viewer | Browse and search past reports by document, date, score |
| 10.4 | Document version comparison | Side-by-side compliance diff between document versions |
| 10.5 | Re-run analysis | Trigger new analysis on existing document with different DQC version |
| 10.6 | Admin UI pages | DQC Manager, Report History, Version Comparator |
| 10.7 | Write tests | CRUD operations, version immutability, comparison logic |

### Acceptance Criteria

- [ ] DQC checklist uploadable and versionable via UI
- [ ] Historical reports browsable and searchable
- [ ] Document version comparison shows compliance delta
- [ ] Re-run produces new report with new DQC version logged

---

## 14. Phase 11 — Testing, Hardening, and Performance

**Duration:** 5–6 days
**Goal:** Comprehensive testing, performance optimization, and production hardening.
**Depends on:** Phase 10

### Tasks

| # | Task | Details |
|---|---|---|
| 11.1 | Unit test coverage | Target 80%+ coverage on all service modules |
| 11.2 | Integration tests | Full pipeline tests with various document types |
| 11.3 | Performance benchmark | 150-page document < 3 minutes, profile bottlenecks |
| 11.4 | Concurrent load test | 5–10 simultaneous analyses (MVP target) |
| 11.5 | Error injection testing | Network failures, Gemini rate limits, corrupted files |
| 11.6 | Security hardening | Input sanitization, API key rotation, file type validation |
| 11.7 | Structured logging review | Verify all key operations logged with context |
| 11.8 | Token usage optimization | Reduce unnecessary token usage without losing quality |
| 11.9 | Memory profiling | Ensure no leaks on repeated runs |
| 11.10 | Documentation | README, API docs, deployment guide, architecture docs |

### Performance Budget

| Operation | Target | Measurement |
|---|---|---|
| Document ingestion (150 pages) | < 10 seconds | Time from upload to text extracted |
| Chunking + embedding | < 30 seconds | Time for chunk + embed + store |
| Full DQC evaluation (15 items) | < 120 seconds | All Gemini calls completed |
| Report generation | < 10 seconds | JSON + PDF generated |
| **Total pipeline** | **< 180 seconds** | End-to-end |

### Acceptance Criteria

- [ ] All tests pass (unit + integration + e2e)
- [ ] Performance targets met
- [ ] No critical security vulnerabilities
- [ ] Documentation complete

---

## 15. Phase 12 — Deployment and Release

**Duration:** 3–4 days
**Goal:** Package and deploy the system for local / on-prem usage.
**Depends on:** Phase 11

### Tasks

| # | Task | Details |
|---|---|---|
| 12.1 | Create Dockerfile | Multi-stage build, minimal image |
| 12.2 | Create docker-compose.yml | API + Frontend + ChromaDB volumes |
| 12.3 | Environment configuration | `.env` template with all required variables |
| 12.4 | Data volume management | Persistent volumes for vectordb, uploads, reports |
| 12.5 | Health check endpoints | `/health`, `/ready` with dependency checks |
| 12.6 | Startup / shutdown hooks | Graceful shutdown, DB connection cleanup |
| 12.7 | Deployment documentation | Step-by-step local deployment guide |
| 12.8 | Smoke test suite | Automated post-deployment validation |
| 12.9 | Release tagging | Semantic versioning, changelog |

### Docker Compose Architecture

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
    env_file: .env

  frontend:
    build:
      context: .
      dockerfile: docker/Dockerfile.frontend
    ports: ["8501:8501"]
    depends_on: [api]

volumes:
  data:
    driver: local
```

### Acceptance Criteria

- [ ] `docker-compose up` launches full system
- [ ] Health checks pass
- [ ] Smoke tests pass on fresh deployment
- [ ] Persistent data survives container restart
- [ ] Deployment guide tested by non-developer

---

## 16. Timeline Summary

| Phase | Name | Duration | Cumulative |
|---|---|---|---|
| 0 | Project Setup | 3–4 days | Week 1 |
| 1 | Document Ingestion | 5–6 days | Week 1–2 |
| 2 | Preprocessing & Chunking | 4–5 days | Week 2–3 |
| 3 | Embedding & Vector Storage | 4–5 days | Week 3–4 |
| 4 | Retrieval Engine | 4–5 days | Week 4–5 |
| 5 | DQC Evaluation Engine ⚠️ | 7–8 days | Week 5–6 |
| — | **Quality Gate Review** | 1–2 days | **Week 7** |
| 6 | Orchestration Layer | 5–6 days | Week 7–8 |
| 7 | Reporting Module | 5–6 days | Week 8–9 |
| 8 | Audit & Traceability | 3–4 days | Week 9–10 |
| 9 | Frontend & API | 7–8 days | Week 10–12 |
| 10 | Admin Features | 4–5 days | Week 12–13 |
| 11 | Testing & Hardening | 5–6 days | Week 13–14 |
| 12 | Deployment & Release | 3–4 days | Week 15–16 |
| | **Total MVP** | | **14–16 weeks** |

### Milestone Checkpoints

| Milestone | Week | Deliverable |
|---|---|---|
| M1: Core Pipeline | Week 5 | Ingest → chunk → embed → retrieve (CLI test) |
| M2: AI Validation Gate | Week 7 | DQC evaluation accuracy validated |
| M3: Full Pipeline | Week 10 | End-to-end: upload → report (no UI) |
| M4: UI Complete | Week 13 | Streamlit UI + API fully functional |
| M5: MVP Release | Week 16 | Dockerized, tested, documented |

---

## 17. Risk Register and Contingency

| # | Risk | Probability | Impact | Mitigation | Contingency |
|---|---|---|---|---|---|
| R1 | Gemini output inconsistency | Medium | High | Few-shot prompting, JSON schema enforcement, retry | Fall back to structured extraction prompts, reduce DQC complexity |
| R2 | Embedding quality insufficient | Low | High | Test with known-good document pairs | **Hot-swap to OpenAI/Cohere embeddings via LangChain config change — no code modifications needed** |
| R3 | Token costs exceed budget | Medium | Medium | Token tracking via LangChain callbacks, context window optimization | Reduce chunk overlap, limit top-k, **swap to cheaper model via config (e.g., Gemini Flash, GPT-4o-mini)** |
| R4 | 3-minute SLA not achievable | Medium | Medium | Profile early, async evaluation | Accept 5-minute SLA for > 200 pages, add caching |
| R5 | ChromaDB scaling limits | Low | Medium | Monitor collection sizes | Migrate to Qdrant or Weaviate (same API pattern) |
| R6 | PDF extraction quality varies | High | Medium | Test with diverse PDFs early | Add OCR fallback (Tesseract), manual section tagging |
| R7 | Scope creep from stakeholders | Medium | High | Strict MVP scope, phase gates | Defer to post-MVP backlog |

---

## 18. Definition of Done per Phase

Every phase is considered **done** when:

1. ✅ All tasks in the phase are implemented
2. ✅ Unit tests written and passing (80%+ coverage for the module)
3. ✅ Integration test with upstream dependency passing
4. ✅ Code reviewed (self-review for solo dev, PR review for team)
5. ✅ No critical or high-severity bugs open
6. ✅ Structured logging implemented for the module
7. ✅ Acceptance criteria checklist completed
8. ✅ Brief technical documentation updated

---

> **Next Steps:** Begin Phase 0 — set up the repository, install dependencies, and create the project structure.
