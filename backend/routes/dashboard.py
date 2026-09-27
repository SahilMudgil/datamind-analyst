import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from database import get_db
from models.models import User, DashboardWidget, DatabaseConnection, Bookmark, Message
from services.auth_service import get_current_user
from agent.executor import execute_sql_safely
from services.schema_service import schema_service
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard Widgets"])


# Schemas
class WidgetCreateSchema(BaseModel):
    connection_id: int
    title: str
    sql_query: str
    chart_type: str
    chart_config: Optional[Dict[str, Any]] = None
    position_x: Optional[int] = 0
    position_y: Optional[int] = 0
    width: Optional[int] = 1
    height: Optional[int] = 1


class WidgetResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    connection_id: int
    title: str
    sql_query: str
    chart_type: str
    chart_config: Optional[Dict[str, Any]] = None
    position_x: int
    position_y: int
    width: int
    height: int
    created_at: Optional[datetime] = None


@router.post("/widgets", response_model=WidgetResponseSchema, status_code=status.HTTP_201_CREATED)
def create_dashboard_widget(
    data: WidgetCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pin a query chart as a widget to the user's dashboard."""
    widget = DashboardWidget(
        user_id=current_user.id,
        connection_id=data.connection_id,
        title=data.title,
        sql_query=data.sql_query,
        chart_type=data.chart_type,
        chart_config=data.chart_config,
        position_x=data.position_x or 0,
        position_y=data.position_y or 0,
        width=data.width or 1,
        height=data.height or 1
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


@router.get("/widgets", response_model=List[WidgetResponseSchema])
def list_dashboard_widgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all dashboard widgets pinned by the current user."""
    return db.query(DashboardWidget).filter(
        DashboardWidget.user_id == current_user.id
    ).order_by(DashboardWidget.created_at.desc()).all()


@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard_widget(
    widget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a widget from the user's dashboard."""
    widget = db.query(DashboardWidget).filter(
        DashboardWidget.id == widget_id,
        DashboardWidget.user_id == current_user.id
    ).first()
    if not widget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found.")
    
    db.delete(widget)
    db.commit()
    return None


@router.post("/widgets/{widget_id}/refresh")
def refresh_widget_data(
    widget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Re-execute the widget's SQL query and return live data."""
    widget = db.query(DashboardWidget).filter(
        DashboardWidget.id == widget_id,
        DashboardWidget.user_id == current_user.id
    ).first()
    if not widget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found.")

    conn_record = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == widget.connection_id
    ).first()
    if not conn_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database connection not found.")

    # Determine target engine
    if conn_record.db_type in ("csv_import", "sqlite") or getattr(db.get_bind(), "dialect", None) and db.get_bind().dialect.name == "sqlite":
        target_engine = db.get_bind()
    else:
        url = schema_service.build_connection_url(conn_record)
        target_engine = create_engine(url, connect_args={"connect_timeout": 5})

    result = execute_sql_safely(
        sql_query=widget.sql_query,
        target_engine=target_engine,
        timeout_seconds=10
    )
    return {
        "widget_id": widget.id,
        "title": widget.title,
        "chart_type": widget.chart_type,
        "chart_config": widget.chart_config,
        "data": result.get("rows", []),
        "columns": result.get("column_names", []),
        "row_count": result.get("row_count", 0),
        "success": result.get("success", False),
        "error": result.get("error")
    }


@router.get("/widgets/live")
def get_all_widgets_live(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all dashboard widgets with fresh execution data."""
    widgets = db.query(DashboardWidget).filter(
        DashboardWidget.user_id == current_user.id
    ).order_by(DashboardWidget.position_y.asc(), DashboardWidget.position_x.asc()).all()

    live_widgets = []
    for w in widgets:
        conn_record = db.query(DatabaseConnection).filter(
            DatabaseConnection.id == w.connection_id
        ).first()

        data_rows = []
        col_names = []
        if conn_record:
            if conn_record.db_type in ("csv_import", "sqlite") or getattr(db.get_bind(), "dialect", None) and db.get_bind().dialect.name == "sqlite":
                target_engine = db.get_bind()
            else:
                url = schema_service.build_connection_url(conn_record)
                target_engine = create_engine(url, connect_args={"connect_timeout": 5})

            result = execute_sql_safely(
                sql_query=w.sql_query,
                target_engine=target_engine,
                timeout_seconds=10
            )
            data_rows = result.get("rows", [])
            col_names = result.get("column_names", [])

        live_widgets.append({
            "id": w.id,
            "title": w.title,
            "connection_id": w.connection_id,
            "sql_query": w.sql_query,
            "chart_type": w.chart_type,
            "chart_config": w.chart_config,
            "position_x": w.position_x,
            "position_y": w.position_y,
            "width": w.width,
            "height": w.height,
            "data": data_rows,
            "columns": col_names,
            "created_at": w.created_at
        })

    return live_widgets


# --- Bookmark Schemas & Endpoints ---

class BookmarkCreateSchema(BaseModel):
    message_id: int
    label: str
    folder: Optional[str] = "General"


@router.post("/bookmarks", status_code=status.HTTP_201_CREATED)
def create_bookmark(
    data: BookmarkCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save an analytical insight or query as a bookmark."""
    msg = db.query(Message).filter(Message.id == data.message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

    bookmark = Bookmark(
        user_id=current_user.id,
        message_id=data.message_id,
        label=data.label,
        folder=data.folder or "General"
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return {
        "id": bookmark.id,
        "user_id": bookmark.user_id,
        "message_id": bookmark.message_id,
        "label": bookmark.label,
        "folder": bookmark.folder,
        "created_at": bookmark.created_at
    }


@router.get("/bookmarks")
def list_bookmarks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all bookmarks saved by the current user."""
    bookmarks = db.query(Bookmark).filter(Bookmark.user_id == current_user.id).order_by(Bookmark.created_at.desc()).all()
    results = []
    for b in bookmarks:
        msg = db.query(Message).filter(Message.id == b.message_id).first()
        results.append({
            "id": b.id,
            "user_id": b.user_id,
            "message_id": b.message_id,
            "label": b.label,
            "folder": b.folder,
            "created_at": b.created_at,
            "final_sql": msg.final_sql if msg else None,
            "content": msg.content if msg else None,
            "chart_type": msg.chart_type if msg else None
        })
    return results


@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_200_OK)
def delete_bookmark(
    bookmark_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a saved bookmark."""
    b = db.query(Bookmark).filter(
        Bookmark.id == bookmark_id,
        Bookmark.user_id == current_user.id
    ).first()
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found.")
    db.delete(b)
    db.commit()
    return {"message": "Bookmark deleted successfully", "id": bookmark_id}

