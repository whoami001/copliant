"""
基于角色的访问控制 (RBAC)

提供权限校验装饰器和权限规则定义
"""

from functools import wraps
from typing import List, Callable
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User, UserRole
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()
security = HTTPBearer()


def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    从 JWT Token 中解析当前用户

    返回数据库中的真实用户对象
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        email = payload.get("email")

        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # 从数据库获取真实用户
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # 如果用户不存在于数据库，返回虚拟用户（兼容旧数据）
            role_str = payload.get("role", "engineer")
            return User(
                id=1,
                email=email,
                name="MVP User",
                role=getattr(UserRole, role_str.upper(), UserRole.ENGINEER),
                is_active=True
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token 解析失败：{e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败"
        )


def require_role(allowed_roles: List[UserRole]):
    """
    权限校验装饰器

    用法:
        @router.post("/approve")
        @require_role([UserRole.SECURITY, UserRole.ADMIN])
        async def approve_record(...):
            ...

    Args:
        allowed_roles: 允许访问的角色列表
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中获取 db 和 current_user
            db = None
            current_user = None

            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Session):
                    db = arg

            # 如果没有传入用户对象，尝试从 kwargs 获取
            if current_user is None:
                for key, value in kwargs.items():
                    if isinstance(value, User):
                        current_user = value
                    elif isinstance(value, Session) and db is None:
                        db = value

            # 校验角色 (ADMIN 自动通行所有权限)
            if current_user and current_user.role != UserRole.ADMIN and current_user.role not in allowed_roles:
                role_names = [r.value for r in allowed_roles]
                logger.warning(
                    f"用户 {current_user.email} (角色：{current_user.role.value}) "
                    f"尝试访问需要角色 {role_names} 的资源"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "INSUFFICIENT_PERMISSION",
                        "required_roles": role_names,
                        "message": f"权限不足：需要以下角色之一 {', '.join(role_names)}"
                    }
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def has_permission(user: User, allowed_roles: List[UserRole]) -> bool:
    """
    检查用户是否有指定权限

    Args:
        user: 用户对象
        allowed_roles: 允许的角色列表

    Returns:
        True 表示有权限
    """
    return user.role in allowed_roles or user.role == UserRole.ADMIN


# 权限规则常量
# 定义各操作允许的最低角色
PERMISSIONS = {
    "view_own_records": [UserRole.ENGINEER, UserRole.SECURITY, UserRole.LEGAL, UserRole.ADMIN],
    "view_all_records": [UserRole.SECURITY, UserRole.LEGAL, UserRole.ADMIN],
    "create_declaration": [UserRole.ENGINEER, UserRole.ADMIN],
    "submit_declaration": [UserRole.ENGINEER, UserRole.ADMIN],
    "security_review": [UserRole.SECURITY, UserRole.ADMIN],
    "legal_approve": [UserRole.LEGAL, UserRole.ADMIN],
    "bulk_import": [UserRole.ENGINEER, UserRole.ADMIN],
    "export_data": [UserRole.SECURITY, UserRole.LEGAL, UserRole.ADMIN],
    "manage_users": [UserRole.ADMIN],
    "manage_settings": [UserRole.ADMIN],
}


def can(user: User, permission: str) -> bool:
    """
    检查用户是否有指定权限

    用法:
        if can(current_user, "bulk_import"):
            # 允许批量导入

    Args:
        user: 用户对象
        permission: 权限名称

    Returns:
        True 表示有权限
    """
    allowed_roles = PERMISSIONS.get(permission, [])
    if not allowed_roles:
        return False
    return has_permission(user, allowed_roles)
