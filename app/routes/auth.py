"""
认证相关路由

提供邮箱验证码登录（MVP 版本，后续可对接 SSO）
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas.auth import EmailLoginRequest, Token
from app.schemas.user import UserResponse
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter()

security = HTTPBearer()


# MVP 版本：简化的认证逻辑
# 生产环境应该对接邮箱验证码或 SSO

@router.post("/login", response_model=Token)
async def login(request: EmailLoginRequest, db: Session = Depends(get_db)):
    """
    邮箱验证码登录

    MVP 版本：任何邮箱 + 任意 code 都可以登录（用于开发测试）
    如果邮箱存在于数据库，返回对应用户信息和角色
    如果邮箱不存在，创建一个新的工程师角色用户
    生产环境需要实现真实的验证码发送和校验
    """
    # 查找或创建用户
    user = db.query(User).filter(User.email == request.email).first()

    if user:
        # 用户已存在，使用真实信息
        user_id = str(user.id)
        role = user.role.value
        logger.info(f"用户 {request.email} ({user.name}) 登录成功，角色：{role}")
    else:
        # 用户不存在，创建默认工程师角色
        user_id = "mvp-user"
        role = "engineer"
        logger.info(f"新用户 {request.email} 登录成功，角色：{role} (默认)")

    # 创建 token
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    token_data = {
        "sub": user_id,
        "exp": expire,
        "role": role,
        "email": request.email,
    }

    access_token = jwt.encode(
        token_data,
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """获取当前登录用户信息"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # 尝试从数据库获取真实用户
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                return UserResponse(
                    id=user.id,
                    email=user.email,
                    name=user.name,
                    role=user.role.value,
                    is_active=user.is_active,
                    created_at=user.created_at,
                )

        # 返回虚拟用户（旧用户兼容）
        return UserResponse(
            id=1,
            email=email or "mvp@company.com",
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
