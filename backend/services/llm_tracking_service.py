import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.models import LLMUsageLog

logger = logging.getLogger(__name__)

# Token pricing per 1 million tokens (USD)
MODEL_PRICING = {
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "default": {"input": 0.10, "output": 0.40}
}


class LLMTrackingService:
    @staticmethod
    def estimate_tokens(text: Optional[str]) -> int:
        """Estimate token count based on character length (~4 chars per token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    @classmethod
    def calculate_cost(cls, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost in USD based on model pricing."""
        pricing = MODEL_PRICING.get(model_name, MODEL_PRICING["default"])
        input_cost = (input_tokens / 1_000_000.0) * pricing["input"]
        output_cost = (output_tokens / 1_000_000.0) * pricing["output"]
        return round(input_cost + output_cost, 6)

    @classmethod
    def log_usage(
        cls,
        db: Session,
        user_id: int,
        provider: str,
        model_used: str,
        step_type: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: Optional[int] = None,
        message_id: Optional[int] = None
    ) -> Optional[LLMUsageLog]:
        """Record an LLM API call into the audit log."""
        try:
            cost = cls.calculate_cost(model_used, input_tokens, output_tokens)
            log_record = LLMUsageLog(
                user_id=user_id,
                message_id=message_id,
                provider=provider,
                model_used=model_used,
                step_type=step_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=cost,
                latency_ms=latency_ms
            )
            db.add(log_record)
            db.commit()
            db.refresh(log_record)
            return log_record
        except Exception as e:
            logger.warning(f"Failed to record LLM usage log: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            return None

    @staticmethod
    def get_user_usage_summary(db: Session, user_id: int) -> Dict[str, Any]:
        """Aggregate total token consumption and costs for a given user."""
        try:
            total_query = db.query(
                func.count(LLMUsageLog.id).label("total_calls"),
                func.sum(LLMUsageLog.input_tokens).label("total_input_tokens"),
                func.sum(LLMUsageLog.output_tokens).label("total_output_tokens"),
                func.sum(LLMUsageLog.estimated_cost_usd).label("total_cost_usd"),
                func.avg(LLMUsageLog.latency_ms).label("avg_latency_ms")
            ).filter(LLMUsageLog.user_id == user_id).first()

            # Breakdown by model
            model_breakdown = db.query(
                LLMUsageLog.model_used,
                func.count(LLMUsageLog.id).label("calls"),
                func.sum(LLMUsageLog.input_tokens + LLMUsageLog.output_tokens).label("tokens"),
                func.sum(LLMUsageLog.estimated_cost_usd).label("cost")
            ).filter(LLMUsageLog.user_id == user_id).group_by(LLMUsageLog.model_used).all()

            # Breakdown by step type
            step_breakdown = db.query(
                LLMUsageLog.step_type,
                func.count(LLMUsageLog.id).label("calls"),
                func.sum(LLMUsageLog.estimated_cost_usd).label("cost")
            ).filter(LLMUsageLog.user_id == user_id).group_by(LLMUsageLog.step_type).all()

            total_calls = total_query.total_calls or 0
            total_input = int(total_query.total_input_tokens or 0)
            total_output = int(total_query.total_output_tokens or 0)
            total_cost = float(total_query.total_cost_usd or 0.0)
            avg_latency = float(total_query.avg_latency_ms or 0.0)

            return {
                "total_calls": total_calls,
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "total_cost_usd": round(total_cost, 6),
                "avg_latency_ms": round(avg_latency, 2),
                "by_model": [
                    {
                        "model": m.model_used,
                        "calls": m.calls,
                        "tokens": int(m.tokens or 0),
                        "cost_usd": round(float(m.cost or 0.0), 6)
                    }
                    for m in model_breakdown
                ],
                "by_step": [
                    {
                        "step_type": s.step_type,
                        "calls": s.calls,
                        "cost_usd": round(float(s.cost or 0.0), 6)
                    }
                    for s in step_breakdown
                ]
            }
        except Exception as e:
            logger.error(f"Error compiling usage summary: {e}")
            return {
                "total_calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_latency_ms": 0.0,
                "by_model": [],
                "by_step": []
            }


llm_tracking_service = LLMTrackingService()
