from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Core Research Schemas (Preserved for backwards compatibility & extended)
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    """Input payload for research queries."""

    topic: str = Field(
        ...,
        description="The research topic or subject to query.",
        min_length=1,
        max_length=200,
        examples=["Quantum Computing"],
    )
    year_from: Optional[int] = Field(default=None, description="Start publication year.")
    year_to: Optional[int] = Field(default=None, description="End publication year.")
    open_access_only: bool = Field(default=False, description="Filter for open-access papers.")
    sources: Optional[List[str]] = Field(default=None, description="List of providers: openalex, crossref.")

    @field_validator("topic", mode="before")
    @classmethod
    def validate_and_strip_topic(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Topic must be a string.")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Topic must not be empty.")
        return cleaned


class Paper(BaseModel):
    """Academic publication metadata model."""

    id: Optional[Union[int, str]] = Field(default=None, description="Unique paper identifier if stored.")
    title: str = Field(..., description="Title of the research paper.")
    authors: List[str] = Field(default_factory=list, description="List of author names.")
    year: Optional[int] = Field(default=None, description="Year of publication.")
    source: str = Field(..., description="Academic repository source (e.g., OpenAlex, Crossref).")
    url: Optional[str] = Field(default=None, description="Direct URL or DOI resolver link.")
    doi: Optional[str] = Field(default=None, description="Digital Object Identifier (DOI).")
    venue: Optional[str] = Field(default=None, description="Journal, book, or conference name.")
    open_access: bool = Field(default=False, description="Whether paper is open access.")
    pdf_url: Optional[str] = Field(default=None, description="Direct PDF download URL if open access.")
    abstract: Optional[str] = Field(default=None, description="Paper abstract text.")
    is_saved: bool = Field(default=False, description="Whether paper is in user library.")


class Source(BaseModel):
    """Reference citation source."""

    name: str = Field(..., description="Provider name (e.g. Wikipedia).")
    title: str = Field(..., description="Document or article title.")
    url: str = Field(..., description="Source link URL.")


class ResearchResponse(BaseModel):
    """Aggregated research response payload."""

    topic: str = Field(..., description="The query topic.")
    summary: str = Field(..., description="Introductory topic summary synthesized from sources.")
    key_points: List[str] = Field(
        default_factory=list,
        description="Core takeaways and key concepts derived from the summary.",
    )
    papers: List[Paper] = Field(
        default_factory=list,
        description="Normalized and deduplicated list of academic papers.",
    )
    sources: List[Source] = Field(
        default_factory=list, description="Primary sources and references consulted."
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Provider-specific warnings in case of partial failures or timeouts.",
    )
    session_id: Optional[int] = Field(default=None, description="Saved research session ID.")


class HealthResponse(BaseModel):
    """Health check response payload."""

    status: str = Field(default="running", description="Current service health status.")
    service: str = Field(default="ResearchLite", description="Name of the microservice.")
    version: Optional[str] = Field(default="2.0.0", description="Service build version.")


class ReadyResponse(BaseModel):
    """Readiness probe response payload."""

    status: str = Field(default="ready", description="Overall readiness status.")
    database: str = Field(default="healthy", description="Database connectivity status.")
    redis: str = Field(default="healthy", description="Redis queue/cache status.")
    worker: str = Field(default="healthy", description="Celery worker status.")


# ---------------------------------------------------------------------------
# Project Schemas
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(default="")
    objective: Optional[str] = Field(default="")


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    objective: Optional[str] = None
    archived: Optional[bool] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    objective: Optional[str] = None
    archived: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    paper_count: int = 0

    class Config:
        from_attributes = True


class ProjectAddPaper(BaseModel):
    paper_id: int


# ---------------------------------------------------------------------------
# Paper Library Schemas
# ---------------------------------------------------------------------------

class PaperSaveRequest(BaseModel):
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    source: str = "Manual"
    url: Optional[str] = None
    doi: Optional[str] = None
    venue: Optional[str] = None
    open_access: bool = False
    pdf_url: Optional[str] = None
    abstract: Optional[str] = None
    project_id: Optional[int] = None


class PaperOut(BaseModel):
    id: int
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    source: str
    url: Optional[str] = None
    doi: Optional[str] = None
    venue: Optional[str] = None
    open_access: bool = False
    pdf_url: Optional[str] = None
    abstract: Optional[str] = None
    has_pdf: bool = False
    processing_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Document & PDF Schemas
# ---------------------------------------------------------------------------

class DocumentOut(BaseModel):
    id: int
    paper_id: int
    file_name: str
    file_size: int
    page_count: int
    processing_status: str
    checksum: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProcessingStatusOut(BaseModel):
    paper_id: int
    has_document: bool
    status: str
    page_count: int
    chunks_count: int
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# RAG & Chat Schemas
# ---------------------------------------------------------------------------

class CitationItem(BaseModel):
    paper_id: int
    paper_title: str
    doi: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    snippet: str


class ChatQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: Optional[int] = None
    paper_ids: Optional[List[int]] = None


class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    citations: List[CitationItem] = Field(default_factory=list)
    created_at: datetime


class ChatResponse(BaseModel):
    session_id: int
    question: str
    answer: str
    citations: List[CitationItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Summaries & Intelligence Schemas
# ---------------------------------------------------------------------------

class PaperSummaryOut(BaseModel):
    paper_id: int
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    research_problem: str
    objective: str
    background: str
    methodology: str
    dataset: str
    models_algorithms: str
    experimental_setup: str
    key_results: str
    major_findings: str
    limitations: str
    future_work: str
    research_contribution: str
    keywords: List[str] = Field(default_factory=list)
    key_takeaways: List[str] = Field(default_factory=list)
    citation: str
    model_used: str
    generated_at: datetime


class CollectionSummaryOut(BaseModel):
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    papers_analyzed: int
    major_themes: List[str] = Field(default_factory=list)
    common_methodologies: str
    major_findings: str
    conflicting_findings: str
    research_gaps: str
    emerging_trends: str
    future_opportunities: str
    references: List[str] = Field(default_factory=list)
    generated_at: datetime


# ---------------------------------------------------------------------------
# Paper Comparison Schemas
# ---------------------------------------------------------------------------

class ComparisonRequest(BaseModel):
    paper_ids: List[int] = Field(..., min_length=2, max_length=5)


class PaperComparisonColumn(BaseModel):
    paper_id: int
    title: str
    authors: List[str]
    year: Optional[int]
    research_problem: str
    objective: str
    dataset: str
    methodology: str
    model: str
    results: str
    strengths: str
    limitations: str
    future_work: str


class ComparisonResponse(BaseModel):
    matrix: List[PaperComparisonColumn]
    similarities: str
    differences: str
    methodological_trends: str
    research_gaps: str


# ---------------------------------------------------------------------------
# Literature Review Schemas
# ---------------------------------------------------------------------------

class LiteratureReviewRequest(BaseModel):
    project_id: Optional[int] = None
    paper_ids: Optional[List[int]] = None
    topic: Optional[str] = None
    citation_style: str = Field(default="IEEE", pattern="^(IEEE|APA|MLA|Harvard)$")


class LiteratureReviewOut(BaseModel):
    id: Optional[int] = None
    title: str
    sections: Dict[str, str]
    references: List[str]
    citation_style: str
    paper_ids: List[int] = Field(default_factory=list)
    project_id: Optional[int] = None
    papers_analyzed: int = 0
    created_at: datetime


# ---------------------------------------------------------------------------
# Notes & Highlights
# ---------------------------------------------------------------------------

class NoteCreate(BaseModel):
    title: str
    content: str
    project_id: Optional[int] = None
    paper_id: Optional[int] = None
    page_number: Optional[int] = None
    tags: List[str] = Field(default_factory=list)


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    page_number: Optional[int] = None
    tags: Optional[List[str]] = None


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    project_id: Optional[int] = None
    paper_id: Optional[int] = None
    page_number: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Citation Manager Schemas
# ---------------------------------------------------------------------------

class CitationFormatRequest(BaseModel):
    paper_ids: List[int]
    style: str = Field(default="IEEE", pattern="^(IEEE|APA|MLA|Harvard)$")


class CitationItemOut(BaseModel):
    paper_id: int
    title: str
    style: str
    formatted_text: str
    bibtex: str


class CitationExportResponse(BaseModel):
    style: str
    citations: List[str]
    bibtex: str


# ---------------------------------------------------------------------------
# Report & Export Schemas
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    title: str = Field(default="ResearchOps AI Report")
    report_type: str = Field(default="research_report")  # research_report, literature_review, collection_summary, comparison, paper_summary
    format: str = Field(default="pdf")  # pdf, docx, md, json, bibtex
    citation_style: str = Field(default="IEEE")
    project_id: Optional[int] = None
    paper_ids: Optional[List[int]] = None
    include_toc: bool = True
    include_cover: bool = True


class ExportOut(BaseModel):
    id: int
    title: str
    report_type: str
    format: str
    download_url: str
    file_size_bytes: int = 0
    status: str
    project_id: Optional[int] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# DevOps & Operations Schemas
# ---------------------------------------------------------------------------

class ProviderStatusItem(BaseModel):
    name: str
    status: str  # healthy, degraded, unavailable
    latency_ms: float
    last_checked: datetime
    error: Optional[str] = None


class JobStatusOut(BaseModel):
    id: str
    job_type: str
    status: str  # queued, running, completed, failed
    progress: int = 0
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class DevOpsOverview(BaseModel):
    app_name: str
    version: str
    git_commit: str
    build_number: str
    environment: str
    api_health: str
    db_health: str
    redis_health: str
    worker_health: str
    providers: List[ProviderStatusItem]
    active_jobs: int
    total_projects: int
    total_papers: int
    total_documents: int
    total_chunks: int
    total_conversations: int
    total_reports: int


class AuditEventOut(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime
