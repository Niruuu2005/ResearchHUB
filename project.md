# Academic Project Report — ResearchLite Microservice

**Project Title:** ResearchLite: Automated Topic Research Microservice  
**Academic Course:** DevOps & Cloud Computing / Software Architecture  
**Service Version:** 1.0.0  

---

## 1. Executive Summary

**ResearchLite** is an asynchronous, containerized topic-research microservice developed using modern Python and FastAPI. The service enables researchers, students, and engineers to instantly acquire synthesized overviews, key conceptual takeaways, and peer-reviewed academic literature on any topic through a unified interface. By integrating three open-access bibliographic and knowledge repositories (**Wikipedia**, **OpenAlex**, and **Crossref**), ResearchLite bridges the gap between general encyclopedic knowledge and formal academic literature while guaranteeing fault-tolerant resilience against third-party API outages.

---

## 2. Problem Statement & Objectives

### 2.1 Problem Statement
Preliminary topic exploration typically involves repetitive manual tasks:
1. Navigating to encyclopedic websites for high-level definitions and summaries.
2. Searching academic databases (such as Google Scholar, OpenAlex, or Crossref) for relevant literature.
3. Manually filtering duplicate entries across publishers.
4. Dealing with unhandled network failures when academic registries experience intermittent downtime.

### 2.2 Project Objectives
- **Single Point of Query**: Aggregate topic summaries and scholarly literature through a unified REST API and web UI.
- **Asynchronous Concurrency**: Execute independent provider queries concurrently using Python `asyncio` and `httpx` to minimize response latency.
- **Fault-Tolerant Architecture**: Handle partial upstream provider failures gracefully, returning available data with warnings instead of failing the request.
- **Deduplication Engine**: Normalize DOIs and titles across distinct academic indexing registries.
- **Containerized Portability**: Ensure deterministic deployment across environments using a Docker container.
- **Automated Verification**: Achieve test coverage across endpoints, adapters, and failure scenarios.

---

## 3. System Architecture & Component Design

```mermaid
graph TD
    subgraph Client Layer
        Web[Single-Page Web UI]
        Client[External API Consumer]
    end

    subgraph Microservice Runtime (Docker / Uvicorn)
        Router[FastAPI Routing Engine]
        Config[App Configuration & Policies]
        
        subgraph Research Orchestration Engine
            Orchestrator[ResearchService]
            NLP[Key-Point Extractor]
            Dedup[DOI & Title Deduplicator]
        end

        subgraph Provider Adapters
            Wiki[WikipediaService]
            Alex[OpenAlexService]
            Cross[CrossrefService]
        end
    end

    subgraph External Public Knowledge APIs
        ExtWiki[(Wikipedia REST API)]
        ExtAlex[(OpenAlex Works API)]
        ExtCross[(Crossref Registry)]
    end

    Web -->|HTTP POST| Router
    Client -->|HTTP GET / POST| Router
    Router --> Orchestrator
    
    Orchestrator -.->|Parallel Async Call| Wiki
    Orchestrator -.->|Parallel Async Call| Alex
    Orchestrator -.->|Parallel Async Call| Cross
    
    Wiki --> ExtWiki
    Alex --> ExtAlex
    Cross --> ExtCross
    
    Wiki -->|Raw Extract| Dedup
    Alex -->|Raw Works| Dedup
    Cross -->|Raw Works| Dedup
    
    Dedup --> NLP
    NLP --> Router
```

### 3.1 Component Responsibilities

1. **FastAPI Application Layer (`app/main.py`, `app/api/routes.py`)**:
   - Manages HTTP request life cycles, CORS policies, routing, static asset serving, and automatic OpenAPI schema generation.
2. **Data Validation Layer (`app/models/schemas.py`)**:
   - Enforces strict input validation on topic strings (stripping whitespace, length constraints, preventing empty inputs) and structures output data models.
3. **Wikipedia Adapter (`app/services/wikipedia_service.py`)**:
   - Fetches introductory topic summaries and canonical URLs via the Wikipedia REST API, with fallback to search when direct page titles differ.
4. **OpenAlex Adapter (`app/services/openalex_service.py`)**:
   - Retrieves scholarly works, publication years, author lists, landing page URLs, and DOIs from the OpenAlex Works API.
5. **Crossref Adapter (`app/services/crossref_service.py`)**:
   - Retrieves bibliographic records, dates, and DOIs from the Crossref public registry.
6. **Research Orchestrator (`app/services/research_service.py`)**:
   - Executes parallel async calls via `asyncio.gather`, cleans and normalizes bibliographic entries, eliminates duplicate DOIs, extracts key takeaways, and captures warnings.

---

## 4. API Design & Data Contract

### 4.1 `GET /health`
- **Purpose**: Liveness and readiness probe for container orchestrators and monitoring agents.
- **Status Code**: `200 OK`
- **Response Format**:
  ```json
  {
    "status": "running",
    "service": "ResearchLite",
    "version": "1.0.0"
  }
  ```

### 4.2 `POST /research`
- **Purpose**: Main aggregated research pipeline endpoint.
- **Request Body**:
  ```json
  {
    "topic": "Quantum Computing"
  }
  ```
- **Validation**:
  - Empty string: returns `422 Unprocessable Entity`.
  - Non-string: returns `422 Unprocessable Entity`.
- **Response Structure**:
  ```json
  {
    "topic": "Quantum Computing",
    "summary": "Quantum computing is a rapidly-emerging technology...",
    "key_points": [
      "Point 1...",
      "Point 2..."
    ],
    "papers": [
      {
        "title": "Title of paper",
        "authors": ["Author One", "Author Two"],
        "year": 2024,
        "source": "OpenAlex",
        "url": "https://doi.org/...",
        "doi": "10.xxxx/yyyy"
      }
    ],
    "sources": [
      {
        "name": "Wikipedia",
        "title": "Quantum computing",
        "url": "https://en.wikipedia.org/wiki/Quantum_computing"
      }
    ],
    "warnings": []
  }
  ```

### 4.3 `GET /papers`
- **Purpose**: Specialized academic paper lookup without summary synthesis.
- **Query Parameter**: `topic` (string, required).
- **Response Format**: Array of `Paper` objects.

---

## 5. Fault Tolerance & Resilience Strategy

In distributed microservices, external dependency failures are inevitable. ResearchLite implements a **graceful degradation pattern**:

```text
               ┌───────────────────────┐
               │    Research Request   │
               └───────────┬───────────┘
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
       ┌───────────┐ ┌───────────┐ ┌───────────┐
       │ Wikipedia │ │ OpenAlex  │ │ Crossref  │
       │ (Success) │ │ (Timeout) │ │ (Success) │
       └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
             │             │             │
             │       Capture Error       │
             │      into 'warnings'      │
             │             │             │
             └─────────────┼─────────────┘
                           ▼
               ┌───────────────────────┐
               │   Return HTTP 200 OK  │
               │  Partial Data + Alert │
               └───────────────────────┘
```

1. **Non-Blocking Execution**: `asyncio.gather(..., return_exceptions=True)` ensures that an exception in one branch does not cancel other active coroutines.
2. **Explicit Timeouts**: External requests are governed by strict client-side timeouts (default: 10s) via `httpx.AsyncClient(timeout=...)`.
3. **Structured Warnings**: Caught exceptions are converted into user-friendly messages in the `warnings` array, allowing frontend clients to notify users without service disruption.

---

## 6. Containerization & Security Hygiene

### 6.1 Dockerfile Architecture
- **Base Image**: `python:3.12-slim` (minimal attack surface and image size).
- **Layer Caching**: Dependency installation (`requirements.txt`) occurs before copying application source to optimize build times.
- **Least Privilege Principle**: Creates and runs under an unprivileged user (`appuser`, UID 1000) rather than `root`.
- **Healthcheck Probe**: Native container health check verifies HTTP liveness at `/health`.

---

## 7. Verification & Testing Methodology

Automated testing is conducted via `pytest` and `FastAPI TestClient`:

| Test Module | Scope | Assertions |
|---|---|---|
| `test_health.py` | System health & root endpoint | Status 200, schema keys (`status`, `service`, `version`), index HTML serving |
| `test_research.py` | Endpoint validation & routing | Empty topics (422), missing bodies (422), successful response schema |
| `test_providers.py` | External adapters & resilience | Mocked Wikipedia parsing, OpenAlex parsing, Crossref parsing, partial failure handling, deduplication logic |

---

## 8. Conclusion & Future Scope

### 8.1 Conclusion
ResearchLite successfully demonstrates the design and implementation of a modern, asynchronous Python microservice. By integrating knowledge APIs, enforcing strict schema validation, providing resilient fallback mechanisms, and containerizing the runtime, the project achieves an optimal balance between simplicity and production-grade engineering practices.

### 8.2 Future Scope
- **Caching Layer**: Introducing an in-memory or Redis LRU cache for frequently queried research topics.
- **Export Options**: Enabling one-click export of paper citations in BibTeX and APA formats.
- **Vector Semantic Search**: Optional local embeddings to rank papers based on abstract similarity.
