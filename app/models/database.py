import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ResearchProject(Base):
    __tablename__ = "research_projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, default="")
    objective = Column(Text, default="")
    archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    papers = relationship("ProjectPaper", back_populates="project", cascade="all, delete-orphan")
    notes = relationship("ResearchNote", back_populates="project", cascade="all, delete-orphan")


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    topic = Column(String(300), nullable=False, index=True)
    year_from = Column(Integer, nullable=True)
    year_to = Column(Integer, nullable=True)
    open_access_only = Column(Boolean, default=False)
    summary = Column(Text, default="")
    key_points_json = Column(Text, default="[]")
    warnings_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(500), nullable=False, index=True)
    abstract = Column(Text, nullable=True)
    doi = Column(String(250), nullable=True, index=True)
    year = Column(Integer, nullable=True, index=True)
    venue = Column(String(300), nullable=True)
    source = Column(String(100), default="OpenAlex")
    source_id = Column(String(250), nullable=True)
    url = Column(String(500), nullable=True)
    open_access = Column(Boolean, default=False)
    pdf_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    authors = relationship("PaperAuthor", back_populates="paper", cascade="all, delete-orphan")
    projects = relationship("ProjectPaper", back_populates="paper", cascade="all, delete-orphan")
    documents = relationship("PaperDocument", back_populates="paper", cascade="all, delete-orphan")
    chunks = relationship("PaperChunk", back_populates="paper", cascade="all, delete-orphan")
    summary = relationship("PaperSummary", back_populates="paper", uselist=False, cascade="all, delete-orphan")
    notes = relationship("ResearchNote", back_populates="paper", cascade="all, delete-orphan")


class PaperAuthor(Base):
    __tablename__ = "paper_authors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    author_name = Column(String(250), nullable=False)
    order_index = Column(Integer, default=0)

    paper = relationship("Paper", back_populates="authors")


class ProjectPaper(Base):
    __tablename__ = "project_papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime, default=datetime.datetime.utcnow)

    project = relationship("ResearchProject", back_populates="papers")
    paper = relationship("Paper", back_populates="projects")


class PaperDocument(Base):
    __tablename__ = "paper_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    storage_key = Column(String(500), nullable=False)
    file_name = Column(String(300), nullable=False)
    file_size = Column(Integer, default=0)
    page_count = Column(Integer, default=0)
    processing_status = Column(String(50), default="pending")  # pending, processing, ready, failed
    checksum = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    paper = relationship("Paper", back_populates="documents")
    chunks = relationship("PaperChunk", back_populates="document", cascade="all, delete-orphan")


class PaperChunk(Base):
    __tablename__ = "paper_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_document_id = Column(Integer, ForeignKey("paper_documents.id", ondelete="CASCADE"), nullable=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, default=1)
    section = Column(String(200), default="Main")
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)  # JSON-encoded vector list for universal cross-platform SQLite/PG support

    paper = relationship("Paper", back_populates="chunks")
    document = relationship("PaperDocument", back_populates="chunks")


class PaperSummary(Base):
    __tablename__ = "paper_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, unique=True)
    research_problem = Column(Text, default="")
    objective = Column(Text, default="")
    background = Column(Text, default="")
    methodology = Column(Text, default="")
    dataset = Column(Text, default="")
    models_algorithms = Column(Text, default="")
    experimental_setup = Column(Text, default="")
    key_results = Column(Text, default="")
    major_findings = Column(Text, default="")
    limitations = Column(Text, default="")
    future_work = Column(Text, default="")
    research_contribution = Column(Text, default="")
    keywords_json = Column(Text, default="[]")
    key_takeaways_json = Column(Text, default="[]")
    citation = Column(Text, default="")
    model_used = Column(String(100), default="heuristic")
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)

    paper = relationship("Paper", back_populates="summary")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scope_type = Column(String(50), default="library")  # paper, project, library
    scope_id = Column(Integer, nullable=True)
    title = Column(String(300), default="Research Conversation")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    citations_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class ResearchNote(Base):
    __tablename__ = "research_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=True)
    page_number = Column(Integer, nullable=True)
    title = Column(String(250), nullable=False)
    content = Column(Text, nullable=False)
    tags_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    project = relationship("ResearchProject", back_populates="notes")
    paper = relationship("Paper", back_populates="notes")


class ExportReport(Base):
    __tablename__ = "export_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    report_type = Column(String(100), nullable=False)  # research_report, literature_review, etc.
    format = Column(String(20), nullable=False)  # pdf, docx, md, json, bibtex
    citation_style = Column(String(50), default="IEEE")
    project_id = Column(Integer, ForeignKey("research_projects.id", ondelete="SET NULL"), nullable=True, index=True)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    status = Column(String(50), default="completed")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(String(100), primary_key=True)
    job_type = Column(String(100), nullable=False)
    status = Column(String(50), default="queued")  # queued, running, completed, failed
    progress = Column(Integer, default=0)
    payload_json = Column(Text, default="{}")
    result_json = Column(Text, default="{}")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class DeploymentRecord(Base):
    __tablename__ = "deployment_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(50), nullable=False)
    commit_hash = Column(String(100), nullable=False)
    build_number = Column(String(50), default="#1")
    environment = Column(String(50), default="development")
    status = Column(String(50), default="successful")
    deployed_at = Column(DateTime, default=datetime.datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class ProviderHealthRecord(Base):
    __tablename__ = "provider_health_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_name = Column(String(100), nullable=False)
    status = Column(String(50), default="healthy")  # healthy, degraded, unavailable
    latency_ms = Column(Float, default=0.0)
    error = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=datetime.datetime.utcnow)
