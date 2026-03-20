"""用户相关 Schema"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    """用户基础 Schema"""
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    """创建用户请求"""
    pass


class UserUpdate(BaseModel):
    """更新用户请求"""
    name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """用户响应"""
    id: int
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserResponse):
    """数据库中的用户对象（内部使用）"""
    pass
