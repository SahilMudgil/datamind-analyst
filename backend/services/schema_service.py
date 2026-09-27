import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from models.models import DatabaseConnection, SchemaCache, CSVUpload
from services.encryption_service import decrypt_credential
from services.embedding_service import embedding_service
from config import settings

logger = logging.getLogger(__name__)


def generate_heuristic_description(
    table_name: str,
    column_name: str,
    data_type: str,
    is_pk: bool = False,
    is_fk: bool = False,
    ref_table: Optional[str] = None
) -> str:
    """Generate high-quality plain-English heuristic descriptions for schema elements."""
    col_lower = column_name.lower()
    table_lower = table_name.lower()

    if is_pk:
        return f"Primary unique identifier for records in the '{table_name}' table."

    if is_fk and ref_table:
        return f"Foreign key referencing '{ref_table}.id', linking this record to its corresponding {ref_table[:-1] if ref_table.endswith('s') else ref_table}."

    if col_lower in ("created_at", "inserted_at"):
        return f"Timestamp recording when the '{table_name}' entry was originally created."
    if col_lower in ("updated_at", "modified_at"):
        return f"Timestamp recording the last time this '{table_name}' record was modified."
    if "date" in col_lower or "time" in col_lower:
        return f"Date or timestamp representing '{column_name}' for this {table_name} record."

    if col_lower in ("email", "user_email"):
        return "Customer or user email address used for contact and identity."
    if col_lower in ("name", "full_name", "customer_name"):
        return f"Name of the {table_name[:-1] if table_name.endswith('s') else table_name}."
    if col_lower in ("title", "product_name"):
        return "Descriptive title or name of the item."
    if col_lower in ("price", "unit_price"):
        return "Unit selling price of the product in standard currency."
    if col_lower in ("total_amount", "order_total", "amount"):
        return "Total financial transaction amount including applicable taxes, shipping, and discounts."
    if col_lower in ("quantity", "qty", "count"):
        return "Quantity or number of units associated with this transaction."
    if col_lower in ("status", "order_status", "payment_status"):
        return f"Operational state or status code of the {table_name} record (e.g. pending, completed, cancelled)."
    if col_lower in ("city", "state", "country", "postal_code", "zip_code", "region"):
        return f"Geographical {column_name.replace('_', ' ')} location attribute for demographic and regional analytics."
    if col_lower in ("category", "product_category", "type"):
        return f"Classification or group category for segmentation in '{table_name}'."
    if col_lower in ("phone", "phone_number"):
        return "Contact telephone number."
    if "rate" in col_lower or "percentage" in col_lower or "discount" in col_lower:
        return f"Percentage or decimal multiplier for {column_name.replace('_', ' ')}."

APP_INTERNAL_TABLES = {
    "users", "database_connections", "schema_cache", "csv_uploads",
    "conversations", "messages", "agent_steps", "query_cache",
    "dashboard_widgets", "bookmarks", "llm_usage_logs", "alembic_version"
}


class SchemaService:
    generate_ai_description = staticmethod(generate_heuristic_description)
    generate_heuristic_description = staticmethod(generate_heuristic_description)

    @staticmethod
    def build_connection_url(conn: DatabaseConnection) -> str:
        """Construct SQLAlchemy connection string from connection model."""
        if conn.db_type == "csv_import" or not conn.host:
            # For CSV or internal tables, fallback to app database
            return settings.DATABASE_URL

        password = decrypt_credential(conn.password_encrypted) if conn.password_encrypted else ""
        user = conn.username or ("root" if conn.db_type == "mysql" else "postgres")
        host = conn.host or "localhost"
        port = int(conn.port) if conn.port else (3306 if conn.db_type == "mysql" else 5432)
        db_name = conn.db_name or "postgres"

        driver = "mysql+pymysql" if conn.db_type == "mysql" else "postgresql"
        url_obj = URL.create(
            drivername=driver,
            username=user,
            password=password,
            host=host,
            port=port,
            database=db_name
        )
        return url_obj.render_as_string(hide_password=False)

    @staticmethod
    def test_connection_params(
        db_type: str,
        host: str,
        port: int,
        db_name: str,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """Test database connection parameters without saving."""
        if db_type == "sqlite":
            url_obj = URL.create(drivername="sqlite", database=db_name)
        elif db_type in ("postgresql", "mysql"):
            driver = "mysql+pymysql" if db_type == "mysql" else "postgresql"
            url_obj = URL.create(
                drivername=driver,
                username=username,
                password=password,
                host=host,
                port=int(port) if port else (3306 if db_type == "mysql" else 5432),
                database=db_name
            )
        else:
            return {"success": False, "error": f"Unsupported database type: {db_type}"}

        try:
            connect_args = {"connect_timeout": 5} if db_type in ("postgresql", "mysql") else {}
            test_engine = create_engine(url_obj, connect_args=connect_args)
            with test_engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            return {"success": True, "message": "Connection established successfully."}
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    async def introspect_and_cache(
        cls,
        connection: DatabaseConnection,
        db: Session,
        engine_override=None,
        table_name_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Introspect tables, columns, primary keys, and foreign keys, then populate schema cache with AI descriptions and embeddings."""
        if engine_override:
            eng = engine_override
        elif connection.db_type == "csv_import":
            eng = db.get_bind()
        else:
            url = cls.build_connection_url(connection)
            connect_args = {"connect_timeout": 8} if connection.db_type in ("postgresql", "mysql") else {}
            eng = create_engine(url, connect_args=connect_args)

        try:
            inspector = inspect(eng)
            table_names = inspector.get_table_names()

            # Filter tables: if table_name_filter is provided (e.g. for CSV upload), use only that table
            if table_name_filter:
                tables_to_index = [t for t in table_names if t == table_name_filter]
            elif connection.db_type == "csv_import":
                # Find table name from csv_uploads if not explicitly passed
                csv_rec = db.query(CSVUpload).filter(CSVUpload.connection_id == connection.id).first()
                if csv_rec and csv_rec.table_name in table_names:
                    tables_to_index = [csv_rec.table_name]
                else:
                    tables_to_index = [t for t in table_names if t not in APP_INTERNAL_TABLES and not t.startswith("pg_")]
            else:
                tables_to_index = [t for t in table_names if t not in APP_INTERNAL_TABLES and not t.startswith("pg_")]

            # Clear previous schema cache for this connection
            db.query(SchemaCache).filter(SchemaCache.connection_id == connection.id).delete()
            db.commit()

            cached_items = []
            texts_to_embed = []

            for t_name in tables_to_index:
                pk_cols = set(inspector.get_pk_constraint(t_name).get("constrained_columns", []))
                fk_info = {}
                try:
                    for fk in inspector.get_foreign_keys(t_name):
                        ref_table = fk.get("referred_table")
                        for col in fk.get("constrained_columns", []):
                            fk_info[col] = ref_table
                except Exception:
                    pass

                columns = inspector.get_columns(t_name)
                for col in columns:
                    col_name = col["name"]
                    data_type = str(col["type"])
                    is_pk = col_name in pk_cols
                    is_fk = col_name in fk_info
                    ref_table = fk_info.get(col_name)

                    description = generate_heuristic_description(
                        table_name=t_name,
                        column_name=col_name,
                        data_type=data_type,
                        is_pk=is_pk,
                        is_fk=is_fk,
                        ref_table=ref_table
                    )

                    texts_to_embed.append(f"Table: {t_name} | Column: {col_name} ({data_type}) | {description}")

                    cached_items.append({
                        "connection_id": connection.id,
                        "table_name": t_name,
                        "column_name": col_name,
                        "data_type": data_type,
                        "is_primary_key": is_pk,
                        "is_foreign_key": is_fk,
                        "references_table": ref_table,
                        "ai_description": description,
                    })

            # Batch compute vector embeddings
            embeddings = await embedding_service.get_embeddings_batch(texts_to_embed)

            # Insert into database
            for item, emb in zip(cached_items, embeddings):
                record = SchemaCache(
                    connection_id=item["connection_id"],
                    table_name=item["table_name"],
                    column_name=item["column_name"],
                    data_type=item["data_type"],
                    is_primary_key=item["is_primary_key"],
                    is_foreign_key=item["is_foreign_key"],
                    references_table=item["references_table"],
                    ai_description=item["ai_description"],
                    description_embedding=emb
                )
                db.add(record)

            db.commit()

            return {
                "success": True,
                "table_count": len(tables_to_index),
                "column_count": len(cached_items),
                "tables": tables_to_index
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error during schema introspection for connection {connection.id}: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_connection_schema(connection_id: int, db: Session) -> Dict[str, Any]:
        """Fetch full cached schema organized hierarchically by table."""
        rows = (
            db.query(SchemaCache)
            .filter(SchemaCache.connection_id == connection_id)
            .order_by(SchemaCache.table_name, SchemaCache.id)
            .all()
        )

        tables_map: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            if row.table_name not in tables_map:
                tables_map[row.table_name] = []
            tables_map[row.table_name].append({
                "id": row.id,
                "name": row.column_name,
                "column_name": row.column_name,
                "data_type": row.data_type,
                "is_primary_key": row.is_primary_key,
                "is_foreign_key": row.is_foreign_key,
                "references_table": row.references_table,
                "ai_description": row.ai_description,
                "has_embedding": row.description_embedding is not None
            })

        table_list = [
            {
                "name": t_name,
                "table_name": t_name,
                "column_count": len(cols),
                "columns": cols
            }
            for t_name, cols in tables_map.items()
        ]

        return {
            "connection_id": connection_id,
            "table_count": len(table_list),
            "tables": table_list
        }


schema_service = SchemaService()
