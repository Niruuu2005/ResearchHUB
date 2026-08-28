# ResearchLite — Development Plan & Milestone Roadmap

---

## 1. Project Overview & Scope

**ResearchLite** is an asynchronous topic-research microservice developed with Python, FastAPI, and Docker, integrating open-access knowledge providers (Wikipedia, OpenAlex, and Crossref).

---

## 2. Milestone Decomposition

### Milestone 1: Core Foundation & Configuration
- [x] Create project layout (`app/`, `tests/`, `docs/`).
- [x] Configure dependencies in `requirements.txt`.
- [x] Set up `.gitignore` and `.env.example`.
- [x] Implement `app/config.py` for environment and timeout configuration.
- [x] Define data validation schemas in `app/models/schemas.py`.

### Milestone 2: Research Provider Adapters
- [x] Implement `WikipediaService` with REST summary endpoint and fallback search.
- [x] Implement `OpenAlexService` for academic publication queries.
- [x] Implement `CrossrefService` for bibliographic metadata queries.
- [x] Enforce finite timeouts and custom User-Agent headers across all adapters.

### Milestone 3: Research Pipeline & Orchestration
- [x] Implement `ResearchService` with `asyncio.gather(..., return_exceptions=True)`.
- [x] Build paper deduplication logic (DOI and normalized title).
- [x] Implement deterministic key-point extraction from summary text.
- [x] Implement partial failure resilience and warning aggregation.

### Milestone 4: API Layer & Endpoints
- [x] Implement `GET /health` endpoint for liveness and version info.
- [x] Implement `POST /research` endpoint with input validation.
- [x] Implement `GET /papers` endpoint for direct publication queries.
- [x] Mount FastAPI router and configure CORS in `app/main.py`.

### Milestone 5: Single-Page Web Frontend
- [x] Design modern dark/light responsive interface in `app/static/index.html`.
- [x] Implement topic search form, sample query tags, and loading states.
- [x] Render summary cards, numbered key points, paper cards with DOI links, and warning alerts.
- [x] Serve frontend at root URL (`GET /`).

### Milestone 6: Containerization & Packaging
- [x] Create production `Dockerfile` with `python:3.12-slim` base and unprivileged user.
- [x] Configure Docker container healthcheck probe.
- [x] Create `.dockerignore` to optimize build context.

### Milestone 7: Automated Testing
- [x] Implement `tests/test_health.py` for health and root endpoints.
- [x] Implement `tests/test_research.py` for route validation and error handling.
- [x] Implement `tests/test_providers.py` for mocked adapter unit tests and resilience checks.
- [x] Configure `pytest.ini` for clean async execution.

### Milestone 8: Academic Documentation & Reports
- [x] Write `README.md` with complete setup, API reference, and testing instructions.
- [x] Write `project.md` academic report.
- [x] Write `docs/architecture.md` with Mermaid diagrams.
- [x] Write `docs/troubleshooting.md` for error triage and debugging.
- [x] Write `docs/viva.md` for academic examination preparation.
- [x] Write `CHANGELOG.md` and `docs/development-log.md`.
