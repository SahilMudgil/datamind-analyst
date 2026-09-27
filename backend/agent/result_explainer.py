import time
import json
import logging
from typing import Dict, Any, List, Optional

from agent.state import AgentState, AgentStepTrace
from config import settings

logger = logging.getLogger(__name__)


def generate_deterministic_explanation(
    query: str,
    rows: List[Dict[str, Any]],
    analysis: Dict[str, Any],
    chart_type: str,
    was_successful: bool,
    error_msg: Optional[str] = None
) -> str:
    """Generate professional, clear, deterministic business explanations when LLM is offline or in test environments."""
    if not was_successful:
        return (
            f"I encountered an issue executing this query: {error_msg or 'Validation or execution error'}. "
            "Please check the table and column names in the Schema Explorer or rephrase your question."
        )

    if not rows:
        return f"The query executed successfully, but no matching records were found for '{query}'."

    # 1. Single Stat Card Metric
    if chart_type == "stat_card" or len(rows) == 1:
        first_row = rows[0]
        items = list(first_row.items())
        if len(items) == 1:
            col, val = items[0]
            formatted_val = f"${val:,.2f}" if isinstance(val, (int, float)) and ("revenue" in col.lower() or "amount" in col.lower() or "sales" in col.lower()) else f"{val:,}" if isinstance(val, int) else str(val)
            return f"Based on your data, the **{col.replace('_', ' ').title()}** is **{formatted_val}**."
        elif len(items) > 1:
            details = ", ".join([f"{k.replace('_', ' ').title()}: **{v}**" for k, v in items[:3]])
            return f"Result summary for your query: {details}."

    # 2. Time-series data with Trends
    trends = analysis.get("trends", [])
    if trends:
        trend_info = trends[0]
        direction = trend_info.get("direction", "observed")
        latest_change = trend_info.get("latest_change_pct", 0)
        return (
            f"Analyzed {len(rows)} reporting periods over time. "
            f"The data shows an **{direction}** trajectory, with a **{abs(latest_change)}%** "
            f"{'increase' if latest_change > 0 else 'decrease'} observed in the most recent period."
        )

    # 3. Categorical distribution / Ranking
    if len(rows) > 1:
        top_row = rows[0]
        keys = list(top_row.keys())
        cat_key = keys[0]
        metric_key = keys[1] if len(keys) > 1 else keys[0]
        top_item = top_row.get(cat_key, "N/A")
        top_val = top_row.get(metric_key, "N/A")
        
        formatted_val = f"${top_val:,.2f}" if isinstance(top_val, (int, float)) and any(w in metric_key.lower() for w in ["revenue", "sales", "price", "amount"]) else str(top_val)
        
        return (
            f"Identified {len(rows)} categories from the database. "
            f"The leading entry is **{top_item}** with **{formatted_val}** in {metric_key.replace('_', ' ')}."
        )

    return f"Retrieved {len(rows)} records answering: '{query}'."


async def result_explainer_node(state: AgentState) -> AgentState:
    """LangGraph node: Generates executive business explanations using Groq Llama 3 or deterministic synthesis."""
    start_time = time.time()
    
    intent = state.get("intent", "data_query")
    query = state.get("query", "")
    resolved_query = state.get("resolved_query", query)
    rows = state.get("query_result", [])
    analysis = state.get("analysis_result", {})
    chart_type = state.get("chart_type", "stat_card")
    was_successful = state.get("was_successful", True)
    error_msg = state.get("execution_error") or "; ".join(state.get("safety_violations", []))

    # Handle greetings & off-topic directly
    if intent == "greeting":
        explanation = (
            "Hello! I am your **DataMind Analyst**. I can introspect your database, write safe SQL, "
            "and uncover statistical trends and charts. What would you like to explore today?"
        )
    elif intent == "off_topic":
        explanation = (
            "I specialize in analyzing your connected database and CSV spreadsheets. "
            "Please ask an analytical question regarding your business metrics, revenue, products, or customers."
        )
    else:
        explanation = None

        # Call Groq LLM if configured and query was successful
        if was_successful and rows and settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here":
            try:
                from groq import Groq
                client = Groq(api_key=settings.GROQ_API_KEY)
                
                system_prompt = (
                    "You are a senior data analyst summarizing query results for business executives. "
                    "Write 2-3 clear, insightful, professional sentences explaining the key findings. "
                    "Highlight significant numbers, trends (% change), or outliers. "
                    "Do NOT recite raw SQL code, table IDs, or markdown code fences."
                )

                prompt_content = f"User Question: {resolved_query}\n"
                prompt_content += f"Summary Statistics: {json.dumps(analysis.get('summary', {}))}\n"
                prompt_content += f"Sample Data Rows: {json.dumps(rows[:5])}\n"
                if analysis.get("trends"):
                    prompt_content += f"Detected Trends: {json.dumps(analysis.get('trends'))}\n"
                if analysis.get("outliers"):
                    prompt_content += f"Outliers: {json.dumps(analysis.get('outliers'))}\n"

                candidate_models = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]
                for m in candidate_models:
                    try:
                        completion = client.chat.completions.create(
                            model=m,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt_content}
                            ],
                            temperature=0.3,
                            max_tokens=200
                        )
                        if completion.choices and completion.choices[0].message.content:
                            explanation = completion.choices[0].message.content.strip()
                            break
                    except Exception as model_err:
                        logger.debug(f"Groq explanation model {m} attempt: {model_err}")
                        continue
            except Exception as e:
                logger.warning(f"Groq result explanation fallback: {e}")

        # Fallback to deterministic synthesis
        if not explanation:
            explanation = generate_deterministic_explanation(
                query=resolved_query,
                rows=rows,
                analysis=analysis,
                chart_type=chart_type,
                was_successful=was_successful,
                error_msg=error_msg
            )

    duration_ms = round((time.time() - start_time) * 1000, 2)

    trace_step: AgentStepTrace = {
        "step_name": "Executive Result Explanation",
        "status": "completed",
        "details": {
            "explanation_preview": explanation[:80] + ("..." if len(explanation) > 80 else ""),
            "chart_type": chart_type
        },
        "duration_ms": duration_ms
    }

    traces = list(state.get("trace_steps", []))
    traces.append(trace_step)

    return {
        **state,
        "result_explanation": explanation,
        "trace_steps": traces
    }
