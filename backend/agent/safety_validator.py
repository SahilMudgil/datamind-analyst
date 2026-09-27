import time
import logging
from typing import Dict, Any, List, Set, Tuple, Optional
import sqlglot
from sqlglot import exp

from agent.state import AgentState, AgentStepTrace
from config import settings

logger = logging.getLogger(__name__)

# Strictly blocked system catalogs and tables
FORBIDDEN_TABLES = {
    "pg_shadow", "pg_authid", "pg_user", "pg_roles", "pg_database",
    "pg_tables", "pg_stat_activity", "pg_proc", "information_schema",
    "sqlite_master", "sqlite_sequence", "users" # Prevent users querying internal auth table
}

DESTRUCTIVE_EXPRESSIONS = (
    exp.Drop, exp.Delete, exp.Update, exp.Insert, exp.Alter,
    exp.Create, exp.TruncateTable, exp.Grant, exp.Revoke
)


def validate_sql_safety(
    sql_query: str,
    allowed_tables: Optional[Set[str]] = None,
    max_limit: int = 100
) -> Tuple[bool, List[str], Optional[str]]:
    """AST-based safety validation using sqlglot.
    
    Returns:
        (is_safe, list_of_violations, sanitized_sql)
    """
    violations = []

    if not sql_query or not sql_query.strip():
        return False, ["SQL query is empty."], None

    # Check 1: Reject SQL comments (-- or /* */) which are common in SQL injection payloads
    if "--" in sql_query or "/*" in sql_query or "*/" in sql_query:
        return False, ["SQL comment syntax ('--', '/*') is rejected by security guardrails."], None

    # Check 2: Parse statements with sqlglot
    try:
        statements = sqlglot.parse(sql_query, read="postgres")
    except Exception as e:
        return False, [f"SQL syntax error: {str(e)}"], None

    if not statements:
        return False, ["Could not parse valid SQL statement."], None

    # Check 3: Strictly block multi-statement payloads
    if len(statements) > 1:
        return False, ["Multi-statement SQL payloads separated by ';' are strictly prohibited."], None

    root = statements[0]

    # Check 4: Must be SELECT statement (or Union of SELECTs)
    if not isinstance(root, (exp.Select, exp.Union)):
        return False, [f"Unauthorized statement type '{root.key.upper()}'. Only read-only SELECT queries are permitted."], None

    # Check 5: Deep AST inspection for any embedded destructive expressions
    for expr_type in DESTRUCTIVE_EXPRESSIONS:
        if root.find(expr_type):
            violations.append(f"Forbidden destructive expression detected: {expr_type.__name__}")

    # Check 6: Extract and validate all referenced tables against allow-list
    # CTE names defined in WITH clauses should not be treated as external physical database tables
    cte_names = set()
    for cte in root.find_all(exp.CTE):
        if cte.alias_or_name:
            cte_names.add(cte.alias_or_name.lower())

    referenced_tables = set()
    for table_expr in root.find_all(exp.Table):
        t_name = table_expr.name.lower()
        if t_name not in cte_names:
            referenced_tables.add(t_name)

        if t_name in FORBIDDEN_TABLES:
            violations.append(f"Access to restricted or system catalog table '{t_name}' is forbidden.")

    if allowed_tables is not None:
        allowed_normalized = {t.lower() for t in allowed_tables}
        for t_name in referenced_tables:
            if t_name not in allowed_normalized and t_name not in FORBIDDEN_TABLES:
                violations.append(f"Table '{t_name}' does not exist in authorized schema allow-list.")

    if violations:
        return False, violations, None

    # Check 7: Enforce LIMIT clause (auto-inject if missing, clamp if excessive)
    limit_clause = root.find(exp.Limit)
    if not limit_clause:
        root = root.limit(max_limit)
    else:
        try:
            curr_val = int(limit_clause.expression.this)
            if curr_val > max_limit or curr_val <= 0:
                limit_clause.set("expression", exp.Literal.number(max_limit))
        except Exception:
            limit_clause.set("expression", exp.Literal.number(max_limit))

    # Output normalized sanitized SQL
    sanitized_sql = root.sql(dialect="postgres")
    return True, [], sanitized_sql


async def safety_validator_node(state: AgentState) -> AgentState:
    """LangGraph node: Validates SQL AST safety, enforces allow-lists, and injects row limits."""
    start_time = time.time()
    
    if not state.get("is_valid_intent", True):
        return state

    raw_sql = state.get("generated_sql", "")
    relevant_tables = state.get("relevant_tables", [])
    retry_count = state.get("retry_count", 0)

    # Allowed tables are the ones in active schema
    allowed_set = set(relevant_tables) if relevant_tables else None

    is_safe, violations, sanitized_sql = validate_sql_safety(
        sql_query=raw_sql,
        allowed_tables=allowed_set,
        max_limit=settings.DEFAULT_ROW_LIMIT
    )

    duration_ms = round((time.time() - start_time) * 1000, 2)

    trace_step: AgentStepTrace = {
        "step_name": f"AST Safety Validation (Attempt {retry_count + 1})",
        "status": "completed" if is_safe else "failed",
        "details": {
            "is_safe": is_safe,
            "violations": violations,
            "sanitized_sql": sanitized_sql if is_safe else None
        },
        "duration_ms": duration_ms
    }

    traces = list(state.get("trace_steps", []))
    traces.append(trace_step)

    # If safety violations and retries available, prepare retry hint
    retry_hint = None
    if not is_safe and retry_count < state.get("max_retries", 2):
        retry_hint = f"Safety violations: {'; '.join(violations)}"

    return {
        **state,
        "is_safe": is_safe,
        "safety_violations": violations,
        "sanitized_sql": sanitized_sql,
        "retry_hint": retry_hint,
        "trace_steps": traces
    }
