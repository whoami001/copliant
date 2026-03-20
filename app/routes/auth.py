"""
认证相关路由

提供邮箱验证码登录（MVP 版本，后续可对接 SSO）
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import get_settings
from app.database import get_db
from app.schemas.auth import EmailLoginRequest, Token
from app.schemas.user import UserResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter()

security = HTTPBearer()


# MVP 版本：简化的认证逻辑
# 生产环境应该对接邮箱验证码或 SSO

@router.post("/login", response_model=Token)
async def login(request: EmailLoginRequest):
    """
    邮箱验证码登录

    MVP 版本：任何邮箱 + 任意 code 都可以登录（用于开发测试）
    生产环境需要实现真实的验证码发送和校验
    """
    # MVP: 简化处理，任何邮箱都能登录
    # TODO: 实现真实的验证码校验

    # 创建 token
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    token_data = {
        "sub": "mvp-user",  # MVP 用固定 ID
        "exp": expire,
        "role": "engineer",  # MVP 默认研发角色
    }

    access_token = jwt.encode(
        token_data,
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    logger.info(f"用户 {request.email} 登录成功")

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """获取当前登录用户信息"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id = payload.get("sub")
        role = payload.get("role")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # MVP: 返回虚拟用户
        return UserResponse(
            id=1,
            email="mvp@company.com",
            name="MVP User",
            role=role or "engineer",
            is_active=True,
            created_at=datetime.utcnow(),
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/logout")
async def logout():
    """登出"""
    # MVP 版本：无操作（JWT 无法服务端吊销）
    # 生产环境需要实现 token 黑名单或对接 SSO
    return {"message": "已登出"}
