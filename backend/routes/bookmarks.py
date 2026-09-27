import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from database import get_db
from models.models import User, Bookmark, Message
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])


class BookmarkCreateSchema(BaseModel):
    message_id: int
    label: str
    folder: Optional[str] = "General"


class BookmarkResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    message_id: int
    label: str
    folder: str
    created_at: Optional[datetime] = None

    # Joined message info
    content: Optional[str] = None
    final_sql: Optional[str] = None
    chart_type: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None


@router.post("", response_model=BookmarkResponseSchema, status_code=status.HTTP_201_CREATED)
def create_bookmark(
    data: BookmarkCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save an assistant response as a bookmark."""
    # Verify message exists
    message = db.query(Message).filter(Message.id == data.message_id).first()
    if not message:
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

    return BookmarkResponseSchema(
        id=bookmark.id,
        user_id=bookmark.user_id,
        message_id=bookmark.message_id,
        label=bookmark.label,
        folder=bookmark.folder,
        created_at=bookmark.created_at,
        content=message.content,
        final_sql=message.final_sql,
        chart_type=message.chart_type,
        chart_config=message.chart_config
    )


@router.get("", response_model=List[BookmarkResponseSchema])
def list_bookmarks(
    folder: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all bookmarks saved by current user."""
    query = db.query(Bookmark).filter(Bookmark.user_id == current_user.id)
    if folder:
        query = query.filter(Bookmark.folder == folder)
    bookmarks = query.order_by(Bookmark.created_at.desc()).all()

    results = []
    for b in bookmarks:
        msg = db.query(Message).filter(Message.id == b.message_id).first()
        results.append(
            BookmarkResponseSchema(
                id=b.id,
                user_id=b.user_id,
                message_id=b.message_id,
                label=b.label,
                folder=b.folder,
                created_at=b.created_at,
                content=msg.content if msg else None,
                final_sql=msg.final_sql if msg else None,
                chart_type=msg.chart_type if msg else None,
                chart_config=msg.chart_config if msg else None
            )
        )
    return results


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
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
    return None
