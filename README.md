# ResearchOps AI — Intelligent Literature Research & DevOps Platform

> **Academic DevOps + AI Literature Research Platform**  
> A cloud-ready, observable research platform built with **Python 3.12+**, **FastAPI**, **PostgreSQL** (pgvector image for future SQL vectors), **Redis**, **Celery**, **Docker Compose**, **Prometheus**, **Grafana**, and RAG-powered document intelligence.

---

## 1. Executive Summary

**ResearchOps AI** is the expanded evolution of the original *ResearchLite* microservice. It transforms an ephemeral query tool into a comprehensive, production-grade **research intelligence workspace and DevOps lifecycle platform**.

The system automates the complete scholarly research lifecycle:

```text
Research Topic
      ↓
Discover Papers (OpenAlex, Crossref, Wikipedia)
      ↓
Save to Project Workspace
      ↓
Download / Upload PDFs
      ↓
Extract, Chunk, and Create Dense Vector Embeddings
      ↓
Chat with Individual Papers & Entire Library (RAG)
      ↓
Compare Research Papers (Side-by-Side Matrix)
      ↓
Generate 11-Section Literature Review
      ↓
Export Referenced Reports (PDF, DOCX, Markdown, BibTeX)
      ↓
Monitor Services, Background Queues & Metrics in ResearchOps Control Center
```

---

## 2. Core Feature Modules

1. **Scholarly Literature Discovery**: Concurrent querying across OpenAlex, Crossref, and Wikipedia with date filtering, open-access status checks, DOI/title deduplication, and key-point extraction.
2. **Project Workspaces**: Create, organize, and archive dedicated research projects grouping papers, notes, chats, and reviews.
3. **Personal Paper Library**: Persistent collection of saved papers with status tracking, tags, and citation generators.
4. **Document Ingestion & Validation**: Secure PDF uploads and open-access downloads with SHA-256 checksumming, MIME verification, and text extraction via PyMuPDF (`fitz`) and `pypdf`.
5. **RAG Semantic Chat**: Query single papers or entire project collections with grounded answers backed by precise page numbers and section citations.
6. **16-Parameter Structured Summaries**: Automated empirical summaries covering research problems, methodologies, datasets, algorithms, findings, limitations, and future directions.
7. **Paper Comparison Matrix**: Side-by-side comparative analysis of 2 to 5 papers highlighting trade-offs, methodological trends, and open research gaps.
8. **Literature Review Builder**: 11-section reviews grounded in saved paper abstracts/metadata (extractive synthesis, not invented prose).
9. **Citation Manager**: Instant formatting and export in IEEE, APA, MLA, Harvard, and BibTeX styles.
10. **Multi-Format Report Exports**: Downloadable PDF (ReportLab), Word DOCX (python-docx), Markdown, JSON, and BibTeX artifacts.
11. **ResearchOps Control Center**: Service health, Celery job queues (when `USE_CELERY=true`), Prometheus gauges from live DB counts, and build metadata.

---

## 3. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Runtime** | Python 3.12+ / FastAPI / Uvicorn | High-throughput asynchronous REST API |
| **Relational Database** | PostgreSQL 16 (pgvector image) / SQLite | Relational state; embeddings stored as JSON with Python cosine search |
| **Distributed Queue** | Redis 7 + Celery | Async PDF/export jobs when `USE_CELERY=true` (sync fallback otherwise) |
| **Document Processing** | PyMuPDF (`fitz`) / pypdf | PDF text extraction and sliding-window chunking |
| **Embeddings & Vector** | sentence-transformers or hash | 384-dim vectors; ST when installed, lexical hash fallback |
| **AI Reasoning** | OpenAI / Gemini / Ollama / offline extract | Configurable LLM; offline mode quotes retrieved chunks only |
| **Observability** | Prometheus + Grafana | Live metrics scraping, latency monitoring, and healthchecks |
| **Containerization** | Docker & Docker Compose | Multi-container reproducible runtime |
| **CI/CD** | GitHub Actions | Automated linting, pytest with coverage, and container builds |
| **User Interface** | Modern Single Page App (SPA) | Glassmorphic dark aesthetic, responsive sidebar, Chart.js analytics |

---

## 4. Quickstart Guide

Full instructions (local, Docker Compose, Terraform → EC2 → Ansible): **[docs/deployment.md](docs/deployment.md)**  
Command cheat sheet: **[docs/deployment-commands.md](docs/deployment-commands.md)**

### Option A: Local Development (Zero-Setup Mode)
The platform includes automatic fallback for local development without requiring external daemons:

```powershell
# 1. Activate virtual environment
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser:
- **Application Dashboard**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **Prometheus Metrics**: `http://localhost:8000/metrics`
- **Health Check**: `http://localhost:8000/health`
- **Readiness Probe**: `http://localhost:8000/ready`

---

### Option B: Docker Compose Multi-Service Cluster

**Start Docker Desktop first.** Free port 8000 (stop local uvicorn) if needed.

```powershell
docker compose up --build -d
docker compose ps
curl.exe http://localhost:8000/health
```

Migrations run automatically on API startup.

Service URLs:
- **API / Web UI**: `http://localhost:8000`
- **Nginx Gateway**: `http://localhost:8080`
- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3001` (admin / admin)

---

### Option C: AWS EC2 (Terraform + Ansible + Docker)

```text
GitHub → Terraform (EC2 + SG) → Ansible (Docker Compose on /opt/researchhub) → http://<public-ip>
```

See **[docs/deployment.md](docs/deployment.md)** Part 3 for the full walkthrough.

---

## 5. Automated Testing

Execute the comprehensive automated test suite:

```powershell
pytest -v
```

Expect all tests to pass (currently ~33). See `tests/` for coverage of health, library, RAG, exports, operations, and more.

---

## 6. Repository Layout

```text
ResearchHub/
├── app/
│   ├── main.py                  # Lifespan startup, router mounting, static serving
│   ├── config.py                # Centralized environment configuration
│   ├── api/                     # Modular REST API endpoints
│   │   ├── health.py            # /health, /ready, /metrics, /api/system/version
│   │   ├── research.py          # /api/research, history tracking
│   │   ├── projects.py          # /api/projects workspaces CRUD
│   │   ├── papers.py            # /api/papers catalogue
│   │   ├── documents.py         # PDF upload, fetch, and stream
│   │   ├── chat.py              # Grounded RAG chat (paper, project, library)
│   │   ├── summaries.py         # 16-field paper & collection summaries
│   │   ├── compare.py           # Multi-paper comparative matrix
│   │   ├── literature_review.py # 11-section literature review generator
│   │   ├── notes.py             # Research notes & highlights
│   │   ├── citations.py         # IEEE, APA, MLA, Harvard, BibTeX
│   │   ├── exports.py           # Report file generation & downloads
│   │   ├── operations.py        # DevOps Control Center, jobs, health
│   │   └── routes.py            # Legacy backwards compatibility forwarders
│   ├── db/
│   │   └── session.py           # SQLAlchemy session, engine, init_db
│   ├── models/
│   │   ├── database.py          # SQLAlchemy ORM models
│   │   └── schemas.py           # Pydantic v2 validation models
│   ├── services/                # Business logic, RAG, providers, LLM, exports
│   ├── workers/                 # Celery app & async task handlers
│   ├── utils/                   # Text chunking, hashing, citations, files
│   └── static/
│       └── index.html           # Modern SPA interface (20 views, Chart.js)
├── monitoring/
│   └── prometheus.yml           # Prometheus scrape configuration
├── tests/                       # 23 automated unit & integration test suites
├── docs/                        # Architecture, API, deployment, and viva docs
├── Dockerfile                   # Production API container image
├── Dockerfile.worker            # Production Celery worker container image
├── docker-compose.yml           # Multi-service container topology
├── requirements.txt             # Python project dependencies
└── README.md                    # Project documentation
```
