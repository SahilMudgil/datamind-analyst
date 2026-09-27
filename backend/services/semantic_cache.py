import logging
import numpy as np
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from models.models import QueryCache
from services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.95


class SemanticCacheService:
    """Semantic Query Cache leveraging pgvector cosine similarity (>= 0.95)."""

    @staticmethod
    def _compute_cosine_similarity(vec1: List[float], vec2: Any) -> float:
        """Calculate cosine similarity between two vector lists/arrays."""
        try:
            a = np.array(vec1, dtype=np.float32)
            # vec2 can be a list, array, or pgvector string representation
            if isinstance(vec2, str):
                vec2 = [float(x) for x in vec2.strip("[]").split(",") if x.strip()]
            b = np.array(vec2, dtype=np.float32)

            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))
        except Exception as e:
            logger.debug(f"Error computing cosine similarity: {e}")
            return 0.0

    async def get_cached_query(
        self,
        connection_id: int,
        question_text: str,
        db: Session,
        threshold: float = SIMILARITY_THRESHOLD
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a semantically equivalent query has already been generated
        for this database connection with cosine similarity >= threshold.
        """
        if not question_text or not db:
            return None

        # 1. Compute embedding for incoming query
        query_emb = await embedding_service.get_embedding(question_text)
        if not query_emb:
            return None

        try:
            # Check dialect
            dialect_name = getattr(db.get_bind(), "dialect", None)
            dialect_name = dialect_name.name if dialect_name else "sqlite"

            if dialect_name == "postgresql":
                # pgvector cosine distance: distance = 1 - cosine_similarity
                # similarity >= 0.95 corresponds to cosine_distance <= 0.05
                max_distance = 1.0 - threshold
                match = db.query(
                    QueryCache,
                    QueryCache.question_embedding.cosine_distance(query_emb).label("distance")
                ).filter(
                    QueryCache.connection_id == connection_id
                ).order_by(
                    "distance"
                ).first()

                if match and match.distance is not None and match.distance <= max_distance:
                    cache_item = match[0]
                    sim = 1.0 - float(match.distance)
                    cache_item.hit_count = (cache_item.hit_count or 1) + 1
                    cache_item.last_used_at = datetime.utcnow()
                    db.commit()

                    logger.info(f"Semantic Cache HIT ({sim:.4f} >= {threshold}): '{question_text}' -> '{cache_item.question_text}'")
                    return {
                        "is_cached": True,
                        "generated_sql": cache_item.generated_sql,
                        "similarity": round(sim, 4),
                        "hit_count": cache_item.hit_count,
                        "cached_question": cache_item.question_text
                    }
            else:
                # Python / NumPy Cosine Distance Fallback (SQLite test environments)
                entries = db.query(QueryCache).filter(QueryCache.connection_id == connection_id).all()
                best_sim = -1.0
                best_entry = None

                for entry in entries:
                    if entry.question_embedding is not None:
                        sim = self._compute_cosine_similarity(query_emb, entry.question_embedding)
                        if sim > best_sim:
                            best_sim = sim
                            best_entry = entry

                if best_entry and best_sim >= threshold:
                    best_entry.hit_count = (best_entry.hit_count or 1) + 1
                    best_entry.last_used_at = datetime.utcnow()
                    db.commit()

                    logger.info(f"Semantic Cache HIT ({best_sim:.4f} >= {threshold}): '{question_text}' -> '{best_entry.question_text}'")
                    return {
                        "is_cached": True,
                        "generated_sql": best_entry.generated_sql,
                        "similarity": round(best_sim, 4),
                        "hit_count": best_entry.hit_count,
                        "cached_question": best_entry.question_text
                    }

        except Exception as e:
            logger.warning(f"Semantic cache lookup encountered error: {e}")
            db.rollback()

        return None

    async def store_cached_query(
        self,
        connection_id: int,
        question_text: str,
        generated_sql: str,
        db: Session
    ) -> Optional[QueryCache]:
        """Cache a verified SQL query with its semantic question embedding."""
        if not question_text or not generated_sql or not db:
            return None

        try:
            query_emb = await embedding_service.get_embedding(question_text)
            if not query_emb:
                return None

            entry = QueryCache(
                connection_id=connection_id,
                question_text=question_text,
                question_embedding=query_emb,
                generated_sql=generated_sql,
                hit_count=1,
                last_used_at=datetime.utcnow()
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            logger.info(f"Semantic Cache STORED: '{question_text}'")
            return entry
        except Exception as e:
            logger.warning(f"Failed to store query in semantic cache: {e}")
            db.rollback()
            return None


semantic_cache = SemanticCacheService()
