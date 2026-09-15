# ResearchOps AI — Academic Viva Defense Guide

Comprehensive technical Q&A covering Architecture, AI/NLP RAG Pipelines, Distributed Systems, and DevOps Engineering.

---

## 1. Project Overview & Elevator Pitch

**Q: What is ResearchOps AI, and what problem does it solve?**  
> **A:** ResearchOps AI is a cloud-ready, observable research intelligence and DevOps platform. Scholarly research is traditionally fragmented across searching for papers, finding open-access PDFs, reading long documents, synthesizing literature, extracting citations, and comparing findings. ResearchOps AI automates this lifecycle through multi-provider discovery (OpenAlex, Crossref, Wikipedia), PDF ingestion, vector chunking, citation-grounded RAG chat, structured summaries, comparative matrices, and 11-section literature reviews grounded in saved abstracts. It also demonstrates DevOps practices: Docker Compose, optional Celery workers, PostgreSQL, Prometheus metrics, structured logging, and CI/CD.

---

## 2. Architecture & Design Trade-offs

**Q: Why choose FastAPI instead of Django or Flask?**  
> **A:** FastAPI is built natively on Python’s asynchronous ASGI framework (Starlette and Pydantic). Because scholarly research involves making parallel network calls to multiple academic repositories (Wikipedia, OpenAlex, Crossref), FastAPI's `async/await` enables non-blocking concurrent HTTP requests via HTTPX. Additionally, automatic OpenAPI documentation and Pydantic v2 data validation ensure strict typing and reliable client contracts.

**Q: Why use PostgreSQL with a pgvector image instead of a separate vector database like Pinecone or Milvus?**  
> **A:** We run the `pgvector/pgvector:pg16` image so relational state (projects, papers, notes, jobs) and embeddings live in one database engine for simpler ops. Today embeddings are stored as JSON on chunk rows and ranked with Python cosine similarity; the pgvector extension is available for a future SQL `#<=>` index without changing the datastore. This keeps filtering by `project_id` / `paper_id` straightforward while remaining portable to SQLite for local zero-setup mode.

**Q: How does the system handle partial external API failures?**  
> **A:** Academic APIs frequently experience rate limits, transient network hiccups, or timeouts. Using `asyncio.gather(*tasks, return_exceptions=True)`, our research orchestration service isolates each provider. If Crossref or OpenAlex fails, the system logs the exception, appends a warning to the response payload, and returns synthesized findings from the surviving providers rather than crashing with a 500 error.

---

## 3. AI & Document Intelligence (RAG)

**Q: Explain the RAG pipeline implemented in ResearchOps AI.**  
> **A:** 
> 1. **Ingestion & Validation**: Uploaded or downloaded open-access PDFs are verified via MIME/magic bytes (`%PDF-`) and SHA-256 checksummed.
> 2. **Text Extraction**: PyMuPDF (`fitz`) or `pypdf` extracts text page-by-page.
> 3. **Chunking**: A sliding window chunks text into 400–600 character passages with an overlap of 100 characters to preserve cross-boundary semantics. Each chunk is tagged with its page number and detected section title.
> 4. **Embedding**: Chunks are embedded into 384-dimensional dense vectors.
> 5. **Retrieval**: When a researcher asks a question, the query vector is compared against chunk vectors using cosine similarity.
> 6. **Grounding & Citations**: The top-K ranked chunks are injected into the prompt. The LLM is instructed to answer strictly based on this evidence, generating explicit citations with paper titles, page numbers, and sections.

**Q: How does the system prevent LLM hallucinations?**  
> **A:** Hallucinations are mitigated through:
> - Strict temperature settings (0.2) in generative prompts.
> - Explicit constraint instructions forbidding statements outside the provided citations.
> - An offline extractive engine that quotes evidence directly from retrieved chunks when external LLM APIs are absent.
> - Literature review sections are built from stored abstracts/metadata rather than invented narrative.

---

## 4. DevOps & Observability

**Q: How do your health probes differ between liveness and readiness?**  
> **A:**
> - **Liveness (`GET /health`)**: Checks if the FastAPI Python process is running and responding. If this fails, container orchestrators (Docker/Kubernetes) immediately restart the container.
> - **Readiness (`GET /ready`)**: Verifies that downstream dependencies (PostgreSQL database, Redis broker, and Celery workers) are operational and capable of processing traffic. If a dependency is offline, the container is taken out of the load balancer rotation without being unnecessarily killed.

**Q: How does Prometheus scrape metrics from the application?**  
> **A:** The `/metrics` endpoint exposes Prometheus exposition text with gauges backed by live database counts (`researchops_total_papers`, `researchops_total_documents`, `researchops_total_chunks`, `researchops_total_projects`, `researchops_active_background_jobs`) plus measured provider probe latencies (`researchops_provider_latency_ms`). Prometheus scrapes this endpoint, and Grafana visualizes those real gauges.

**Q: What is the purpose of the Celery worker and Redis in this architecture?**  
> **A:** Heavy operations—such as downloading 30MB PDFs, running text extraction on 50 pages, and computing embeddings—would block the ASGI event loop if executed synchronously inside an HTTP request. Offloading these jobs to Celery workers via a Redis queue allows API requests to return immediately with a job ID, keeping the user interface fast and responsive.
