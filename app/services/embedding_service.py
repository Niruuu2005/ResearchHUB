import json
import logging
import math
from typing import List, Optional

logger = logging.getLogger(__name__)

_model_instance = None
_model_load_attempted = False


class EmbeddingService:
    """Generates dense vector embeddings for semantic document retrieval."""

    def __init__(self):
        self._dim = 384

    def _resolve_provider(self) -> str:
        from app.config import settings
        provider = (settings.embedding_provider or "auto").lower()
        if provider == "auto":
            # Prefer real sentence-transformers when installed; otherwise lexical hash.
            try:
                import sentence_transformers  # noqa: F401
                return "sentence-transformers"
            except Exception:
                return "hash"
        if provider in ("heuristic", "hash"):
            return "hash"
        return provider

    def _get_transformer_model(self):
        global _model_instance, _model_load_attempted
        if self._resolve_provider() != "sentence-transformers":
            return None

        if _model_instance is None and not _model_load_attempted:
            _model_load_attempted = True
            try:
                from sentence_transformers import SentenceTransformer
                from app.config import settings

                model_name = settings.embedding_model or "all-MiniLM-L6-v2"
                _model_instance = SentenceTransformer(model_name)
                logger.info(f"SentenceTransformer model loaded: {model_name}")
            except Exception as e:
                logger.warning(
                    f"Could not load SentenceTransformer: {e}. Using lexical hash embeddings."
                )
                _model_instance = False
        return _model_instance if _model_instance is not False else None

    def embed_text(self, text: str) -> List[float]:
        """Generate normalized 384-dim embedding vector."""
        if not text:
            return [0.0] * self._dim

        model = self._get_transformer_model()
        if model:
            try:
                vector = model.encode(text, normalize_embeddings=True)
                return vector.tolist()
            except Exception as exc:
                logger.warning(f"Model encode failed: {exc}. Using lexical hash fallback.")

        return self._deterministic_embed(text)

    def provider_in_use(self) -> str:
        if self._get_transformer_model():
            return "sentence-transformers"
        return "hash"

    def _deterministic_embed(self, text: str) -> List[float]:
        """Lexical bag-of-words hash embedding (dev fallback — not semantic ST vectors)."""
        vec = [0.0] * self._dim
        words = text.lower().split()
        for i, word in enumerate(words):
            h = hash(word)
            idx1 = abs(h) % self._dim
            idx2 = abs(h // 384) % self._dim
            weight = 1.0 / (1.0 + math.log(1 + i))
            vec[idx1] += weight
            vec[idx2] += weight * 0.5

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            return [x / norm for x in vec]
        return [1.0 / math.sqrt(self._dim)] * self._dim

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two unit vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        return max(-1.0, min(1.0, dot))
