# ResearchOps AI — System Architecture & Specification

> **Intelligent Literature Research, Paper Analysis & DevOps Platform**  
> Scalable, observable architecture with FastAPI, PostgreSQL (pgvector-ready image), Redis, Celery, Docker, Prometheus, and RAG-based document intelligence.

---

## 1. High-Level Multi-Service Architecture

```mermaid
flowchart TD
    Browser["Client Browser (Single Page Application)"]
    
    subgraph Gateway & Ingress
        Nginx["Reverse Proxy / Nginx"]
    end

    subgraph Application Tier
        API["FastAPI REST API (/api/*, /metrics, /health, /ready)"]
        Worker["Celery Background Worker"]
    end

    subgraph Persistence & Caching
        PG[("PostgreSQL 16 (pgvector image)")]
        Redis[("Redis Cache & Broker")]
        DocStore[("Document Storage / Volume")]
    end

    subgraph Observability
        Prometheus["Prometheus Server (:9090)"]
        Grafana["Grafana Dashboard (:3001)"]
    end

    subgraph External Research Providers
        OpenAlex[("OpenAlex Works API")]
        Crossref[("Crossref Works API")]
        Wiki[("Wikipedia REST API")]
    end

    Browser -->|HTTPS / REST| Nginx
    Nginx --> API
    API -->|Read / Write| PG
    API -->|Queue Jobs / Cache| Redis
    API -->|Store PDFs & Reports| DocStore

    Worker -->|Consume Tasks| Redis
    Worker -->|Vector Indexing / Chunks| PG
    Worker -->|Extract Text| DocStore

    API -->|Async HTTP Queries| OpenAlex
    API -->|Async HTTP Queries| Crossref
    API -->|Async HTTP Queries| Wiki

    Prometheus -->|Scrape /metrics| API
    Grafana -->|Query Metrics| Prometheus
```

---

## 2. RAG Document Intelligence Pipeline

```mermaid
flowchart LR
    PDF["Research Paper PDF"] --> TextExt["PyMuPDF / pypdf Text Extraction"]
    TextExt --> Chunking["Sliding Window Chunker (Section & Page Tagged)"]
    Chunking --> Embedding["Dense Vector Embedding (384-dim)"]
    Embedding --> VectorStore[("Chunk Embeddings (JSON + Python Cosine)")]

    Query["User Question"] --> QueryEmbed["Query Vector Embedding"]
    QueryEmbed --> CosineSim["Cosine Similarity Search"]
    VectorStore --> CosineSim
    CosineSim --> TopK["Top-K Relevant Chunks"]
    TopK --> LLM["Grounded LLM / Offline Extract"]
    LLM --> Answer["Citations-Backed Response (Page & Section Referenced)"]
```

---

## 3. Data Entities & Schema Topology

- **ResearchProject**: Workspaces grouping papers, notes, chats, comparisons, and literature reviews.
- **Paper**: Canonical bibliographic records with DOI and title normalization deduplication.
- **PaperDocument**: Ingested PDFs with checksum validation, file metadata, and extraction lifecycle states (`pending`, `processing`, `ready`, `failed`).
- **PaperChunk**: Overlapping text passages tagged with page numbers and detected academic section headings.
- **PaperSummary**: Standardized 16-parameter empirical research summary.
- **ChatSession & ChatMessage**: Multi-turn dialogue with JSON-serialized source citation pills.
- **ExportReport**: Multi-format generated artifacts (PDF, DOCX, Markdown, JSON, BibTeX).
- **BackgroundJob**: Distributed Celery task tracker for long-running extractions.
- **DeploymentRecord & AuditEvent**: DevOps release tracking and operational audit trail.

---

## 4. Observability & DevOps Resilience

1. **Liveness Probe (`GET /health`)**: Checks process responsiveness.
2. **Readiness Probe (`GET /ready`)**: Asserts database and worker queue operational state.
3. **Prometheus Exporter (`GET /metrics`)**: Exposes DB-backed gauges (papers, documents, chunks, projects, active jobs) and measured provider probe latencies.
4. **Graceful Provider Degradation**: Isolated timeouts prevent single academic provider failures from halting user research queries.
5. **Build Metadata**: Control Center surfaces version/commit/build info (no simulated container rollback).
