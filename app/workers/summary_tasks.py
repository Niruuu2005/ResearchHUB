import logging
from app.db.session import SessionLocal
from app.services.summary_service import SummaryService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="generate_paper_summary_task")
def generate_paper_summary_task(paper_id: int):
    """Asynchronously generates 16-parameter structured paper summary."""
    logger.info(f"Starting asynchronous summary extraction for paper {paper_id}")
    with SessionLocal() as db:
        try:
            service = SummaryService()
            summary = service.summarize_paper(db, paper_id)
            logger.info(f"Asynchronous summary completed for paper {paper_id}")
            return {"status": "success", "paper_id": paper_id, "title": summary.title}
        except Exception as exc:
            logger.error(f"Failed to generate summary for paper {paper_id}: {exc}")
            raise


@celery_app.task(name="generate_project_summary_task")
def generate_project_summary_task(project_id: int):
    """Asynchronously synthesizes project collection review."""
    logger.info(f"Starting asynchronous collection summary for project {project_id}")
    with SessionLocal() as db:
        try:
            service = SummaryService()
            summary = service.summarize_project(db, project_id)
            logger.info(f"Asynchronous collection summary completed for project {project_id}")
            return {"status": "success", "project_id": project_id, "papers": summary.papers_analyzed}
        except Exception as exc:
            logger.error(f"Failed to summarize collection for project {project_id}: {exc}")
            raise
