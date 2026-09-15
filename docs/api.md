# ResearchOps AI — REST API Reference

Comprehensive guide to endpoints provided by the ResearchOps AI backend service.

---

## 1. System & Observability

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe returning operational status and version. |
| `GET` | `/ready` | Readiness probe verifying database, redis, and worker availability. |
| `GET` | `/metrics` | Prometheus metrics scrape endpoint. |
| `GET` | `/api/system/version` | Deployed version, git commit hash, and build number. |

---

## 2. Topic Research

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/research` | Multi-provider discovery (Wikipedia, OpenAlex, Crossref) with filters. |
| `GET` | `/api/research/history` | Chronological research session history. |
| `GET` | `/api/research/{session_id}` | Retrieve cached research query details. |
| `DELETE` | `/api/research/{session_id}` | Remove research session from history. |

---

## 3. Projects & Workspaces

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/projects` | List all research workspaces with paper counts. |
| `POST` | `/api/projects` | Create a new research project. |
| `GET` | `/api/projects/{id}` | Project workspace details and associated papers. |
| `PATCH` | `/api/projects/{id}` | Rename or update project metadata. |
| `DELETE` | `/api/projects/{id}` | Delete a research project. |
| `POST` | `/api/projects/{id}/papers` | Link paper to project. |
| `DELETE` | `/api/projects/{id}/papers/{paper_id}` | Remove paper from project. |

---

## 4. Paper Library & PDF Ingestion

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/papers` | Filterable paper catalogue (search, project, pagination). |
| `POST` | `/api/papers/save` | Save discovered paper to personal library. |
| `GET` | `/api/papers/{id}` | Get paper metadata and indexing state. |
| `DELETE` | `/api/papers/{id}` | Delete paper from library. |
| `POST` | `/api/papers/{id}/upload` | Multipart upload for paper PDF. |
| `POST` | `/api/papers/{id}/fetch-pdf` | Download open-access PDF directly. |
| `GET` | `/api/papers/{id}/pdf` | Stream stored PDF document. |
| `GET` | `/api/papers/{id}/processing-status` | Get vector indexing and chunk status. |

---

## 5. RAG Chat & AI Intelligence

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat/paper/{id}` | Grounded Q&A with single paper with page citations. |
| `POST` | `/api/chat/project/{id}` | Cross-paper synthesis chat within a project. |
| `POST` | `/api/chat/library` | Global RAG chat across all saved library papers. |
| `GET` | `/api/chat/{session_id}/messages` | Message history for chat session. |
| `POST` | `/api/papers/{id}/summarize` | Generate 16-parameter structured paper summary. |
| `POST` | `/api/projects/{id}/summarize` | Generate project collection review. |
| `POST` | `/api/compare` | Compare 2 to 5 papers (matrix + analysis). |
| `POST` | `/api/literature-review` | Generate 11-section grounded literature review. |

---

## 6. Citations & Reports

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/citations/format` | Format citations in IEEE, APA, MLA, Harvard. |
| `POST` | `/api/citations/export` | Bulk export citations and BibTeX. |
| `POST` | `/api/exports/report` | Generate downloadable report (PDF, DOCX, MD, JSON, BibTeX). |
| `GET` | `/api/exports` | List exported reports. |
| `GET` | `/api/exports/{id}/download` | Download generated report file. |

---

## 7. ResearchOps Control Center

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/operations/overview` | DevOps dashboard metrics, health, and counts. |
| `GET` | `/api/operations/providers/health` | Live latency and status for academic APIs. |
| `GET` | `/api/operations/jobs` | Background task queue state. |
| `GET` | `/api/operations/audit` | Operational audit trail. |
| `GET` | `/api/operations/deployments` | Build / deployment metadata (read-only). |
