import time
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from scipy import stats

from agent.state import AgentState, AgentStepTrace

logger = logging.getLogger(__name__)


def determine_chart_selection(
    df: pd.DataFrame,
    numeric_cols: List[str],
    date_cols: List[str],
    cat_cols: List[str],
    query: str = ""
) -> Dict[str, Any]:
    """Deterministically select optimal chart visualization based on tabular result shape."""
    row_count = len(df)
    q_lower = query.lower()

    # 1. Single scalar result (1 row, 1 numeric column) -> Stat Card
    if row_count == 1 and len(df.columns) == 1:
        val = df.iloc[0, 0]
        col = df.columns[0]
        return {
            "chart_type": "stat_card",
            "chart_config": {
                "value": float(val) if isinstance(val, (int, float, np.number)) else str(val),
                "label": col.replace("_", " ").title(),
                "format": "currency" if any(w in col.lower() for w in ["revenue", "sales", "price", "amount", "cost"]) else "number"
            }
        }

    # 2. Time-series data -> Area Chart (for cumulative/trend) or Line Chart
    if date_cols and numeric_cols:
        date_col = date_cols[0]
        num_col = numeric_cols[0]
        is_area = any(w in q_lower for w in ["area", "cumulative", "growth", "trend", "volume"])
        chart_type = "area" if is_area else "line"
        return {
            "chart_type": chart_type,
            "chart_config": {
                "xAxis": date_col,
                "yAxis": num_col,
                "xKey": date_col,
                "yKeys": [num_col],
                "title": f"{num_col.replace('_', ' ').title()} Over Time",
                "strokeColor": "#818cf8"
            }
        }

    # 3. Categorical distribution / Breakdown -> Pie Chart or Bar Chart
    if cat_cols and numeric_cols:
        cat_col = cat_cols[0]
        num_col = numeric_cols[0]
        
        is_pie_query = any(w in q_lower for w in ["breakdown", "pie", "share", "distribution", "split", "proportion", "method"])
        
        if is_pie_query and 2 <= row_count <= 8 and not any(w in num_col.lower() for w in ["rank", "id"]):
            return {
                "chart_type": "pie",
                "chart_config": {
                    "xAxis": cat_col,
                    "yAxis": num_col,
                    "xKey": cat_col,
                    "yKeys": [num_col],
                    "nameKey": cat_col,
                    "dataKey": num_col,
                    "title": f"Distribution of {num_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}"
                }
            }
            
        return {
            "chart_type": "bar",
            "chart_config": {
                "xAxis": cat_col,
                "yAxis": num_col,
                "xKey": cat_col,
                "yKeys": [num_col],
                "title": f"{num_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}",
                "barColor": "#6366f1"
            }
        }

    # Default fallback: Table or basic Bar
    if numeric_cols:
        first_col = df.columns[0]
        num_col = numeric_cols[0]
        return {
            "chart_type": "bar",
            "chart_config": {
                "xAxis": first_col,
                "yAxis": num_col,
                "xKey": first_col,
                "yKeys": [num_col],
                "title": "Data Distribution"
            }
        }

    return {
        "chart_type": "stat_card",
        "chart_config": {
            "value": row_count,
            "label": "Total Records"
        }
    }


def perform_statistical_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Execute statistical trend detection, z-score outlier analysis, and summary metrics."""
    analysis = {
        "summary": {},
        "summary_statistics": {},
        "trends": [],
        "outliers": [],
        "correlations": []
    }

    if df.empty:
        return analysis

    # Identify numeric, date, and categorical columns
    numeric_cols = []
    date_cols = []
    cat_cols = []

    for col in df.columns:
        # Check if numeric
        converted_num = pd.to_numeric(df[col], errors="coerce")
        if converted_num.notnull().sum() > len(df) * 0.5:
            df[col] = converted_num
            numeric_cols.append(col)
            continue

        # Check if date
        col_lower = col.lower()
        if "date" in col_lower or "month" in col_lower or "year" in col_lower or "time" in col_lower:
            date_cols.append(col)
        else:
            cat_cols.append(col)

    # 1. Summary Metrics for numeric columns
    for num_col in numeric_cols:
        series = df[num_col].dropna()
        if not series.empty:
            stat_obj = {
                "total": float(series.sum()),
                "sum": float(series.sum()),
                "mean": round(float(series.mean()), 2),
                "median": round(float(series.median()), 2),
                "min": float(series.min()),
                "max": float(series.max())
            }
            analysis["summary"][num_col] = stat_obj
            analysis["summary_statistics"][num_col] = stat_obj

    # 2. Trend Detection (for time-series data)
    if date_cols and numeric_cols:
        d_col = date_cols[0]
        n_col = numeric_cols[0]
        try:
            sorted_df = df.sort_values(by=d_col).copy()
            pct_changes = sorted_df[n_col].pct_change().dropna() * 100
            if not pct_changes.empty:
                latest_pct = round(float(pct_changes.iloc[-1]), 2)
                avg_pct = round(float(pct_changes.mean()), 2)
                direction = "increased" if latest_pct > 1 else ("decreased" if latest_pct < -1 else "stable")

                analysis["trends"].append({
                    "column": n_col,
                    "date_column": d_col,
                    "latest_change_pct": latest_pct,
                    "average_change_pct": avg_pct,
                    "direction": direction,
                    "trajectory_summary": f"{direction.capitalize()} trajectory with a {abs(latest_pct)}% change in the most recent period."
                })
        except Exception as e:
            logger.warning(f"Trend detection calculation error: {e}")

    # 3. Z-score Outlier Analysis (requires at least 4 data points)
    if len(df) >= 4:
        for num_col in numeric_cols:
            series = df[num_col].dropna()
            if len(series) >= 4 and series.std() > 0:
                try:
                    z_scores = np.abs(stats.zscore(series))
                    threshold = 1.75 if len(series) <= 6 else 2.0
                    outlier_indices = np.where(z_scores >= threshold)[0]
                    for idx in outlier_indices:
                        outlier_val = float(series.iloc[idx])
                        row_context = df.iloc[idx].to_dict()
                        analysis["outliers"].append({
                            "column": num_col,
                            "value": outlier_val,
                            "z_score": round(float(z_scores[idx]), 2),
                            "context": {k: str(v) for k, v in row_context.items() if k != num_col}
                        })
                except Exception as e:
                    logger.warning(f"Outlier calculation error for {num_col}: {e}")

    # 4. Correlation check (if >= 2 numeric columns)
    if len(numeric_cols) >= 2 and len(df) >= 3:
        try:
            corr_matrix = df[numeric_cols].corr()
            for i in range(len(numeric_cols)):
                for j in range(i + 1, len(numeric_cols)):
                    c1, c2 = numeric_cols[i], numeric_cols[j]
                    val = corr_matrix.loc[c1, c2]
                    if not np.isnan(val) and abs(val) >= 0.6:
                        analysis["correlations"].append({
                            "columns": [c1, c2],
                            "coefficient": round(float(val), 2),
                            "relationship": "strong positive" if val > 0.7 else ("strong negative" if val < -0.7 else "moderate")
                        })
        except Exception:
            pass

    return analysis


async def data_analysis_node(state: AgentState) -> AgentState:
    """LangGraph node: Computes trends, z-scores, correlations, and chooses the optimal chart."""
    start_time = time.time()
    
    rows = state.get("query_result", [])
    if not rows or not isinstance(rows, list):
        return {
            **state,
            "analysis_result": {"summary": "No data rows available."},
            "chart_type": "stat_card",
            "chart_config": {"value": 0, "label": "No Data"}
        }

    df = pd.DataFrame(rows)
    
    # Run statistical calculations
    analysis_res = perform_statistical_analysis(df)

    # Determine column categories for chart selection
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    date_cols = [c for c in df.columns if any(w in c.lower() for w in ["date", "month", "year", "time"])]
    cat_cols = [c for c in df.columns if c not in numeric_cols and c not in date_cols]

    query_text = state.get("resolved_query") or state.get("query", "")
    chart_info = determine_chart_selection(df, numeric_cols, date_cols, cat_cols, query=query_text)

    duration_ms = round((time.time() - start_time) * 1000, 2)

    trace_step: AgentStepTrace = {
        "step_name": "Data Analysis & Chart Selection",
        "status": "completed",
        "details": {
            "selected_chart": chart_info["chart_type"],
            "trends_detected": len(analysis_res["trends"]),
            "outliers_found": len(analysis_res["outliers"]),
            "metrics_analyzed": list(analysis_res["summary"].keys())
        },
        "duration_ms": duration_ms
    }

    traces = list(state.get("trace_steps", []))
    traces.append(trace_step)

    return {
        **state,
        "analysis_result": analysis_res,
        "chart_type": chart_info["chart_type"],
        "chart_config": chart_info["chart_config"],
        "trace_steps": traces
    }
