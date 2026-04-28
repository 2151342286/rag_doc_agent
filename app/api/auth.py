from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from fastapi import Depends
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    blacklist_token,
    is_token_blacklisted,
    security_scheme,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register(db, payload.username, payload.email, payload.password)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    tokens = await auth_service.login(db, payload.username, payload.password)
    return tokens

@router.post("/logout")
async def logout(
    credentials = Depends(security_scheme),
    refresh_token: str = Body(None),
):
    token = credentials.credentials 
    payload = decode_token(token)
    now = int(datetime.now(timezone.utc).timestamp())
    remaining = payload["exp"] - now
    await blacklist_token(token, max(remaining, 1))
    # 拉黑 refresh_token（如果有传）
    if refresh_token:
        refresh_payload = decode_token(refresh_token)
        refresh_remaining = refresh_payload["exp"] - now
        await blacklist_token(refresh_token, max(refresh_remaining, 1))

    return {"msg": "已登出"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    """用 refresh_token 换取新的 access_token"""
    payload = decode_token(refresh_token)
    
    # 验证必须是 refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的刷新令牌")
    
    # 检查黑名单
    if await is_token_blacklisted(refresh_token):
        raise HTTPException(status_code=401, detail="刷新令牌已失效")
    
    user_id = int(payload.get("sub"))
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    # 签发新的 access_token
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),  # 同时发新的 refresh_token
        "token_type": "bearer",
    }