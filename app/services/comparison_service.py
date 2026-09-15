import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.database import Paper
from app.models.schemas import ComparisonResponse, PaperComparisonColumn
from app.services.summary_service import SummaryService

logger = logging.getLogger(__name__)

_UNSTATED = "Not stated in available abstract or extracted text."


class ComparisonService:
    """Builds comparison matrices from paper summaries and synthesizes only from those fields."""

    def __init__(self, summary_service: Optional[SummaryService] = None):
        self.summary_service = summary_service or SummaryService()

    def compare_papers(self, db: Session, paper_ids: List[int]) -> ComparisonResponse:
        if len(paper_ids) < 2 or len(paper_ids) > 5:
            raise ValueError("Comparison requires between 2 and 5 papers.")

        # Preserve request order
        ordered_ids = list(dict.fromkeys(paper_ids))
        papers_by_id = {
            p.id: p for p in db.query(Paper).filter(Paper.id.in_(ordered_ids)).all()
        }
        papers = [papers_by_id[i] for i in ordered_ids if i in papers_by_id]
        if len(papers) < 2:
            raise ValueError("At least 2 valid papers must be found in the database.")

        columns: List[PaperComparisonColumn] = []
        for p in papers:
            s = self.summary_service.summarize_paper(db, p.id)
            columns.append(
                PaperComparisonColumn(
                    paper_id=p.id,
                    title=p.title,
                    authors=s.authors,
                    year=p.year,
                    research_problem=s.research_problem,
                    objective=s.objective,
                    dataset=s.dataset,
                    methodology=s.methodology,
                    model=s.models_algorithms,
                    results=s.key_results,
                    strengths=s.major_findings,
                    limitations=s.limitations,
                    future_work=s.future_work,
                )
            )

        return ComparisonResponse(
            matrix=columns,
            similarities=self._similarities(columns),
            differences=self._differences(columns),
            methodological_trends=self._methods(columns),
            research_gaps=self._gaps(columns),
        )

    def _stated(self, value: str) -> bool:
        v = (value or "").strip()
        return bool(v) and v != _UNSTATED and not v.lower().startswith("not stated")

    def _similarities(self, columns: List[PaperComparisonColumn]) -> str:
        years = [c.year for c in columns if c.year]
        year_bit = (
            f" Publication years in this set: {', '.join(str(y) for y in sorted(set(years)))}."
            if years
            else ""
        )
        shared_method_terms = self._shared_tokens([c.methodology for c in columns if self._stated(c.methodology)])
        method_bit = (
            f" Overlapping methodology terms: {', '.join(shared_method_terms[:8])}."
            if shared_method_terms
            else " No overlapping methodology wording was detected across stated fields."
        )
        titles = "; ".join(f"'{c.title}'" for c in columns)
        return (
            f"Compared {len(columns)} papers: {titles}.{year_bit}{method_bit} "
            "Similarity notes are derived only from structured summary fields extracted from each paper's available text."
        )

    def _differences(self, columns: List[PaperComparisonColumn]) -> str:
        lines = []
        for c in columns:
            bits = []
            if self._stated(c.research_problem):
                bits.append(f"problem: {c.research_problem[:160]}")
            if self._stated(c.methodology):
                bits.append(f"method: {c.methodology[:160]}")
            if self._stated(c.results):
                bits.append(f"results: {c.results[:160]}")
            if not bits:
                bits.append("insufficient extracted text for detailed contrast")
            lines.append(f"- '{c.title}' ({c.year or 'n.d.'}): " + " | ".join(bits))
        return "Per-paper contrasts from extracted fields:\n" + "\n".join(lines)

    def _methods(self, columns: List[PaperComparisonColumn]) -> str:
        stated = [c for c in columns if self._stated(c.methodology)]
        if not stated:
            return "No methodology statements were available in the extracted paper text."
        lines = [f"- '{c.title}': {c.methodology}" for c in stated]
        return "Methodologies as stated in available text:\n" + "\n".join(lines)

    def _gaps(self, columns: List[PaperComparisonColumn]) -> str:
        stated = [c for c in columns if self._stated(c.limitations) or self._stated(c.future_work)]
        if not stated:
            return (
                "No explicit limitations or future-work statements were found in the available abstracts/extracted text. "
                "Gaps cannot be asserted beyond missing metadata."
            )
        lines = []
        for c in stated:
            lim = c.limitations if self._stated(c.limitations) else None
            fut = c.future_work if self._stated(c.future_work) else None
            parts = []
            if lim:
                parts.append(f"limitations: {lim}")
            if fut:
                parts.append(f"future work: {fut}")
            lines.append(f"- '{c.title}': " + " | ".join(parts))
        return "Author-stated limitations / future work from extracted text:\n" + "\n".join(lines)

    @staticmethod
    def _shared_tokens(texts: List[str]) -> List[str]:
        if len(texts) < 2:
            return []
        sets = []
        stop = {"the", "and", "for", "with", "from", "that", "this", "using", "based", "into"}
        for t in texts:
            toks = {w.lower() for w in __import__("re").findall(r"[A-Za-z]{4,}", t) if w.lower() not in stop}
            sets.append(toks)
        shared = set.intersection(*sets) if sets else set()
        return sorted(shared)[:12]
