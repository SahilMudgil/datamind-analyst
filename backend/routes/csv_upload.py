import logging
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.models import User
from services.auth_service import get_current_user
from services.csv_service import csv_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/csv", tags=["CSV Ingestion"])


@router.post("/preview")
async def preview_csv_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Parse uploaded CSV and return sanitized column headers and top rows for client-side preview."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files (.csv) are currently supported."
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded CSV file is empty."
        )

    result = csv_service.preview_csv(file_bytes=file_bytes, max_rows=5)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.get("error", "Failed to parse CSV file.")
        )
    return result


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_csv_file(
    file: UploadFile = File(...),
    table_name: Optional[str] = Form(None),
    custom_table_name: Optional[str] = Form(None),
    display_name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a CSV dataset, persist as a relational database table, create connection, and index schema."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files (.csv) are supported."
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file is empty."
        )

    result = await csv_service.process_and_import_csv(
        file_bytes=file_bytes,
        filename=file.filename,
        user_id=current_user.id,
        db=db,
        custom_table_name=custom_table_name or table_name,
        display_name=display_name
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to process and import CSV dataset.")
        )

    return result
