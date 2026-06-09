from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, field_validator
import re
import uuid

from database import get_db
from database.crud import (
    get_user_by_email, get_user_by_username, create_user, create_session,
    revoke_user_sessions, update_user_login, create_audit_log,
)
from auth.password import hash_password, verify_password
from auth.jwt import create_access_token, create_refresh_token, verify_token
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, v):
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("username")
    @classmethod
    def valid_username(cls, v):
        if len(v) < 3 or len(v) > 30:
            raise ValueError("Username must be 3-30 characters")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscores, hyphens")
        return v

    @field_validator("password")
    @classmethod
    def valid_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain letters and numbers")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def lower_email(cls, v):
        return v.lower()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    role: str
    plan: str
    created_at: str


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: RegisterRequest, req: Request, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, request.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    existing = await get_user_by_username(db, request.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    hashed = hash_password(request.password)
    user = await create_user(db, request.email, request.username, hashed)

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)
    await create_session(db, user.id, access_token, refresh_token,
                         ip=req.client.host if req.client else None,
                         ua=req.headers.get("user-agent"))
    await create_audit_log(db, user.id, "register", ip=req.client.host if req.client else None,
                           ua=req.headers.get("user-agent"))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"id": str(user.id), "email": user.email, "username": user.username,
              "role": user.role, "plan": user.plan}
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, req: Request, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, request.email)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)
    await create_session(db, user.id, access_token, refresh_token,
                         ip=req.client.host if req.client else None,
                         ua=req.headers.get("user-agent"))
    await update_user_login(db, user.id)
    await create_audit_log(db, user.id, "login", ip=req.client.host if req.client else None,
                           ua=req.headers.get("user-agent"))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"id": str(user.id), "email": user.email, "username": user.username,
              "role": user.role, "plan": user.plan}
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_req: RefreshTokenRequest, req: Request, db: AsyncSession = Depends(get_db)):
    payload = verify_token(refresh_req.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload.get("sub")
    from database.crud import get_user_by_id
    user = await get_user_by_id(db, uuid.UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)
    await create_session(db, user.id, access_token, refresh_token,
                         ip=req.client.host if req.client else None,
                         ua=req.headers.get("user-agent"))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"id": str(user.id), "email": user.email, "username": user.username,
              "role": user.role, "plan": user.plan}
    )


@router.post("/logout")
async def logout(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await revoke_user_sessions(db, user.id)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(user=Depends(get_current_user)):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        role=user.role,
        plan=user.plan,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )
