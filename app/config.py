import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application configuration settings."""

    app_name: str = os.getenv("APP_NAME", "ResearchLite")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    debug: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Timeouts (seconds)
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10.0"))

    # Provider Limits
    max_papers_per_provider: int = int(os.getenv("MAX_PAPERS_PER_PROVIDER", "5"))

    # Etiquette User-Agent for public academic APIs
    user_agent: str = os.getenv(
        "USER_AGENT",
        "ResearchLite/1.0.0 (DevOps FA Project; mailto:researchlite@example.edu)",
    )


settings = Settings()
