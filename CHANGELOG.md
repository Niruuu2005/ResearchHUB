# Changelog

All notable changes to the **ResearchLite** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-08-28

### Added
- **Core Microservice Application**:
  - FastAPI application entry point with CORS support, static file mounting, and OpenAPI/Swagger documentation at `/docs`.
  - Configuration management in `app/config.py` with environment variable overrides and sensible timeouts.
  - Strict Pydantic v2 validation models for requests (`ResearchRequest`), responses (`ResearchResponse`, `HealthResponse`), academic publications (`Paper`), and reference citations (`Source`).
- **Research Provider Adapters**:
  - `WikipediaService`: Asynchronous client for Wikipedia REST API with search fallback for topic background summaries and canonical links.
  - `OpenAlexService`: Asynchronous client for the OpenAlex Works API to fetch scholarly publication metadata, DOIs, and authors.
  - `CrossrefService`: Asynchronous client for the Crossref API for bibliographic records and publication years.
- **Orchestration & Data Pipeline**:
  - `ResearchService`: Concurrent provider query execution via `asyncio.gather`.
  - Deterministic key-point extraction algorithm from topic summaries.
  - Paper normalization and deduplication by DOI and title similarity.
  - Fault-tolerant partial failure handling with structured warning collection.
- **User Interface**:
  - Modern single-page responsive web frontend at `/` with dark mode, live search suggestions, animated loading states, card layouts, and warning banners.
- **Containerization**:
  - Dockerfile based on `python:3.12-slim` with unprivileged `appuser` security and native healthcheck probe.
  - `.dockerignore` optimized build exclusion.
- **Automated Test Suite**:
  - 12 comprehensive unit and integration tests covering `/health`, `/research`, `/papers`, mock provider parsing, deduplication, and partial failure resilience.
- **Documentation**:
  - Comprehensive `README.md`, `project.md`, `docs/architecture.md`, `docs/viva.md`, `docs/troubleshooting.md`, `docs/development-plan.md`, and `docs/development-log.md`.
