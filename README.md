## WCAG Accessibility Audit Agent

### Overview

The **WCAG Accessibility Audit Agent** is an AI‑assisted CLI tool that crawls a website, collects rich accessibility data, and generates WCAG‑aligned findings and reports.  
It combines automated checks (axe‑core, keyboard navigation recording, DOM analysis) with AI agents and an optional RAG (Retrieval‑Augmented Generation) knowledge base built from WCAG 2.2 documentation to produce human‑readable summaries, prioritized fixes, and PDF/JSON reports.

The pipeline is designed to be run locally from the command line and can optionally integrate with Vertex AI (Gemini), Pinecone, and downstream APIs or databases.

### Technologies

- **Language / Runtime**: Python 3.10+
- **Crawling & Browser Automation**: `playwright`
- **Accessibility Scanning**: `axe-playwright-python`
- **HTML Parsing**: `beautifulsoup4`, `lxml`
- **AI / LLM**:
  - Google Gemini via `google-genai`
  - Orchestration with `langchain` and `langgraph`
- **Vector Search (RAG, optional)**: Pinecone (`pinecone-client`, `langchain-pinecone`)
- **Reporting**: `weasyprint`, `Jinja2`, `Pillow`
- **API / Backend (optional, later stages)**: `fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg`, `psycopg2-binary`
- **Cloud Integrations (optional)**:
  - Google Cloud Vertex AI & Storage (`google-cloud-storage`, `google-cloud-tasks`)
- **Config & Utilities**: `python-dotenv`, `pydantic`, `pydantic-settings`, `loguru`, `httpx`, `aiofiles`

---

## Prerequisites

- **Python**: 3.8 or higher (3.10+ recommended)
- **pip**: Python package manager
- **Git**: For cloning the repository
- **Playwright browsers**: Installed via `playwright install` (see below)
- **(For AI & RAG)**:
  - Google Cloud project with Vertex AI / Gemini access
  - Service account JSON credentials
  - Pinecone account and API key (if you want RAG enrichment)

---

## Project Structure (High Level)

- **`run_audit.py`**: Quick start for **Steps 1 & 2** – crawl and collect data.
- **`run_step3.py`**: **Steps 1 + 2 + 3** – crawl, collect, then run AI agents.
- **`run_step5.py`**: **Full pipeline** – crawl → collect → analyze → (optional RAG) → aggregate → generate PDF/JSON report.
- **`build_knowledge_base.py`**: One‑time script to embed WCAG docs into Pinecone for RAG.
- **`config/settings.py`**: Central configuration loader; reads `.env`, resolves Google credentials, validates Vertex AI config.
- **`src/pipeline.py`**: `AuditDataPipeline`, orchestrating crawling + data collection.
- **`src/crawler/`**: Website crawler using Playwright.
- **`src/collectors/`**: Per‑page collectors:
  - `screenshot_collector.py` – multiple viewports, 200% zoom.
  - `dom_collector.py` – full DOM + semantic snapshot.
  - `axe_scanner.py` – axe‑core WCAG scan.
  - `keyboard_recorder.py` – keyboard navigation / focus order.
- **`src/agents/`**:
  - `vision_agent.py` – screenshot‑based analysis.
  - `semantic_agent.py` – DOM/semantic analysis.
  - `keyboard_agent.py` – keyboard/focus analysis.
  - `orchestrator.py` – runs all agents in parallel and converts axe findings.
- **`src/rag/`**: WCAG data loader + Pinecone knowledge base integration.
- **`src/aggregator/`**: Deduplicates and aggregates issues into a unified report model.
- **`src/reports/pdf_generator.py`**: Produces a PDF report from the aggregated model.
- **`src/models.py`**: Pydantic models for crawl results, per‑page collections, issues, and reports.
- **`data/`**:
  - `wcag_docs/chunks.json` – cached WCAG chunks after KB build.
  - Audit outputs (JSON, PDF) and screenshots (default under `data/screenshots`).

---

## Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd "WCAG AUDIT AGENT"
```

If this repo is nested (e.g. `WCAG AUDIT AGENT/WCAG AUDIT AGENT`), ensure you are in the inner project folder that contains `run_audit.py`.

### 2. Create and activate a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

**Linux / macOS:**

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Install Playwright browsers (one‑time):

```bash
python -m playwright install
```

### 4. Configure environment variables

Create a `.env` file in the project root (same folder as `config/settings.py`) based on the variables below. You can also create a `.env.example` and copy from it.

#### Required for AI analysis (Steps 3+)

- **`GEMINI_API_KEY`** – API key for Google Gemini (via `google-genai`)  
- **`GCP_PROJECT_ID`** – Google Cloud project ID  
- **`GCP_REGION`** – Region (e.g. `us-central1`)  
- **`GOOGLE_APPLICATION_CREDENTIALS`** – Path to service account JSON (can be relative to project root; `settings.py` resolves it)

#### Required for RAG (optional, Step 4/5)

- **`PINECONE_API_KEY`** – Pinecone API key  
- **`PINECONE_INDEX_NAME`** – Pinecone index name (e.g. `wcag-knowledge`)

#### Crawler options (optional overrides)

- **`MAX_PAGES`** – Default max pages to crawl (fallback if CLI not used)  
- **`CRAWL_TIMEOUT_MS`** – Page timeout in ms (default `30000`)  
- **`HEADLESS_BROWSER`** – `"true"` / `"false"` (default `"true"`)

#### Backend / Storage (optional, future API pipeline)

- **`DATABASE_URL`** – Postgres connection URL  
- **`GCS_BUCKET_NAME`** – Google Cloud Storage bucket for uploads/reports

Example `.env` snippet:

```env
GEMINI_API_KEY=your-gemini-key
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=service-account.json

PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX_NAME=wcag-knowledge

MAX_PAGES=5
CRAWL_TIMEOUT_MS=30000
HEADLESS_BROWSER=true
```

Place your Google Cloud service account JSON file in the project root and set `GOOGLE_APPLICATION_CREDENTIALS` accordingly (relative or absolute path).

---

## Usage

You can run the pipeline in several modes depending on how much of the stack you have configured.

### Mode 1: Quick Crawl & Collect only (Steps 1 & 2)

Script: `run_audit.py`

```bash
python run_audit.py https://example.com
python run_audit.py https://example.com --max-pages 10
python run_audit.py https://secure.example.com --max-pages 5 --wcag-level wcag2aaa
```

- Prompts optionally for authentication (username/password + CSS selectors) if `--auth` or you answer `y` when asked.
- Crawls up to `--max-pages` pages.
- Collects:
  - Screenshots (desktop, tablet, mobile, 200% zoom)
  - Full DOM + semantic snapshot
  - axe‑core violations
  - Keyboard navigation / focus issues
- Prints a per‑page summary and writes raw JSON into `./data/audit_<id>_raw.json`.

### Mode 2: Crawl + Collect + AI Analysis (Steps 1 + 2 + 3)

Script: `run_step3.py`

```bash
python run_step3.py https://www.example.com --max-pages 3
python run_step3.py https://secure.example.com --max-pages 2 --auth
```

This mode additionally:

- Validates your Vertex AI / Gemini configuration via `config/settings.validate_vertex_ai()`.
- Runs three AI agents in parallel per page:
  - **Vision Agent** – analyzes screenshots for visual accessibility problems.
  - **Semantic Agent** – inspects DOM and structure for WCAG issues.
  - **Keyboard Agent** – evaluates keyboard navigation and focus.
- Converts axe‑core findings into a unified `AccessibilityIssue` format.
- Outputs:
  - Console summary grouped by severity (Critical, Serious, Moderate, Minor).
  - Full JSON results: `./data/audit_<id>_full.json`.

### Mode 3: Full Pipeline with RAG & Report (Steps 1 + 2 + 3 + 4 + 5)

Script: `run_step5.py`

```bash
python build_knowledge_base.py                      # one‑time, builds Pinecone KB
python run_step5.py https://www.example.com --max-pages 1
python run_step5.py https://www.example.com --max-pages 3 --wcag-level wcag2aa
python run_step5.py https://secure.example.com --max-pages 2 --auth
```

This mode:

- Runs crawl + collection + AI analysis as above.
- Optionally performs **RAG enrichment** (if `PINECONE_API_KEY` is set and `--no-rag` is not passed):
  - Links issues to WCAG 2.2 Understanding docs and Techniques.
  - Adds richer “why this matters” and “how to fix” context.
- Aggregates all issues across pages:
  - Deduplicates similar findings.
  - Computes overall score and per‑page scores.
  - Groups by severity, WCAG principle, and impact group.
- Generates outputs in the chosen `--output-dir` (default `./data`):
  - **PDF report** with executive summary, per‑page details, priority fixes.
  - **JSON report** `wcag_audit_<id>_report.json` with all structured data.

You can disable RAG even if Pinecone is configured:

```bash
python run_step5.py https://example.com --max-pages 3 --no-rag
```

---

## Data Output & Persistence

- **Screenshots**: Saved under `data/screenshots/` grouped by audit ID and viewport.
- **Raw collection JSON**: `data/audit_<audit_id>_raw.json` (Steps 1 & 2).
- **Full AI analysis JSON**: `data/audit_<audit_id>_full.json` (Steps 1+2+3).
- **Aggregated report JSON**: `data/wcag_audit_<audit_id>_report.json` (Full pipeline).
- **PDF report**: Generated into `data/` (path printed at the end of `run_step5.py`).
- **WCAG knowledge chunks**: `data/wcag_docs/chunks.json` (created by `build_knowledge_base.py`).

If you configure `DATABASE_URL` and `GCS_BUCKET_NAME`, later stages of the project can persist results to Postgres and upload PDFs/JSON to GCS (FastAPI endpoints are scaffolded in the dependencies but may not yet be fully wired in this repo snapshot).

---

## Architecture

### Step 1: Crawl

- **Module**: `src/crawler/crawler.py`
- **Responsibility**:
  - Discover pages starting from a seed URL (up to `max_pages`).
  - Track page metadata: URL, title, depth.
  - Handle optional authentication via `AuthConfig` (login form selectors provided at runtime).

### Step 2: Data Collection

- **Module**: `src/pipeline.py`, `src/collectors/*`
- For each discovered (or single) page:
  - Capture multiple viewport screenshots.
  - Extract full DOM and a semantic snapshot for LLM input.
  - Run axe‑core against the page for automated rule checks.
  - Record keyboard navigation order and focus visibility.
- Everything is wrapped in `AuditDataPipeline.run`, which returns:
  - `CrawlResult`
  - `List[PageCollectionResult]`

### Step 3: AI Agents

- **Module**: `src/agents/orchestrator.py`
- Steps:
  - Convert axe‑core violations into a unified `AccessibilityIssue` model (with mapped WCAG criteria, severity, impact groups).
  - Run three async agents in parallel using Gemini:
    - Vision, Semantic, Keyboard.
  - Combine all issues and summarize by source and severity.

### Step 4: RAG Knowledge Base (optional)

- **Modules**: `src/rag/wcag_data_loader.py`, `src/rag/knowledge_base.py`, `build_knowledge_base.py`
- Responsibilities:
  - Load WCAG 2.2 Understanding docs and Techniques into chunks.
  - Embed them via Vertex AI (`text-embedding-005`).
  - Store vectors in Pinecone under `PINECONE_INDEX_NAME`.
  - At audit time, query relevant techniques/understanding texts for each issue to enrich guidance.

### Step 5: Aggregation & Reporting

- **Modules**: `src/aggregator/deduplicator.py`, `src/reports/pdf_generator.py`
- Responsibilities:
  - Merge raw issues across pages, deduplicate, and compute:
    - Overall score
    - Per‑page scores
    - Severity distributions
    - Impact groups and WCAG principles affected
  - Select priority fixes with the biggest impact.
  - Render a structured PDF using WeasyPrint + Jinja2 templates.
  - Emit a machine‑readable JSON mirror of the report.

---

## Example Quick Usage

1. **Clone** the repository and `cd` into the project.
2. **Create & activate** a virtual environment.
3. **Install** dependencies with `pip install -r requirements.txt` and `python -m playwright install`.
4. **Create `.env`** with Gemini / Vertex AI settings (and Pinecone if you want RAG).
5. **(Optional)** Build the WCAG knowledge base:
   - `python build_knowledge_base.py`
6. **Run a quick audit**:
   - Collection only: `python run_audit.py https://example.com --max-pages 3`
   - With AI: `python run_step3.py https://example.com --max-pages 3`
   - Full report: `python run_step5.py https://example.com --max-pages 3`

Check the `data/` directory for generated JSON and PDF reports.

---

## Troubleshooting

- **`.env` not found**:
  - `config/settings.py` expects `.env` in the project root. If missing, you will see a warning. Copy `.env.example` to `.env` and fill in values.
- **Vertex AI / Gemini errors**:
  - Run any Step‑3+ script; it calls `validate_vertex_ai()` which will print specific configuration issues (missing project ID, missing or unreadable credentials file).
  - Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to a valid JSON file and that the service account has Vertex AI permissions.
- **Playwright / browser errors**:
  - Make sure you have run `python -m playwright install`.
  - On CI/headless environments, ensure required system libraries for Chromium are installed.
- **No pages collected**:
  - Check network access and target URL.
  - Confirm `max-pages` is ≥ 1.
  - For authenticated flows, verify the CSS selectors for username, password, and submit button.
- **RAG not working / disabled**:
  - `run_step5.py` prints the RAG status at startup.
  - Ensure `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` are set, and that `--no-rag` is not passed.
  - Run `build_knowledge_base.py` once before auditing with RAG.
- **PDF not generated**:
  - Check that `weasyprint` dependencies (system libraries like Cairo, Pango) are installed for your OS.
  - Inspect console output for WeasyPrint‑related errors.

If you run into issues not covered here, start by re‑running the command with a smaller `--max-pages` and verify that `.env` and credentials are correctly configured.

