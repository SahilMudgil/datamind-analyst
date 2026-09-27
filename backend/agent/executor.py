import time
import logging
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from agent.state import AgentState, AgentStepTrace
from models.models import DatabaseConnection
from services.schema_service import schema_service
from database import get_db
from config import settings

logger = logging.getLogger(__name__)


def serialize_value(val: Any) -> Any:
    """Serialize database types (Decimals, dates, UUIDs) into JSON-compatible values."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


def execute_sql_safely(
    sql_query: str,
    target_engine,
    timeout_seconds: int = 10
) -> Dict[str, Any]:
    """Execute a read-only SQL query against the target database engine with timeout enforcement."""
    try:
        with target_engine.connect() as connection:
            # For PostgreSQL, set statement_timeout
            try:
                if target_engine.dialect.name == "postgresql":
                    connection.execute(text(f"SET statement_timeout = '{timeout_seconds * 1000}';"))
            except Exception:
                pass

            result = connection.execute(text(sql_query))
            column_names = list(result.keys())
            raw_rows = result.fetchall()

            rows = [
                {col: serialize_value(val) for col, val in zip(column_names, row)}
                for row in raw_rows
            ]

            return {
                "success": True,
                "rows": rows,
                "column_names": column_names,
                "row_count": len(rows),
                "error": None
            }
    except Exception as e:
        logger.error(f"SQL execution error: {e}")
        return {
            "success": False,
            "rows": [],
            "column_names": [],
            "row_count": 0,
            "error": str(e)
        }


async def execution_node(state: AgentState) -> AgentState:
    """LangGraph node: Executes sanitized SQL against the target database connection."""
    start_time = time.time()
    
    if not state.get("is_valid_intent", True):
        return state

    sql_to_run = state.get("sanitized_sql") or state.get("generated_sql", "")
    connection_id = state.get("connection_id")
    target_engine = state.get("target_engine")
    db: Optional[Session] = state.get("db")

    local_session = False
    if target_engine is None:
        if db is None:
            try:
                db_gen = get_db()
                db = next(db_gen)
                local_session = True
            except Exception:
                db = None

        if db is not None:
            conn_record = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
            if conn_record:
                dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
                if dialect_name is None and hasattr(db, "get_bind"):
                    try:
                        dialect_name = db.get_bind().dialect.name
                    except Exception:
                        dialect_name = None
                else:
                    dialect_name = getattr(dialect_name, "name", None)

                if conn_record.db_type in ("csv_import", "sqlite") or dialect_name == "sqlite":
                    target_engine = db.get_bind()
                else:
                    url = schema_service.build_connection_url(conn_record)
                    target_engine = create_engine(url, connect_args={"connect_timeout": 5})

    exec_result = None
    if target_engine is not None and sql_to_run:
        exec_result = execute_sql_safely(
            sql_query=sql_to_run,
            target_engine=target_engine,
            timeout_seconds=settings.QUERY_TIMEOUT_SECONDS
        )
    else:
        # Fallback if no target engine could be bound
        exec_result = {
            "success": False,
            "rows": [],
            "column_names": [],
            "row_count": 0,
            "error": "No database connection available to execute query."
        }

    duration_ms = round((time.time() - start_time) * 1000, 2)

    trace_step: AgentStepTrace = {
        "step_name": f"Database Execution (Attempt {state.get('retry_count', 0) + 1})",
        "status": "completed" if exec_result["success"] else "failed",
        "details": {
            "row_count": exec_result["row_count"],
            "columns": exec_result["column_names"],
            "error": exec_result["error"]
        },
        "duration_ms": duration_ms
    }

    traces = list(state.get("trace_steps", []))
    traces.append(trace_step)

    if local_session and db:
        db.close()

    return {
        **state,
        "query_result": exec_result["rows"],
        "column_names": exec_result["column_names"],
        "row_count": exec_result["row_count"],
        "was_successful": exec_result["success"],
        "execution_error": exec_result["error"],
        "trace_steps": traces
    }
