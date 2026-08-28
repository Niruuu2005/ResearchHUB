# ResearchLite — Academic Viva Preparation Guide

This document contains high-yield questions, detailed technical answers, and conceptual summaries for faculty assessments and viva examinations.

---

## 1. Core Architecture & Microservices

### Q1: What is a Microservice Architecture, and how does ResearchLite exemplify it?
**Answer:**  
A microservice architecture structures an application as a collection of small, loosely-coupled, independently deployable services organized around specific business capabilities.  
**ResearchLite** is a self-contained research microservice with a single, clear responsibility: receiving a topic and returning synthesized summaries and academic literature. It exposes well-defined REST contracts (`/health`, `/research`, `/papers`), communicates over standard HTTP/JSON, and is packaged into a standalone Docker container with its own dependencies and runtime environment.

### Q2: Why did you choose FastAPI over Flask or Django?
**Answer:**  
1. **Native Asynchronous Support**: FastAPI is built on Starlette and ASGI, supporting native Python `async`/`await` coroutines. This allows ResearchLite to query Wikipedia, OpenAlex, and Crossref in parallel without blocking the server event loop.
2. **Automatic Data Validation**: Powered by Pydantic v2, request inputs and response schemas are strictly typed and validated at runtime, returning descriptive error messages (HTTP 422) for invalid payloads.
3. **Automated Interactive Documentation**: Generates OpenAPI (Swagger UI) at `/docs` and ReDoc at `/redoc` out-of-the-box without manual documentation overhead.
4. **Performance**: Significantly higher throughput compared to traditional WSGI frameworks like Flask.

---

## 2. Concurrency & Asynchronous Programming

### Q3: How does ResearchLite execute parallel requests to external APIs?
**Answer:**  
ResearchLite uses `httpx.AsyncClient` alongside `asyncio.gather(..., return_exceptions=True)`. When a request is received:
```python
results = await asyncio.gather(
    self.wikipedia.fetch_summary(topic),
    self.openalex.search_papers(topic),
    self.crossref.search_papers(topic),
    return_exceptions=True
)
```
All three network I/O operations occur concurrently on the asyncio event loop. Rather than waiting sequentially (e.g. $1s + 1s + 1s = 3s$), total execution time is roughly bounded by the slowest single request ($\approx \max(1s, 1s, 1s) = 1s$).

### Q4: What does `return_exceptions=True` in `asyncio.gather` accomplish?
**Answer:**  
By default, if any coroutine inside `asyncio.gather` raises an exception, the entire gather call fails immediately, canceling other tasks. Setting `return_exceptions=True` catches individual exceptions and returns them as values in the results list. This enables our service to inspect whether a provider failed (e.g. timeout on Crossref), append a warning message to the client response, and still deliver successful data from Wikipedia and OpenAlex.

---

## 3. Data Processing & Deduplication

### Q5: How does the Deduplication Engine work?
**Answer:**  
Scholarly papers often appear simultaneously in OpenAlex and Crossref. ResearchLite performs deduplication in two stages:
1. **DOI Normalization**: Checks for exact matching of normalized lowercase Digital Object Identifiers (`doi`). If already seen, the duplicate is skipped.
2. **Title Normalization**: Strips punctuation and whitespace, converts to lowercase, and checks against a set of seen titles.
3. **Sorting**: Orders unique publications by publication year in descending order.

### Q6: How are Key Points extracted without a heavy LLM?
**Answer:**  
To maintain zero external API key requirements and instant response times, ResearchLite uses deterministic sentence boundary tokenization and semantic length filtering to select the most salient thematic sentences from the introductory summary, ensuring fast, deterministic, and cost-free execution.

---

## 4. Containerization & Docker

### Q7: What is the difference between a Docker Image and a Docker Container?
**Answer:**  
- **Docker Image**: An immutable, read-only template with instructions for creating a container (including OS layer, Python runtime, source code, and dependencies).
- **Docker Container**: A running, stateful, isolated instance of an image executed as a process on the host OS kernel.

### Q8: Why use `python:3.12-slim` instead of `alpine` or `latest`?
**Answer:**  
- `python:3.12-slim` is based on Debian Slim, offering a tiny footprint (~150MB) while maintaining full compatibility with standard C-extensions (glibc) used by Python packages, avoiding musl libc compilation issues common in Alpine.
- Pinned version `3.12-slim` ensures deterministic, reproducible builds across development and production environments.

### Q9: Why is running the container as a non-root user important?
**Answer:**  
Running as `root` inside a container presents security risks: if an attacker exploits a remote code execution vulnerability in the application or runtime, they gain root privileges on the container and potentially the host system. ResearchLite creates an unprivileged user (`appuser`, UID 1000) in the Dockerfile to enforce the principle of least privilege.

---

## 5. API Testing & Verification

### Q10: How do you test external API calls reliably without internet dependency in CI?
**Answer:**  
In unit tests (`tests/test_providers.py`), we use `unittest.mock.patch` to intercept HTTP client calls (`httpx.AsyncClient.get`) and supply mocked `httpx.Response` objects containing canned JSON fixtures. This guarantees tests are fast, deterministic, and pass even during offline development or external API outages.
