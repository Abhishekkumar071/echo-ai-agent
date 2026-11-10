"""
Embedding service for generating semantic representations of text.
Resilient design: if embedding model loading or generation fails,
it returns None instead of raising an unhandled exception (Change 2).
"""
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global cached embedding model instance
_EMBEDDING_MODEL: Any = None


def get_embedding_model():
    """Lazily load the embedding model to avoid startup slowdown."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is not None:
        return _EMBEDDING_MODEL

    settings = get_settings()
    try:
        # Try fastembed (lightweight ONNX runtime, 768-dim BAAI/bge-base-en-v1.5)
        from fastembed import TextEmbedding
        model_name = "BAAI/bge-base-en-v1.5"
        logger.info("Loading FastEmbed model: %s", model_name)
        _EMBEDDING_MODEL = TextEmbedding(model_name=model_name)
        return _EMBEDDING_MODEL
    except ImportError:
        logger.info("FastEmbed not installed, checking sentence-transformers...")

    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SentenceTransformer model: %s", settings.embedding_model)
        _EMBEDDING_MODEL = SentenceTransformer(settings.embedding_model)
        return _EMBEDDING_MODEL
    except Exception as exc:
        logger.warning("Could not load local embedding model (%s). Embeddings will be disabled: %s", type(exc).__name__, exc)
        return None


class EmbeddingService:
    def __init__(self):
        self.settings = get_settings()

    async def generate_embedding(self, text: str) -> list[float] | None:
        """
        Generate a 768-dimensional normalized embedding vector for the given text.
        Returns None if generation fails or model is unavailable.
        Never throws unhandled exceptions to caller.
        """
        if not text or not text.strip():
            return None

        clean_text = text.strip().replace("\n", " ")

        try:
            model = get_embedding_model()
            if model is None:
                return None

            # FastEmbed interface
            if hasattr(model, "embed"):
                embeddings = list(model.embed([clean_text]))
                if embeddings and len(embeddings) > 0:
                    vector = [float(v) for v in embeddings[0]]
                    # Ensure 768 dim
                    if len(vector) == self.settings.embedding_dim:
                        return vector
                    # If model returned different dimension (e.g. 384), pad or truncate to 768
                    if len(vector) < self.settings.embedding_dim:
                        return vector + [0.0] * (self.settings.embedding_dim - len(vector))
                    return vector[:self.settings.embedding_dim]

            # SentenceTransformer interface
            if hasattr(model, "encode"):
                embedding = model.encode(clean_text, normalize_embeddings=True)
                vector = [float(v) for v in embedding]
                if len(vector) == self.settings.embedding_dim:
                    return vector
                if len(vector) < self.settings.embedding_dim:
                    return vector + [0.0] * (self.settings.embedding_dim - len(vector))
                return vector[:self.settings.embedding_dim]

        except Exception as exc:
            logger.warning("Embedding generation failed for text '%.40s...': %s", clean_text, exc)
            return None

        return None
