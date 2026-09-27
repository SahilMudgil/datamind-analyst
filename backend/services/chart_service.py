from typing import List, Dict, Any, Optional, Tuple

class ChartService:
    PALETTE = ["#6366f1", "#06b6d4", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#3b82f6"]

    @staticmethod
    def _is_numeric(val: Any) -> bool:
        if val is None:
            return False
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return True
        try:
            float(str(val))
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _is_date_like(col_name: str, sample_val: Any) -> bool:
        col_lower = col_name.lower()
        if any(d in col_lower for d in ("date", "month", "year", "day", "time", "period", "week")):
            return True
        if sample_val and isinstance(sample_val, str):
            # Check YYYY-MM-DD format
            if len(sample_val) >= 7 and sample_val[4] == "-" and (sample_val[:4].isdigit()):
                return True
        return False

    @classmethod
    def select_chart(cls, rows: List[Dict[str, Any]], columns: List[str]) -> Tuple[str, Dict[str, Any]]:
        """Deterministically select chart type and build Recharts configuration."""
        if not rows or not columns:
            return "stat_card", {"title": "No Data", "value": "0"}

        row_count = len(rows)
        col_count = len(columns)

        # 1. Single scalar value (1 row x 1 col, or 1 row with numeric values)
        if row_count == 1:
            numeric_cols = [c for c in columns if cls._is_numeric(rows[0].get(c))]
            if numeric_cols:
                main_col = numeric_cols[0]
                val = rows[0].get(main_col)
                formatted_val = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}" if isinstance(val, int) else str(val)
                return "stat_card", {
                    "title": main_col.replace("_", " ").title(),
                    "value": formatted_val,
                    "raw_value": val,
                    "metric_key": main_col
                }

        # Analyze column data types from the first non-null values
        numeric_cols = []
        date_cols = []
        text_cols = []

        for c in columns:
            sample_vals = [r.get(c) for r in rows if r.get(c) is not None]
            sample = sample_vals[0] if sample_vals else None

            if sample is not None and cls._is_numeric(sample):
                numeric_cols.append(c)
            elif sample is not None and cls._is_date_like(c, sample):
                date_cols.append(c)
            else:
                text_cols.append(c)

        # 2. Time-series / Date on X-axis + Numeric on Y-axis -> LINE CHART
        if date_cols and numeric_cols:
            x_key = date_cols[0]
            y_keys = numeric_cols[:3] # Up to 3 metric series
            return "line", {
                "title": f"{', '.join(y.replace('_', ' ').title() for y in y_keys)} over {x_key.replace('_', ' ').title()}",
                "xKey": x_key,
                "yKeys": y_keys,
                "xAxis": x_key,
                "yAxis": y_keys[0],
                "colors": cls.PALETTE[:len(y_keys)],
                "is_time_series": True
            }

        # 3. Low-cardinality category (<= 5 distinct slices) + percentage / share / positive values -> PIE CHART
        if text_cols and numeric_cols and 2 <= row_count <= 5:
            cat_col = text_cols[0]
            metric_col = numeric_cols[0]
            # Check if all values are positive
            all_positive = all(float(r.get(metric_col, 0) or 0) >= 0 for r in rows)
            if all_positive:
                return "pie", {
                    "title": f"Distribution of {metric_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}",
                    "nameKey": cat_col,
                    "dataKey": metric_col,
                    "xKey": cat_col,
                    "yKeys": [metric_col],
                    "xAxis": cat_col,
                    "yAxis": metric_col,
                    "colors": cls.PALETTE[:row_count]
                }

        # 4. Categorical column + Numeric columns -> BAR CHART
        if text_cols and numeric_cols:
            x_key = text_cols[0]
            y_keys = numeric_cols[:2]
            return "bar", {
                "title": f"{', '.join(y.replace('_', ' ').title() for y in y_keys)} by {x_key.replace('_', ' ').title()}",
                "xKey": x_key,
                "yKeys": y_keys,
                "xAxis": x_key,
                "yAxis": y_keys[0],
                "colors": cls.PALETTE[:len(y_keys)]
            }

        # 5. Default fallback to BAR chart with first col as X, or stat_card if only 1 numeric col
        if numeric_cols and len(columns) > 1:
            x_key = [c for c in columns if c not in numeric_cols]
            x_col = x_key[0] if x_key else columns[0]
            y_col = numeric_cols[0]
            return "bar", {
                "title": f"{y_col.replace('_', ' ').title()} Overview",
                "xKey": x_col,
                "yKeys": [y_col],
                "xAxis": x_col,
                "yAxis": y_col,
                "colors": [cls.PALETTE[0]]
            }

        return "stat_card", {
            "title": "Total Records",
            "value": str(row_count),
            "raw_value": row_count
        }

chart_service = ChartService()
