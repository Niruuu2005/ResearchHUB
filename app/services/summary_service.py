import json
import logging
import re
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.database import Paper, PaperChunk, PaperSummary, ResearchProject, ProjectPaper
from app.models.schemas import CollectionSummaryOut, PaperSummaryOut
from app.services.llm_service import LLMService
from app.utils.citations import format_ieee

logger = logging.getLogger(__name__)


class SummaryService:
    """Generates structured single-paper summaries and multi-paper collection reviews."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()

    def _to_summary_out(self, paper: Paper, summary: PaperSummary) -> PaperSummaryOut:
        author_names = [a.author_name for a in paper.authors]
        return PaperSummaryOut(
            paper_id=paper.id,
            title=paper.title,
            authors=author_names,
            year=paper.year,
            venue=paper.venue,
            doi=paper.doi,
            research_problem=summary.research_problem,
            objective=summary.objective,
            background=summary.background,
            methodology=summary.methodology,
            dataset=summary.dataset,
            models_algorithms=summary.models_algorithms,
            experimental_setup=summary.experimental_setup,
            key_results=summary.key_results,
            major_findings=summary.major_findings,
            limitations=summary.limitations,
            future_work=summary.future_work,
            research_contribution=summary.research_contribution,
            keywords=json.loads(summary.keywords_json or "[]"),
            key_takeaways=json.loads(summary.key_takeaways_json or "[]"),
            citation=summary.citation,
            model_used=summary.model_used,
            generated_at=summary.generated_at,
        )

    def list_summaries(self, db: Session) -> List[PaperSummaryOut]:
        """Return saved paper summaries only — does not auto-generate."""
        rows = (
            db.query(PaperSummary, Paper)
            .join(Paper, Paper.id == PaperSummary.paper_id)
            .order_by(PaperSummary.generated_at.desc())
            .all()
        )
        return [self._to_summary_out(paper, summary) for summary, paper in rows]

    def summarize_paper(self, db: Session, paper_id: int) -> PaperSummaryOut:
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise ValueError(f"Paper with ID {paper_id} not found.")

        # Check existing summary
        existing = db.query(PaperSummary).filter(PaperSummary.paper_id == paper_id).first()
        if existing:
            return self._to_summary_out(paper, existing)

        # Retrieve text sample from chunks or abstract
        chunks = db.query(PaperChunk).filter(PaperChunk.paper_id == paper_id).limit(6).all()
        if chunks:
            text_sample = " ".join([c.content for c in chunks])
        elif paper.abstract:
            text_sample = paper.abstract
        else:
            text_sample = f"{paper.title}. Published in {paper.year or 'recent years'}."

        author_names = [a.author_name for a in paper.authors]
        citation = format_ieee(author_names, paper.title, paper.venue, paper.year, paper.doi)

        data = self.llm.extract_structured_summary(paper.title, author_names, text_sample)

        summary_db = PaperSummary(
            paper_id=paper.id,
            research_problem=data["research_problem"],
            objective=data["objective"],
            background=data["background"],
            methodology=data["methodology"],
            dataset=data["dataset"],
            models_algorithms=data["models_algorithms"],
            experimental_setup=data["experimental_setup"],
            key_results=data["key_results"],
            major_findings=data["major_findings"],
            limitations=data["limitations"],
            future_work=data["future_work"],
            research_contribution=data["research_contribution"],
            keywords_json=json.dumps(data["keywords"]),
            key_takeaways_json=json.dumps(data["key_takeaways"]),
            citation=citation,
            model_used=data["model_used"],
        )
        db.add(summary_db)
        db.commit()
        db.refresh(summary_db)

        return PaperSummaryOut(
            paper_id=paper.id,
            title=paper.title,
            authors=author_names,
            year=paper.year,
            venue=paper.venue,
            doi=paper.doi,
            research_problem=summary_db.research_problem,
            objective=summary_db.objective,
            background=summary_db.background,
            methodology=summary_db.methodology,
            dataset=summary_db.dataset,
            models_algorithms=summary_db.models_algorithms,
            experimental_setup=summary_db.experimental_setup,
            key_results=summary_db.key_results,
            major_findings=summary_db.major_findings,
            limitations=summary_db.limitations,
            future_work=summary_db.future_work,
            research_contribution=summary_db.research_contribution,
            keywords=data["keywords"],
            key_takeaways=data["key_takeaways"],
            citation=citation,
            model_used=summary_db.model_used,
            generated_at=summary_db.generated_at,
        )

    def summarize_project(self, db: Session, project_id: int) -> CollectionSummaryOut:
        project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        papers = (
            db.query(Paper)
            .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
            .filter(ProjectPaper.project_id == project_id)
            .all()
        )

        refs = []
        title_tokens = {}
        method_bits = []
        finding_bits = []
        limitation_bits = []
        future_bits = []
        abstracts_present = 0

        for p in papers:
            authors = [a.author_name for a in p.authors]
            refs.append(format_ieee(authors, p.title, p.venue, p.year, p.doi))
            if p.abstract:
                abstracts_present += 1
            for tok in re.findall(r"[A-Za-z]{5,}", (p.title or "").lower()):
                if tok in ("paper", "study", "using", "based", "toward", "towards", "approach"):
                    continue
                title_tokens[tok] = title_tokens.get(tok, 0) + 1

            existing = db.query(PaperSummary).filter(PaperSummary.paper_id == p.id).first()
            if existing:
                if existing.methodology and not existing.methodology.startswith("Not stated"):
                    method_bits.append(f"'{p.title}': {existing.methodology[:180]}")
                if existing.major_findings and not existing.major_findings.startswith("Not stated"):
                    finding_bits.append(f"'{p.title}': {existing.major_findings[:180]}")
                if existing.limitations and not existing.limitations.startswith("Not stated"):
                    limitation_bits.append(f"'{p.title}': {existing.limitations[:180]}")
                if existing.future_work and not existing.future_work.startswith("Not stated"):
                    future_bits.append(f"'{p.title}': {existing.future_work[:180]}")
            elif p.abstract:
                finding_bits.append(f"'{p.title}': {p.abstract[:200]}")

        themes = [t.capitalize() for t, _ in sorted(title_tokens.items(), key=lambda kv: -kv[1])[:6]]
        if not themes:
            themes = [project.name] if papers else []

        n = len(papers)
        none_msg = "No structured summaries or abstracts available yet for this project."

        return CollectionSummaryOut(
            project_id=project.id,
            project_name=project.name,
            papers_analyzed=n,
            major_themes=themes,
            common_methodologies=(
                "\n".join(method_bits[:8])
                if method_bits
                else (
                    f"{n} papers in '{project.name}'. Generate per-paper summaries to populate methodology synthesis."
                    if n
                    else none_msg
                )
            ),
            major_findings=(
                "\n".join(finding_bits[:8])
                if finding_bits
                else (
                    f"{abstracts_present}/{n} papers have abstracts stored; generate summaries for deeper findings."
                    if n
                    else none_msg
                )
            ),
            conflicting_findings=(
                "Conflicts are not inferred automatically. Compare the per-paper findings above directly."
                if finding_bits
                else "Insufficient extracted findings to identify conflicts."
            ),
            research_gaps=(
                "\n".join(limitation_bits[:8])
                if limitation_bits
                else "No author-stated limitations were found in stored summaries."
            ),
            emerging_trends=(
                f"Title-token themes in this project: {', '.join(themes)}."
                if themes
                else "Add papers to derive theme trends from titles."
            ),
            future_opportunities=(
                "\n".join(future_bits[:8])
                if future_bits
                else "No author-stated future-work text was available in stored summaries."
            ),
            references=refs,
            generated_at=datetime.utcnow(),
        )

    def list_summaries(self, db: Session):
        from app.models.database import PaperSummary
        records = db.query(PaperSummary).order_by(PaperSummary.generated_at.desc()).all()
        results = []
        for s in records:
            paper = s.paper
            if not paper:
                continue
            author_names = [a.author_name for a in paper.authors]
            results.append(
                PaperSummaryOut(
                    paper_id=paper.id,
                    title=paper.title,
                    authors=author_names,
                    year=paper.year,
                    venue=paper.venue,
                    doi=paper.doi,
                    research_problem=s.research_problem,
                    objective=s.objective,
                    background=s.background,
                    methodology=s.methodology,
                    dataset=s.dataset,
                    models_algorithms=s.models_algorithms,
                    experimental_setup=s.experimental_setup,
                    key_results=s.key_results,
                    major_findings=s.major_findings,
                    limitations=s.limitations,
                    future_work=s.future_work,
                    research_contribution=s.research_contribution,
                    keywords=json.loads(s.keywords_json or "[]"),
                    key_takeaways=json.loads(s.key_takeaways_json or "[]"),
                    citation=s.citation or "",
                    model_used=s.model_used or "deterministic",
                    generated_at=s.generated_at or datetime.utcnow(),
                )
            )
        return results
