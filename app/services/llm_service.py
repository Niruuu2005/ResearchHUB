import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings
from app.models.schemas import CitationItem

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were", "have", "has",
    "been", "into", "onto", "over", "under", "between", "among", "using", "based", "their",
    "which", "while", "where", "when", "than", "then", "also", "such", "these", "those",
    "about", "after", "before", "within", "without", "through", "during", "other", "more",
}


class LLMService:
    """Multi-provider LLM interface. Offline mode quotes retrieved/paper text only — never invents findings."""

    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model

    async def answer_question(self, question: str, citations: List[CitationItem]) -> str:
        """Answer a researcher's question grounded strictly on retrieved chunks."""
        if not citations:
            return (
                "No paper text is available yet for this question. "
                "Save papers with abstracts from Discover, or ingest a PDF so RAG can retrieve methodology and dataset details."
            )

        context_str = "\n\n".join([
            f"[Source {i+1}] Paper: {c.paper_title} (Page {c.page or 1}, Section {c.section or 'General'}):\n{c.snippet}"
            for i, c in enumerate(citations)
        ])

        only_metadata = all((c.section or "").lower() in ("metadata", "") and "No abstract" in (c.snippet or "") for c in citations)
        if only_metadata:
            titles = ", ".join(sorted({c.paper_title for c in citations if c.paper_title})[:3])
            return (
                f"Only bibliographic metadata is available for: {titles}. "
                "No abstract or PDF text is indexed yet, so methodology and dataset details cannot be explained. "
                "Re-run Discover/Save (abstracts are now stored) or upload/ingest the PDF, then ask again."
            )

        if self.provider == "openai" and self.api_key:
            try:
                return await self._call_openai_chat(question, context_str)
            except Exception as e:
                logger.warning(f"OpenAI call failed: {e}. Falling back to grounded extract.")

        if self.provider == "gemini" and self.api_key:
            try:
                return await self._call_gemini_chat(question, context_str)
            except Exception as e:
                logger.warning(f"Gemini call failed: {e}. Falling back to grounded extract.")

        if self.provider == "ollama":
            try:
                return await self._call_ollama_chat(question, context_str)
            except Exception as e:
                logger.warning(f"Ollama call failed: {e}. Falling back to grounded extract.")

        return self._heuristic_answer(question, citations)

    async def _call_openai_chat(self, question: str, context: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model or "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are ResearchOps AI assistant. Answer the question using ONLY "
                                "the provided context citations. State facts clearly with reference numbers. "
                                "If the context is insufficient, say so explicitly."
                            ),
                        },
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
                    ],
                    "temperature": 0.2,
                },
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    async def _call_gemini_chat(self, question: str, context: str) -> str:
        model = self.model or "gemini-3.6-flash"
        if model.startswith("gpt-"):
            model = "gemini-3.6-flash"
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.api_key}"
        )
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                url,
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": (
                                        "You are ResearchOps AI. Answer using ONLY the provided context. "
                                        "If the context is an abstract (not full PDF text), extract whatever "
                                        "the abstract states about methodology, datasets, evaluation, findings, "
                                        "and limitations. Quote or paraphrase those points clearly. "
                                        "If a detail is not in the context, say it is not stated in the available "
                                        "abstract/text and suggest ingesting the PDF for deeper detail. "
                                        "Cite source numbers when possible.\n\n"
                                        f"Context:\n{context}\n\nQuestion: {question}"
                                    )
                                }
                            ]
                        }
                    ],
                    "generationConfig": {"temperature": 0.2},
                },
            )
            data = resp.json()
            if resp.status_code >= 400:
                err = data.get("error", {}).get("message") or resp.text[:300]
                raise RuntimeError(f"Gemini HTTP {resp.status_code}: {err}")
            candidates = data.get("candidates") or []
            if not candidates:
                raise RuntimeError(f"Gemini returned no candidates: {data}")
            parts = candidates[0].get("content", {}).get("parts") or []
            if not parts:
                raise RuntimeError("Gemini returned empty content")
            return parts[0].get("text", "").strip()

    async def _call_ollama_chat(self, question: str, context: str) -> str:
        base = (settings.ollama_base_url or "http://localhost:11434").rstrip("/")
        model = self.model or "llama3.2"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Answer using ONLY the provided research context. "
                                "If the context is insufficient, say so explicitly."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Context:\n{context}\n\nQuestion: {question}",
                        },
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            message = data.get("message") or {}
            content = message.get("content") or data.get("response") or ""
            if not content.strip():
                raise RuntimeError("Empty Ollama response")
            return content.strip()

    def _heuristic_answer(self, question: str, citations: List[CitationItem]) -> str:
        """Quote retrieved snippets only — no invented analysis."""
        if not citations:
            return (
                f"No indexed paper content matched '{question}'. "
                "Upload or fetch PDFs so retrieval can ground answers in research text."
            )

        q_tokens = [w for w in re.findall(r"[a-z0-9]+", question.lower()) if len(w) > 2]
        ranked = sorted(
            citations,
            key=lambda c: sum(1 for w in q_tokens if w in (c.snippet or "").lower()),
            reverse=True,
        )

        lines = []
        if self.provider in ("openai", "gemini", "ollama") and (
            self.api_key or self.provider == "ollama"
        ):
            lines.append(
                f"LLM ({self.provider}) did not return a response; "
                "showing a grounded extract from retrieved paper text."
            )
        else:
            lines.append(
                "Offline mode (no LLM configured): answer is assembled only from retrieved paper text."
            )
        lines.append("")
        for i, c in enumerate(ranked[:4], 1):
            snippet = (c.snippet or "").strip()
            lines.append(
                f"[{i}] {c.paper_title} (p. {c.page or 1}, {c.section or 'Main'}):\n\"{snippet}\""
            )
            lines.append("")
        return "\n".join(lines).strip()

    def extract_structured_summary(self, title: str, authors: List[str], text_sample: str) -> Dict[str, Any]:
        """Build structured fields only from provided title/authors/text — never invent statistics."""
        text = (text_sample or "").strip()
        title = (title or "").strip() or "Untitled"
        sentences = self._sentences(text)

        def pick(patterns: List[str], fallback: str) -> str:
            for s in sentences:
                low = s.lower()
                if any(p in low for p in patterns):
                    return s.strip()
            return fallback

        unavailable = "Not stated in available abstract or extracted text."
        first = sentences[0] if sentences else unavailable
        keywords = self._keywords_from_text(f"{title}. {text}")

        research_problem = pick(
            ["problem", "challenge", "issue", "address", "investigate", "study"],
            first if first != unavailable else f"Focus of the work as indicated by the title: {title}.",
        )
        objective = pick(
            ["aim", "objective", "propose", "we present", "this paper", "goal"],
            first,
        )
        methodology = pick(
            ["method", "approach", "algorithm", "framework", "model", "technique", "pipeline"],
            unavailable,
        )
        dataset = pick(
            ["dataset", "corpus", "benchmark", "data set", "collection of"],
            unavailable,
        )
        models = pick(
            ["model", "network", "transformer", "architecture", "algorithm"],
            unavailable,
        )
        experimental = pick(
            ["experiment", "evaluation", "setup", "baseline", "metric", "measure"],
            unavailable,
        )
        key_results = pick(
            ["result", "achieve", "improve", "outperform", "accuracy", "performance", "show that"],
            unavailable,
        )
        major_findings = pick(
            ["find", "conclude", "demonstrate", "indicate", "suggest"],
            key_results if key_results != unavailable else first,
        )
        limitations = pick(
            ["limit", "constraint", "drawback", "however", "although", "weakness"],
            unavailable,
        )
        future_work = pick(
            ["future", "further", "next step", "extend", "remain open"],
            unavailable,
        )
        contribution = pick(
            ["contribution", "novel", "propose", "introduce", "we present"],
            f"As indicated by the title and available text: {title}.",
        )
        background = pick(
            ["background", "prior", "previous", "recent", "existing", "literature"],
            first,
        )

        takeaways = []
        for s in sentences[:3]:
            if s.strip():
                takeaways.append(s.strip()[:220])
        if not takeaways:
            takeaways = [f"Title: {title}", "Insufficient body text for further takeaways."]

        return {
            "research_problem": research_problem,
            "objective": objective,
            "background": background,
            "methodology": methodology,
            "dataset": dataset,
            "models_algorithms": models,
            "experimental_setup": experimental,
            "key_results": key_results,
            "major_findings": major_findings,
            "limitations": limitations,
            "future_work": future_work,
            "research_contribution": contribution,
            "keywords": keywords[:8] or [w for w in re.findall(r"[A-Za-z]{5,}", title)][:6],
            "key_takeaways": takeaways[:5],
            "model_used": "offline-text-extract",
        }

    @staticmethod
    def _sentences(text: str) -> List[str]:
        if not text:
            return []
        parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
        return [p.strip() for p in parts if len(p.strip()) > 25][:40]

    @staticmethod
    def _keywords_from_text(text: str) -> List[str]:
        counts: Dict[str, int] = {}
        for tok in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text.lower()):
            if tok in _STOPWORDS:
                continue
            counts[tok] = counts.get(tok, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [w.capitalize() for w, _ in ranked[:8]]
