from datetime import datetime, timedelta, timezone
from typing import Optional
from app.models.user import User  
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt
from app.core.config import settings
from app.core.database import get_db


# ── Redis 连接 ──
# 从 Redis 取出来的数据自动转成 str，默认是 bytes
redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


security_scheme = HTTPBearer()


# ─── 密码工具 ────────────────────────────────────────────
def hash_password(password: str) -> str:
     return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ─── JWT 工具 ────────────────────────────────────────────
def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """解析 token，出错统一抛 401"""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")


# ─── 黑名单（登出 / 强制下线）────────────────────────────
async def blacklist_token(token: str, expire_seconds: int):
    """将 token 加入 Redis 黑名单，过期时间跟随 token 剩余有效期"""
    await redis.setex(f"blacklist:{token}", expire_seconds, "1")


async def is_token_blacklisted(token: str) -> bool:
    return await redis.exists(f"blacklist:{token}") > 0


# ─── 获取当前用户（FastAPI 依赖）──────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    """解析 token → 查黑名单 → 查数据库 → 返回用户"""


    payload = decode_token(credentials.credentials)

    # 检查黑名单
    if await is_token_blacklisted(credentials.credentials):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="凭据已失效，请重新登录")

    user_id = int(payload.get("sub"))
    result = await db.get(User, user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return result