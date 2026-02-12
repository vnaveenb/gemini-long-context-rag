# LRA — Learning Content Compliance Intelligence System

RAG-based Data Quality Checklist (DQC) validation for learning course materials using **Gemini** and **ChromaDB**.

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Gemini API key ([get one here](https://aistudio.google.com))

### 2. Setup

```bash
# Clone and enter
cd LRA

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e ".[dev]"

# Configure environment
copy .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 3. Run the API

```bash
uvicorn src.api.main:app --reload --port 8000
```

API docs at: http://localhost:8000/docs

### 4. Run the Frontend

```bash
streamlit run src/frontend/app.py
```

UI at: http://localhost:8501

### 5. Run via CLI (no server needed)

```python
from src.orchestration.orchestrator import Pipeline

pipeline = Pipeline()
report = pipeline.run(
    file_path="path/to/your/document.pdf",
    user="your_name",
)
print(f"Score: {report.overall_compliance.score}%")
```

## Architecture

```
Upload → Extract → Chunk → Embed → Store → Retrieve → Evaluate → Report
  │         │        │       │        │        │          │          │
  │    PDF/DOCX  Section  Gemini  ChromaDB  Top-k    LangChain   JSON
  │    PPTX/XLSX  aware   embed            semantic   LCEL +     + PDF
  │              chunker   -001            search     Gemini
```

### LLM Provider Swapping

Change provider in `.env` — zero code changes:

```env
# Gemini (default)
LLM_PROVIDER=google_genai
LLM_MODEL=gemini-2.5-flash

# OpenAI
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4o

# Anthropic
# LLM_PROVIDER=anthropic
# LLM_MODEL=claude-3.5-sonnet

# Local (Ollama)
# LLM_PROVIDER=ollama
# LLM_MODEL=llama3
```

## Project Structure

```
src/
├── config.py              # Central configuration
├── llm/                   # LangChain LLM abstraction (factory + callbacks)
├── models/                # Pydantic data models
├── ingestion/             # PDF/DOCX/PPTX/XLSX extractors
├── preprocessing/         # Section-aware chunking
├── vectorstore/           # ChromaDB via LangChain
├── retrieval/             # Semantic search + context assembly
├── evaluation/            # DQC engine (LCEL chains + output parsers)
├── orchestration/         # End-to-end pipeline
├── reporting/             # JSON + PDF report generation
├── audit/                 # SQLite audit trail
├── api/                   # FastAPI backend
└── frontend/              # Streamlit UI
```

## Docker

```bash
cd docker
docker-compose up --build
```

- API: http://localhost:8000
- UI: http://localhost:8501

## License

Internal use only.
