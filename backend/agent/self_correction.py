import time
import re
import logging
from typing import Dict, Any, List
from agent.state import AgentState, AgentStepTrace

logger = logging.getLogger(__name__)


def analyze_database_error(
    error_msg: str,
    previous_sql: str,
    schema_prompt: str,
    relevant_columns: List[Any] = None,
    relevant_tables: List[str] = None
) -> str:
    """Analyze database error message and generate an actionable correction hint for SQL generator."""
    err_lower = error_msg.lower()

    # 1. Missing Column Error (e.g. column "net_margin" does not exist)
    col_match = re.search(r'column ["\']?([a-zA-Z0-9_]+)["\']? does not exist', error_msg, re.IGNORECASE)
    if not col_match:
        col_match = re.search(r'no such column:?\s*["\']?([a-zA-Z0-9_\.]+)["\']?', error_msg, re.IGNORECASE)
    
    if col_match:
        missing_col = col_match.group(1).split(".")[-1]
        available_cols_text = ""
        table_ref = f" for table '{', '.join(relevant_tables)}'" if relevant_tables else ""
        if relevant_columns:
            col_names = [c.get("column_name") for c in relevant_columns if isinstance(c, dict) and c.get("column_name")]
            if col_names:
                available_cols_text = f" Available columns{table_ref}: {', '.join(col_names)}."
        elif relevant_tables:
            available_cols_text = f" Inspect available tables: {', '.join(relevant_tables)}."
        return (
            f"The column '{missing_col}' does not exist in the database. "
            f"Inspect the provided schema closely and replace it with a valid column or calculated expression.{available_cols_text} "
            f"For financial calculations, use existing columns like 'total_amount', 'unit_price * quantity', or 'total_revenue'."
        )

    # 2. Missing / Unknown Table Error
    table_match = re.search(r'relation ["\']?([a-zA-Z0-9_]+)["\']? does not exist', error_msg, re.IGNORECASE)
    if not table_match:
        table_match = re.search(r'no such table:?\s*["\']?([a-zA-Z0-9_]+)["\']?', error_msg, re.IGNORECASE)
    if table_match:
        missing_table = table_match.group(1)
        return (
            f"The table '{missing_table}' does not exist. "
            f"You must query only tables explicitly listed in the schema context."
        )

    # 3. GROUP BY Error
    if "must appear in the group by clause" in err_lower or "aggregate function" in err_lower:
        return (
            "SQL GROUP BY error: Every column in the SELECT list that is not wrapped in an aggregate function "
            "(SUM, COUNT, AVG, MIN, MAX) must be explicitly listed in the GROUP BY clause."
        )

    # 4. Ambiguous Column Error
    if "is ambiguous" in err_lower:
        return (
            "Ambiguous column reference: When joining multiple tables, prefix every column with its table alias "
            "(e.g., 'orders.id' or 'o.id' instead of just 'id')."
        )

    # Default generic error hint
    return f"The database execution failed with error: {error_msg}. Please adjust your SQL query to resolve this."


async def self_correction_node(state: AgentState) -> AgentState:
    """LangGraph node: Analyzes SQL execution errors or safety rejections and formulates repair hints for retry."""
    start_time = time.time()
    
    current_retry = state.get("retry_count", 0) + 1
    previous_sql = state.get("generated_sql", "")
    exec_error = state.get("execution_error")
    safety_violations = state.get("safety_violations", [])
    schema_prompt = state.get("schema_prompt", "")
    retry_history = list(state.get("retry_history", []))

    if safety_violations:
        hint = f"Security guardrail rejected query: {'; '.join(safety_violations)}. Generate a clean read-only SELECT query."
        analyzed_issue = "Safety validation violation"
    elif exec_error:
        hint = analyze_database_error(
            exec_error,
            previous_sql,
            schema_prompt,
            state.get("relevant_columns", []),
            state.get("relevant_tables", [])
        )
        analyzed_issue = f"Database error: {exec_error}"
    else:
        hint = "Previous query produced no results or invalid format. Please refine SQL."
        analyzed_issue = "Execution returned empty/invalid state"

    # Record retry attempt in history
    retry_history.append({
        "attempt": current_retry,
        "failed_sql": previous_sql,
        "error": exec_error or "; ".join(safety_violations),
        "hint": hint
    })

    duration_ms = round((time.time() - start_time) * 1000, 2)

    trace_step: AgentStepTrace = {
        "step_name": f"Self-Correction Reflection (Retry #{current_retry})",
        "status": "completed",
        "details": {
            "attempt": current_retry,
            "issue_detected": analyzed_issue,
            "correction_hint": hint
        },
        "duration_ms": duration_ms
    }

    traces = list(state.get("trace_steps", []))
    traces.append(trace_step)

    logger.info(f"Self-correction loop triggered (attempt {current_retry}): {hint}")

    return {
        **state,
        "retry_count": current_retry,
        "retry_hint": hint,
        "retry_history": retry_history,
        "is_safe": False,
        "was_successful": False,
        "trace_steps": traces
    }
