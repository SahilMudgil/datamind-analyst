import time
import logging
import numpy as np
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from agent.state import AgentState, AgentStepTrace
from models.models import SchemaCache
from services.embedding_service import embedding_service
from database import get_db

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two normalized float vectors."""
    if not vec1 or not vec2:
        return 0.0
    v1 = np.array(vec1, dtype=np.float32)
    v2 = np.array(vec2, dtype=np.float32)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (norm1 * norm2))


async def schema_linker_node(state: AgentState, db: Optional[Session] = None) -> AgentState:
    """LangGraph node: Vector similarity search against schema_cache to select top relevant tables & columns."""
    start_time = time.time()
    resolved_query = state.get("resolved_query") or state.get("query", "")
    connection_id = state.get("connection_id")

    # If previous step determined query is invalid/off-topic, skip schema linking
    if not state.get("is_valid_intent", True):
        return state

    # If no db session injected, check state or obtain one from get_db
    db_session = db or state.get("db")
    local_session = False
    if db_session is None:
        try:
            db_generator = get_db()
            db_session = next(db_generator)
            local_session = True
        except Exception as e:
            logger.warning(f"Could not obtain database session in schema linker: {e}")
            db_session = None

    try:
        # 1. Fetch cached schema for this connection
        schema_entries = []
        if db_session is not None:
            schema_entries = (
                db_session.query(SchemaCache)
                .filter(SchemaCache.connection_id == connection_id)
                .all()
            )

        if not schema_entries:
            # Empty schema cache or connection not found
            trace_step: AgentStepTrace = {
                "step_name": "Vector Schema Linking",
                "status": "completed",
                "details": {
                    "matched_tables": [],
                    "message": "No schema cache found for connection."
                },
                "duration_ms": round((time.time() - start_time) * 1000, 2)
            }
            traces = list(state.get("trace_steps", []))
            traces.append(trace_step)
            return {
                **state,
                "relevant_tables": [],
                "relevant_columns": [],
                "schema_prompt": "",
                "trace_steps": traces
            }

        # 2. Get embedding for the resolved query
        query_embedding = await embedding_service.get_embedding(resolved_query)

        # 3. Score all columns and group by table
        table_scores: Dict[str, float] = {}
        table_columns_map: Dict[str, List[SchemaCache]] = {}
        col_scores: Dict[int, float] = {}

        for entry in schema_entries:
            t_name = entry.table_name
            if t_name not in table_columns_map:
                table_columns_map[t_name] = []
                table_scores[t_name] = 0.0
            table_columns_map[t_name].append(entry)

            # Compute similarity if embedding exists
            sim = 0.0
            if entry.description_embedding is not None and len(entry.description_embedding) > 0:
                sim = cosine_similarity(query_embedding, entry.description_embedding)
            else:
                # Lexical keyword fallback matching
                q_lower = resolved_query.lower()
                c_lower = entry.column_name.lower()
                t_lower = t_name.lower()
                if c_lower in q_lower or t_lower in q_lower:
                    sim = 0.8
                elif any(word in (entry.ai_description or "").lower() for word in q_lower.split() if len(word) > 3):
                    sim = 0.5
                else:
                    sim = 0.1

            col_scores[entry.id] = sim
            if sim > table_scores[t_name]:
                table_scores[t_name] = sim

        # 4. Rank tables and select top matches
        # If total tables <= 8 (typical business/demo DB), keep all tables to ensure joins are never missed
        total_tables = len(table_columns_map)
        if total_tables <= 8:
            selected_tables = list(table_columns_map.keys())
        else:
            sorted_tables = sorted(table_scores.items(), key=lambda x: x[1], reverse=True)
            # Select top tables with score > 0.25 (minimum 2 tables)
            selected_tables = [t for t, score in sorted_tables[:4]]

            # Also include any table referenced by foreign keys of selected tables
            referenced_tables = set()
            for t in selected_tables:
                for col in table_columns_map[t]:
                    if col.is_foreign_key and col.references_table:
                        referenced_tables.add(col.references_table)
            
            for ref_t in referenced_tables:
                if ref_t in table_columns_map and ref_t not in selected_tables:
                    selected_tables.append(ref_t)

            # Also include junction tables (e.g., order_items) that connect two or more of the selected tables
            for t, cols in table_columns_map.items():
                if t not in selected_tables:
                    fks_in_t = {c.references_table for c in cols if c.is_foreign_key and c.references_table}
                    if len(fks_in_t.intersection(set(selected_tables))) >= 2:
                        selected_tables.append(t)

        # 5. Build rich schema prompt text with column types & AI explanations
        schema_prompt_lines = ["Available Database Tables & Columns:"]
        relevant_cols_list = []

        for t in selected_tables:
            schema_prompt_lines.append(f"\nTable: `{t}`")
            cols = table_columns_map[t]
            for col in cols:
                pk_flag = " [PRIMARY KEY]" if col.is_primary_key else ""
                fk_flag = f" [FOREIGN KEY -> {col.references_table}.id]" if col.is_foreign_key and col.references_table else ""
                desc = f" - Description: {col.ai_description}" if col.ai_description else ""
                schema_prompt_lines.append(f"  • `{col.column_name}` ({col.data_type}){pk_flag}{fk_flag}{desc}")
                
                relevant_cols_list.append({
                    "table": t,
                    "column": col.column_name,
                    "data_type": col.data_type,
                    "is_pk": col.is_primary_key,
                    "is_fk": col.is_foreign_key,
                    "references_table": col.references_table,
                    "description": col.ai_description
                })

        schema_prompt = "\n".join(schema_prompt_lines)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        trace_step: AgentStepTrace = {
            "step_name": "Vector Schema Linking",
            "status": "completed",
            "details": {
                "matched_tables": selected_tables,
                "table_count": len(selected_tables),
                "total_columns_linked": len(relevant_cols_list)
            },
            "duration_ms": duration_ms
        }

        traces = list(state.get("trace_steps", []))
        traces.append(trace_step)

        return {
            **state,
            "relevant_tables": selected_tables,
            "relevant_columns": relevant_cols_list,
            "schema_prompt": schema_prompt,
            "trace_steps": traces
        }

    finally:
        if local_session and db_session:
            db_session.close()
