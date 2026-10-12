import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.database import Paper, PaperAuthor, ProjectPaper, PaperDocument, ResearchProject
from app.models.schemas import PaperSaveRequest

logger = logging.getLogger(__name__)


class PaperService:
    """Manages paper persistence, library interactions, and user-isolated project associations."""

    @staticmethod
    def get_papers(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        project_id: Optional[int] = None,
        search: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Paper]:
        query = db.query(Paper)
        if user_id is not None:
            query = query.filter(Paper.user_id == str(user_id))
        if project_id:
            query = query.join(ProjectPaper).filter(ProjectPaper.project_id == project_id)
        if search:
            search_clean = f"%{search.strip().lower()}%"
            query = query.filter(Paper.title.ilike(search_clean))
        return query.order_by(Paper.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_paper_by_id(db: Session, paper_id: int, user_id: Optional[str] = None) -> Optional[Paper]:
        query = db.query(Paper).filter(Paper.id == paper_id)
        if user_id is not None:
            query = query.filter(Paper.user_id == str(user_id))
        return query.first()

    @staticmethod
    def save_paper(db: Session, payload: PaperSaveRequest, user_id: Optional[str] = None) -> Paper:
        # Check if paper with DOI already exists for this user
        paper = None
        user_str = str(user_id) if user_id else None

        if payload.doi:
            q = db.query(Paper).filter(Paper.doi == payload.doi.strip().lower())
            if user_str:
                q = q.filter(Paper.user_id == user_str)
            paper = q.first()

        if not paper:
            # Check normalized title for this user
            norm_title = payload.title.strip()
            q = db.query(Paper).filter(Paper.title.ilike(norm_title))
            if user_str:
                q = q.filter(Paper.user_id == user_str)
            paper = q.first()

        if not paper:
            paper = Paper(
                user_id=user_str,
                title=payload.title.strip(),
                abstract=payload.abstract or "",
                doi=(payload.doi.strip().lower() if payload.doi else None),
                year=payload.year,
                venue=payload.venue,
                source=payload.source,
                url=payload.url,
                open_access=payload.open_access,
                pdf_url=payload.pdf_url,
            )
            db.add(paper)
            db.flush()

            # Add authors
            for idx, author_name in enumerate(payload.authors):
                author = PaperAuthor(paper_id=paper.id, author_name=author_name.strip(), order_index=idx)
                db.add(author)
        else:
            # Enrich existing library record if discovery now has better metadata
            if payload.abstract and not (paper.abstract or "").strip():
                paper.abstract = payload.abstract
            if payload.venue and not paper.venue:
                paper.venue = payload.venue
            if payload.pdf_url and not paper.pdf_url:
                paper.pdf_url = payload.pdf_url
            if user_str and not paper.user_id:
                paper.user_id = user_str
            paper.open_access = payload.open_access or paper.open_access

        # Associate with project if specified and authorized
        if payload.project_id:
            project_query = db.query(ResearchProject).filter(ResearchProject.id == payload.project_id)
            if user_str:
                project_query = project_query.filter(ResearchProject.user_id == user_str)
            project = project_query.first()
            if project:
                existing_link = db.query(ProjectPaper).filter(
                    ProjectPaper.project_id == payload.project_id,
                    ProjectPaper.paper_id == paper.id,
                ).first()
                if not existing_link:
                    link = ProjectPaper(project_id=payload.project_id, paper_id=paper.id)
                    db.add(link)

        db.commit()
        db.refresh(paper)
        return paper

    @staticmethod
    def delete_paper(db: Session, paper_id: int, user_id: Optional[str] = None) -> bool:
        query = db.query(Paper).filter(Paper.id == paper_id)
        if user_id is not None:
            query = query.filter(Paper.user_id == str(user_id))
        paper = query.first()
        if not paper:
            return False
        db.delete(paper)
        db.commit()
        return True

    @staticmethod
    def get_related_papers(db: Session, paper_id: int, limit: int = 5, user_id: Optional[str] = None) -> List[dict]:
        target_query = db.query(Paper).filter(Paper.id == paper_id)
        if user_id is not None:
            target_query = target_query.filter(Paper.user_id == str(user_id))
        target = target_query.first()
        if not target:
            return []

        all_query = db.query(Paper).filter(Paper.id != paper_id)
        if user_id is not None:
            all_query = all_query.filter(Paper.user_id == str(user_id))
        all_papers = all_query.all()
        target_words = set(target.title.lower().split())

        scored = []
        for p in all_papers:
            p_words = set(p.title.lower().split())
            overlap = len(target_words.intersection(p_words))
            similarity = min(98, max(45, int((overlap / max(1, len(target_words))) * 100)))
            if p.year and target.year and abs(p.year - target.year) <= 2:
                similarity = min(99, similarity + 10)
            scored.append({
                "paper": p,
                "similarity_percent": similarity,
                "common_themes": list(target_words.intersection(p_words))[:3],
            })

        scored.sort(key=lambda x: x["similarity_percent"], reverse=True)
        return scored[:limit]
