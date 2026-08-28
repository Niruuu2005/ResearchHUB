# ResearchLite — Development Log & Milestone History

This log records the completed development phases, tests, and deliverables.

---

## Milestone 1 — Project Inception & Foundation
- **Date**: 2026-08-28
- **Scope**: Core project directory structure, dependencies, configuration, and data models.
- **Files Created**:
  - `requirements.txt`
  - `.gitignore`
  - `.env.example`
  - `app/__init__.py`
  - `app/config.py`
  - `app/models/__init__.py`
  - `app/models/schemas.py`
- **Result**: Data schemas validated with Pydantic v2.

---

## Milestone 2 — Research Provider Adapters
- **Date**: 2026-08-28
- **Scope**: Built asynchronous client adapters for Wikipedia, OpenAlex, and Crossref APIs.
- **Files Created**:
  - `app/services/__init__.py`
  - `app/services/wikipedia_service.py`
  - `app/services/openalex_service.py`
  - `app/services/crossref_service.py`
- **Result**: All providers implement non-blocking `httpx` async client queries with custom `User-Agent` headers and timeout boundaries.

---

## Milestone 3 — Orchestration, Deduplication & Aggregation
- **Date**: 2026-08-28
- **Scope**: Integrated `ResearchService` with concurrent `asyncio.gather` pipeline, deduplication by DOI/title, key-point extraction, and partial failure resilience.
- **Files Created**:
  - `app/services/research_service.py`
- **Result**: Partial provider failures are caught and surfaced via structured `warnings` without failing requests.

---

## Milestone 4 — FastAPI Routing & API Surface
- **Date**: 2026-08-28
- **Scope**: Exposed `/health`, `/research`, and `/papers` endpoints with CORS and Swagger OpenAPI documentation.
- **Files Created**:
  - `app/api/__init__.py`
  - `app/api/routes.py`
  - `app/main.py`
- **Result**: Complete REST API verified and functional.

---

## Milestone 5 — Single-Page User Interface
- **Date**: 2026-08-28
- **Scope**: Built a modern, responsive single-page web UI in vanilla HTML5, CSS3, and JavaScript.
- **Files Created**:
  - `app/static/index.html`
- **Result**: Live search, loading indicators, summary cards, key-point bullets, paper cards, and warning banners.

---

## Milestone 6 — Containerization & Packaging
- **Date**: 2026-08-28
- **Scope**: Docker containerization with unprivileged `appuser` and health check.
- **Files Created**:
  - `Dockerfile`
  - `.dockerignore`
- **Result**: Production-ready container configuration.

---

## Milestone 7 — Automated Testing Suite
- **Date**: 2026-08-28
- **Scope**: Automated unit and integration test suite with Pytest and TestClient.
- **Files Created**:
  - `tests/__init__.py`
  - `tests/test_health.py`
  - `tests/test_research.py`
  - `tests/test_providers.py`
  - `pytest.ini`
- **Result**: 12/12 tests passed successfully.

---

## Milestone 8 — Academic Documentation & Viva Preparation
- **Date**: 2026-08-28
- **Scope**: Complete documentation suite for academic assessment.
- **Files Created**:
  - `README.md`
  - `project.md`
  - `CHANGELOG.md`
  - `docs/development-plan.md`
  - `docs/architecture.md`
  - `docs/troubleshooting.md`
  - `docs/viva.md`
  - `docs/development-log.md`
- **Result**: Full academic submission-ready documentation.
