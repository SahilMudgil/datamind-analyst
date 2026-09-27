import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.models import User, DatabaseConnection, SchemaCache
from services.auth_service import get_current_user
from services.encryption_service import encrypt_credential
from services.schema_service import schema_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/connections", tags=["Database Connections"])


# Request & Response Schemas
class TestConnectionRequest(BaseModel):
    db_type: str = Field(default="postgresql", description="Database engine type")
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    db_name: str = Field(default="postgres")
    username: str = Field(default="postgres")
    password: str = Field(default="")


class CreateConnectionRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    db_type: str = Field(default="postgresql")
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    db_name: str = Field(...)
    username: str = Field(...)
    password: str = Field(...)


class ConnectionResponse(BaseModel):
    id: int
    display_name: str
    db_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    db_name: Optional[str] = None
    username: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


@router.post("/test")
def test_connection(req: TestConnectionRequest, current_user: User = Depends(get_current_user)):
    """Test connection credentials against the target database without persisting."""
    result = schema_service.test_connection_params(
        db_type=req.db_type,
        host=req.host,
        port=req.port,
        db_name=req.db_name,
        username=req.username,
        password=req.password
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Unable to connect to database.")
        )
    return {"success": True, "message": "Connection test successful!"}


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    req: CreateConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save an external database connection, encrypt password, and trigger schema introspection."""
    encrypted_pw = encrypt_credential(req.password)

    new_conn = DatabaseConnection(
        user_id=current_user.id,
        display_name=req.display_name,
        db_type=req.db_type,
        host=req.host,
        port=req.port,
        db_name=req.db_name,
        username=req.username,
        password_encrypted=encrypted_pw
    )
    db.add(new_conn)
    db.commit()
    db.refresh(new_conn)

    # Automatically introspect and cache schema asynchronously/inline
    try:
        await schema_service.introspect_and_cache(connection=new_conn, db=db)
    except Exception as e:
        logger.warning(f"Initial schema introspection encountered error for conn {new_conn.id}: {e}")

    return ConnectionResponse(
        id=new_conn.id,
        display_name=new_conn.display_name,
        db_type=new_conn.db_type,
        host=new_conn.host,
        port=new_conn.port,
        db_name=new_conn.db_name,
        username=new_conn.username,
        created_at=new_conn.created_at.isoformat() if new_conn.created_at else None
    )


@router.get("", response_model=List[ConnectionResponse])
def list_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all database and CSV connections belonging to the current authenticated user."""
    connections = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.user_id == current_user.id)
        .order_by(DatabaseConnection.created_at.desc())
        .all()
    )
    return [
        ConnectionResponse(
            id=c.id,
            display_name=c.display_name,
            db_type=c.db_type,
            host=c.host,
            port=c.port,
            db_name=c.db_name,
            username=c.username,
            created_at=c.created_at.isoformat() if c.created_at else None
        )
        for c in connections
    ]


@router.get("/{connection_id}/schema")
def get_connection_schema(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve full cached schema with plain-English AI explanations for a connection."""
    conn = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.id == connection_id, DatabaseConnection.user_id == current_user.id)
        .first()
    )
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection with id {connection_id} not found."
        )

    schema_data = schema_service.get_connection_schema(connection_id=conn.id, db=db)
    return {
        "connection_id": conn.id,
        "display_name": conn.display_name,
        "db_type": conn.db_type,
        **schema_data
    }


@router.post("/{connection_id}/refresh-schema")
async def refresh_connection_schema(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Re-introspect external database and refresh AI descriptions and embeddings in schema cache."""
    conn = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.id == connection_id, DatabaseConnection.user_id == current_user.id)
        .first()
    )
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection with id {connection_id} not found."
        )

    result = await schema_service.introspect_and_cache(connection=conn, db=db)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to refresh schema cache.")
        )

    return {
        "success": True,
        "message": "Schema cache refreshed successfully.",
        **result
    }


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a database connection and all its associated schema cache and conversations."""
    conn = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.id == connection_id, DatabaseConnection.user_id == current_user.id)
        .first()
    )
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection with id {connection_id} not found."
        )

    # Cleanly remove associated records and connection
    db.query(SchemaCache).filter(SchemaCache.connection_id == connection_id).delete(synchronize_session=False)
    db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).delete(synchronize_session=False)
    db.commit()
    return None
