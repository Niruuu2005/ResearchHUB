import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.database import Paper, ProjectPaper, ResearchProject
from app.models.schemas import LiteratureReviewOut
from app.utils.citations import format_citation

logger = logging.getLogger(__name__)


class LiteratureReviewService:
    """Builds an 11-section literature review from saved paper metadata (titles, venues, abstracts, citations)."""

    def build_literature_review(
        self,
        db: Session,
        project_id: Optional[int] = None,
        paper_ids: Optional[List[int]] = None,
        topic: Optional[str] = None,
        citation_style: str = "IEEE",
    ) -> LiteratureReviewOut:
        papers: List[Paper] = []
        resolved_project_id: Optional[int] = None
        project_name = (topic or "").strip() or "Scholarly Literature Review"

        # Prefer explicit paper_ids when provided; otherwise project; otherwise recent library papers.
        if paper_ids:
            requested = list(dict.fromkeys(paper_ids))  # preserve order, dedupe
            found = {
                p.id: p
                for p in db.query(Paper).filter(Paper.id.in_(requested)).all()
            }
            missing = [pid for pid in requested if pid not in found]
            if missing:
                raise ValueError(f"Paper ID(s) not found in library: {missing}")
            papers = [found[pid] for pid in requested]
            if project_id:
                project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
                if not project:
                    raise ValueError(f"Project with ID {project_id} not found.")
                resolved_project_id = project.id
                if not topic:
                    project_name = project.name
        elif project_id is not None:
            project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
            if not project:
                raise ValueError(f"Project with ID {project_id} not found.")
            resolved_project_id = project.id
            if not topic:
                project_name = project.name
            papers = (
                db.query(Paper)
                .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
                .filter(ProjectPaper.project_id == project_id)
                .order_by(Paper.created_at.desc())
                .all()
            )
            if not papers:
                raise ValueError(
                    f"Project '{project.name}' has no papers. Add papers to the workspace before generating a review."
                )
        else:
            papers = db.query(Paper).order_by(Paper.created_at.desc()).limit(10).all()
            if not papers:
                raise ValueError(
                    "No papers available to construct a literature review. Save papers to your library first."
                )

        citation_style = (citation_style or "IEEE").strip()
        references: List[str] = []
        for idx, p in enumerate(papers, 1):
            authors = [a.author_name for a in p.authors]
            cite_str = format_citation(citation_style, authors, p.title, p.venue, p.year, p.doi)
            if citation_style.upper() == "IEEE":
                references.append(f"[{idx}] {cite_str}")
            else:
                references.append(cite_str)

        resolved_ids = [p.id for p in papers]
        sections = self._build_sections(project_name, papers, citation_style)

        return LiteratureReviewOut(
            title=f"Literature Review: {project_name}",
            sections=sections,
            references=references,
            citation_style=citation_style,
            paper_ids=resolved_ids,
            project_id=resolved_project_id,
            papers_analyzed=len(papers),
            created_at=datetime.utcnow(),
        )

    def _build_sections(self, project_name: str, papers: List[Paper], citation_style: str) -> dict:
        n = len(papers)
        titles = [p.title for p in papers]
        years = sorted({p.year for p in papers if p.year})
        year_span = (
            f"{years[0]}–{years[-1]}" if len(years) > 1 else (str(years[0]) if years else "n/a")
        )
        venues = [p.venue for p in papers if p.venue]
        sources = sorted({p.source for p in papers if p.source})
        oa_count = sum(1 for p in papers if p.open_access)

        def cite_marker(idx: int) -> str:
            return f"[{idx}]" if citation_style.upper() == "IEEE" else f"({idx})"

        paper_blurbs = []
        abstract_quotes = []
        limitation_quotes = []
        for i, p in enumerate(papers, 1):
            authors = ", ".join(a.author_name for a in p.authors[:3]) or "Unknown authors"
            if len(p.authors) > 3:
                authors += " et al."
            venue_bit = f"; venue: {p.venue}" if p.venue else ""
            year_bit = f" ({p.year})" if p.year else ""
            abstract = (p.abstract or "").strip()
            if abstract:
                snippet = abstract[:320].rstrip() + ("…" if len(abstract) > 320 else "")
                focus = f' Abstract: "{snippet}"'
                abstract_quotes.append(f"{cite_marker(i)} \"{snippet}\"")
                low = abstract.lower()
                if any(k in low for k in ("limitation", "future work", "challenge", "open problem", "however")):
                    limitation_quotes.append(f"{cite_marker(i)} '{p.title}': excerpt notes limits/challenges in abstract.")
            else:
                focus = " No abstract stored for this record."
            paper_blurbs.append(
                f"{cite_marker(i)} {p.title}{year_bit} — {authors}{venue_bit}.{focus}"
            )

        listed = "; ".join(f"{cite_marker(i)} '{t}'" for i, t in enumerate(titles, 1))
        venue_sentence = f" Venues present: {', '.join(venues[:8])}." if venues else " No venue metadata stored."
        source_sentence = f" Library sources: {', '.join(sources)}." if sources else ""

        findings_section = (
            "Quoted abstracts from the corpus:\n\n" + "\n\n".join(abstract_quotes)
            if abstract_quotes
            else "No abstracts are stored for the selected papers; findings cannot be quoted beyond titles and bibliographic fields."
        )
        gaps_section = (
            "\n".join(limitation_quotes)
            if limitation_quotes
            else "No abstracts in this selection explicitly mention limitations, challenges, or future work."
        )

        return {
            "1. Introduction": (
                f"Literature review for '{project_name}' covering {n} saved publication(s) "
                f"(year span: {year_span}).{source_sentence} "
                "Content below is restricted to titles, authors, venues, years, and abstracts stored in the library."
            ),
            "2. Background": (
                f"Included works: {listed}.{venue_sentence}"
            ),
            "3. Existing Approaches": (
                "Per-paper bibliographic synopsis with abstract excerpts where available:\n\n"
                + "\n\n".join(paper_blurbs)
            ),
            "4. Methodological Trends": (
                f"Open-access flag count: {oa_count}/{n}. "
                "Methodology wording is only available when present in abstracts or generated summaries; "
                "this section does not invent methods beyond stored metadata."
            ),
            "5. Comparative Analysis": (
                "Compare the per-paper abstracts and titles listed in section 3. "
                "No additional comparative claims are asserted beyond those records."
            ),
            "6. Major Findings": findings_section,
            "7. Challenges": (
                "Library-side data challenges for this selection: "
                f"{n - len(abstract_quotes)}/{n} papers lack abstracts; "
                f"{n - oa_count}/{n} are not marked open access. "
                "Author-stated research challenges appear only when present in abstracts (see section 8)."
            ),
            "8. Research Gaps": gaps_section,
            "9. Future Research Directions": (
                "Future directions are not synthesized beyond author text. "
                "Use Chat/RAG on indexed PDFs or configure an LLM provider for deeper generation."
            ),
            "10. Conclusion": (
                f"Reviewed {n} bibliographic record(s) for '{project_name}' ({year_span}) using {citation_style} references. "
                "All narrative claims above are limited to stored research metadata and abstract quotes."
            ),
        }
