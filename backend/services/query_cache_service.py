import logging
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.models import QueryCache
from services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class QueryCacheService:
    def __init__(self, similarity_threshold: float = 0.95):
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two numeric vectors."""
        v1 = np.array(vec1, dtype=float)
        v2 = np.array(vec2, dtype=float)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

    async def find_cached_query(
        self,
        connection_id: int,
        question_text: str,
        db: Session,
        threshold: Optional[float] = None
    ) -> Optional[QueryCache]:
        """Search query_cache for a semantically similar previous question."""
        target_threshold = threshold if threshold is not None else self.similarity_threshold
        
        try:
            # 1. Compute embedding of user question
            query_embedding = await embedding_service.get_embedding(question_text)
            if not query_embedding:
                return None

            # Fetch all cached entries for this connection
            cached_entries = db.query(QueryCache).filter(
                QueryCache.connection_id == connection_id
            ).all()

            if not cached_entries:
                return None

            best_match = None
            highest_sim = -1.0

            for entry in cached_entries:
                entry_emb = entry.question_embedding
                # Handle string/list serialization differences
                if isinstance(entry_emb, str):
                    try:
                        import json
                        entry_emb = json.loads(entry_emb)
                    except Exception:
                        continue
                elif hasattr(entry_emb, "tolist"):
                    entry_emb = entry_emb.tolist()

                if not entry_emb or len(entry_emb) != len(query_embedding):
                    continue

                sim = self._cosine_similarity(query_embedding, entry_emb)
                if sim > highest_sim:
                    highest_sim = sim
                    best_match = entry

            if highest_sim >= target_threshold and best_match:
                logger.info(
                    f"Semantic cache HIT (similarity {highest_sim:.4f} >= {target_threshold}) "
                    f"for question: '{question_text}'"
                )
                best_match.hit_count = (best_match.hit_count or 0) + 1
                best_match.last_used_at = datetime.utcnow()
                db.commit()
                db.refresh(best_match)
                return best_match

            logger.info(
                f"Semantic cache MISS (highest similarity {highest_sim:.4f} < {target_threshold}) "
                f"for question: '{question_text}'"
            )
            return None

        except Exception as e:
            logger.warning(f"Error checking semantic query cache: {e}")
            return None

    async def save_cached_query(
        self,
        connection_id: int,
        question_text: str,
        generated_sql: str,
        db: Session
    ) -> Optional[QueryCache]:
        """Save a newly validated SQL generation into query_cache."""
        if not question_text or not generated_sql:
            return None

        try:
            # Check for exact duplicate question text
            existing = db.query(QueryCache).filter(
                QueryCache.connection_id == connection_id,
                QueryCache.question_text == question_text
            ).first()

            if existing:
                existing.generated_sql = generated_sql
                existing.hit_count = (existing.hit_count or 0) + 1
                existing.last_used_at = datetime.utcnow()
                db.commit()
                db.refresh(existing)
                return existing

            embedding = await embedding_service.get_embedding(question_text)
            cache_entry = QueryCache(
                connection_id=connection_id,
                question_text=question_text,
                question_embedding=embedding,
                generated_sql=generated_sql,
                hit_count=1,
                last_used_at=datetime.utcnow()
            )
            db.add(cache_entry)
            db.commit()
            db.refresh(cache_entry)
            logger.info(f"Saved new query to semantic cache for connection {connection_id}")
            return cache_entry

        except Exception as e:
            logger.warning(f"Error saving query to semantic cache: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            return None


query_cache_service = QueryCacheService()
