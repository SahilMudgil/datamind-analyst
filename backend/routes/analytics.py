import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.models import User, LLMUsageLog, QueryCache
from services.auth_service import get_current_user
from services.llm_tracking_service import llm_tracking_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Usage"])


@router.get("/llm-usage")
def get_llm_usage_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve token consumption, estimated costs, and model stats for current user."""
    return llm_tracking_service.get_user_usage_summary(db=db, user_id=current_user.id)


@router.get("/cache-stats")
def get_cache_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve semantic query cache performance and hit rates."""
    total_cached = db.query(func.count(QueryCache.id)).scalar() or 0
    total_hits = db.query(func.sum(QueryCache.hit_count)).scalar() or 0

    popular = db.query(QueryCache).order_by(
        QueryCache.hit_count.desc()
    ).limit(5).all()

    return {
        "total_cached_queries": total_cached,
        "total_cache_hits": int(total_hits),
        "top_cached_queries": [
            {
                "question": q.question_text,
                "hits": q.hit_count,
                "last_used_at": q.last_used_at.isoformat() if q.last_used_at else None
            }
            for q in popular
        ]
    }
