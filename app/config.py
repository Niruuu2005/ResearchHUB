import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file() -> None:
    """Load key=value pairs from project-root .env into os.environ (does not override existing)."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


_load_env_file()


@dataclass(frozen=True)
class Settings:
    """Application configuration settings for ResearchOps AI."""

    app_name: str = os.getenv("APP_NAME", "ResearchOps AI")
    app_version: str = os.getenv("APP_VERSION", "2.0.0")
    debug: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./researchops.db")

    # Redis & Queue
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Storage Paths
    storage_provider: str = os.getenv("STORAGE_PROVIDER", "local")
    storage_path: str = os.getenv("STORAGE_PATH", "./data/documents")
    export_storage_path: str = os.getenv("EXPORT_STORAGE_PATH", "./data/exports")

    # Timeouts (seconds)
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10.0"))

    # Provider Limits & Settings
    max_papers_per_provider: int = int(os.getenv("MAX_PAPERS_PER_PROVIDER", "5"))
    enable_wikipedia: bool = os.getenv("ENABLE_WIKIPEDIA", "true").lower() in ("true", "1", "yes")
    enable_openalex: bool = os.getenv("ENABLE_OPENALEX", "true").lower() in ("true", "1", "yes")
    enable_crossref: bool = os.getenv("ENABLE_CROSSREF", "true").lower() in ("true", "1", "yes")

    # AI / LLM Configuration — openai | gemini | ollama | heuristic (offline extract)
    llm_provider: str = os.getenv("LLM_PROVIDER", "heuristic")
    llm_api_key: str = (
        os.getenv("LLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Embedding Provider — auto (ST if installed else hash) | sentence-transformers | hash
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "auto")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Document Processing Limits
    max_pdf_size_mb: int = int(os.getenv("MAX_PDF_SIZE_MB", "50"))

    # Etiquette User-Agent for public academic APIs
    user_agent: str = os.getenv(
        "USER_AGENT",
        "ResearchOpsAI/2.0.0 (DevOps Platform; mailto:researchops@example.edu)",
    )

    # Git & Deployment Metadata
    git_commit: str = os.getenv("GIT_COMMIT", "dev-local")
    build_number: str = os.getenv("BUILD_NUMBER", "build-1")
    app_env: str = os.getenv("APP_ENV", "development")


settings = Settings()

# Ensure local directories exist
Path(settings.storage_path).mkdir(parents=True, exist_ok=True)
Path(settings.export_storage_path).mkdir(parents=True, exist_ok=True)
