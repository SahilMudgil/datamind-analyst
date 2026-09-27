from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from database import get_db
from models.models import User
from services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)

from pydantic import BaseModel, EmailStr, ConfigDict

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class RegisterSchema(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None

class TokenResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponseSchema

@router.post("/register", response_model=TokenResponseSchema, status_code=status.HTTP_201_CREATED)
def register(user_data: RegisterSchema, db: Session = Depends(get_db)):
    # Check if email exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    hashed_pw = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_pw,
        name=user_data.name or user_data.email.split("@")[0]
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": new_user.email, "user_id": new_user.id})
    return TokenResponseSchema(
        access_token=token,
        token_type="bearer",
        user=UserResponseSchema.model_validate(new_user)
    )

@router.post("/login", response_model=TokenResponseSchema)
def login(creds: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == creds.email).first()
    if not user or not verify_password(creds.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    token = create_access_token({"sub": user.email, "user_id": user.id})
    return TokenResponseSchema(
        access_token=token,
        token_type="bearer",
        user=UserResponseSchema.model_validate(user)
    )

@router.get("/me", response_model=UserResponseSchema)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return UserResponseSchema.model_validate(current_user)
