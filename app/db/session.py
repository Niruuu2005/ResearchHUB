import logging
from typing import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models.database import Base, DeploymentRecord

logger = logging.getLogger(__name__)

# Determine SQLite vs PostgreSQL connection options
is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _ensure_schema_columns():
    """Add columns introduced after initial create_all (SQLite/Postgres without Alembic)."""
    try:
        inspector = inspect(engine)
        if "export_reports" not in inspector.get_table_names():
            return
        columns = {col["name"] for col in inspector.get_columns("export_reports")}
        if "project_id" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE export_reports ADD COLUMN project_id INTEGER"))
            logger.info("Added export_reports.project_id column.")
    except Exception as exc:
        logger.warning(f"Schema column ensure skipped: {exc}")


def init_db():
    """Create database tables and populate initial records if necessary."""
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_schema_columns()
        logger.info("Database tables verified/created successfully.")

        # Seed initial deployment record if table is empty
        with SessionLocal() as db:
            existing_deployment = db.query(DeploymentRecord).first()
            if not existing_deployment:
                initial_deploy = DeploymentRecord(
                    version=settings.app_version,
                    commit_hash=settings.git_commit,
                    build_number=settings.build_number,
                    environment=settings.app_env,
                    status="successful",
                )
                db.add(initial_deploy)
                db.commit()
                logger.info(f"Initialized deployment tracking for {settings.app_version}.")
    except Exception as exc:
        logger.error(f"Failed to initialize database: {exc}")


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining database sessions per-request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
