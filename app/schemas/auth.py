"""认证相关 Schema"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class EmailLoginRequest(BaseModel):
    """邮箱验证码登录请求"""
    email: EmailStr
    code: str


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Token 载荷"""
    sub: str  # user id
    exp: datetime
    role: str
