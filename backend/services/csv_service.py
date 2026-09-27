import io
import re
import logging
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.models import DatabaseConnection, CSVUpload
from services.schema_service import schema_service
from database import engine as default_app_engine
from config import settings

logger = logging.getLogger(__name__)


def sanitize_identifier(name: str, default: str = "item") -> str:
    """Sanitize table and column names into safe SQL identifiers."""
    if not name:
        return default
    # Replace non-alphanumeric chars with underscore
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip())
    # Collapse multiple consecutive underscores
    cleaned = re.sub(r"_+", "_", cleaned).strip("_").lower()
    # Identifiers cannot begin with numbers
    if cleaned and cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    return cleaned or default


class CSVService:
    sanitize_identifier = staticmethod(sanitize_identifier)

    @staticmethod
    def preview_csv(file_bytes: bytes, max_rows: int = 5) -> Dict[str, Any]:
        """Parse CSV and return sanitized columns, sample data, and total count for preview."""
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), nrows=max_rows)
            sanitized_cols = [sanitize_identifier(c, f"col_{i}") for i, c in enumerate(df.columns)]
            # Also get approximate row count quickly
            total_rows = sum(1 for _ in io.BytesIO(file_bytes)) - 1
            return {
                "success": True,
                "columns": sanitized_cols,
                "original_columns": list(df.columns),
                "row_count": max(0, total_rows),
                "preview_rows": df.head(max_rows).fillna("").to_dict(orient="records")
            }
        except Exception as e:
            logger.error(f"Error previewing CSV: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    async def process_and_import_csv(
        cls,
        file_bytes: bytes,
        filename: str,
        user_id: int,
        db: Session,
        custom_table_name: Optional[str] = None,
        display_name: Optional[str] = None,
        target_engine=None
    ) -> Dict[str, Any]:
        """Ingest CSV, create table in database, persist connection & csv_uploads, and build schema cache."""
        try:
            # 1. Read full CSV
            df = pd.read_csv(io.BytesIO(file_bytes))
            
            # 2. Sanitize table and column names
            base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
            raw_table_name = custom_table_name or base_name
            table_name = sanitize_identifier(raw_table_name, "csv_table")
            
            sanitized_cols = [sanitize_identifier(col, f"col_{i}") for i, col in enumerate(df.columns)]
            df.columns = sanitized_cols

            row_count, col_count = df.shape

            # 3. Determine database engine to load table into (use session bound engine by default)
            active_engine = target_engine or db.get_bind()

            # 4. Save DataFrame to database table
            df.to_sql(table_name, con=active_engine, if_exists="replace", index=False)

            # 5. Create DatabaseConnection record
            conn_display = display_name or f"CSV: {filename}"
            db_conn = DatabaseConnection(
                user_id=user_id,
                display_name=conn_display,
                db_type="csv_import",
                db_name=settings.DATABASE_URL.split("/")[-1] if "/" in settings.DATABASE_URL else "app_db",
                host="localhost",
                port=5433
            )
            db.add(db_conn)
            db.flush()

            # 6. Create CSVUpload record
            csv_record = CSVUpload(
                user_id=user_id,
                connection_id=db_conn.id,
                original_filename=filename,
                table_name=table_name,
                row_count=row_count,
                column_count=col_count
            )
            db.add(csv_record)
            db.commit()
            db.refresh(db_conn)

            # 7. Introspect and populate schema cache with AI descriptions & embeddings
            cache_result = await schema_service.introspect_and_cache(
                connection=db_conn,
                db=db,
                engine_override=active_engine,
                table_name_filter=table_name
            )

            return {
                "success": True,
                "connection_id": db_conn.id,
                "display_name": db_conn.display_name,
                "table_name": table_name,
                "row_count": row_count,
                "column_count": col_count,
                "schema_cached": cache_result.get("success", False),
                "columns": sanitized_cols
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error processing CSV import '{filename}': {e}")
            return {"success": False, "error": str(e)}


csv_service = CSVService()
