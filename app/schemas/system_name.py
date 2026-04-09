"""
系统名称管理 Schema
"""

from pydantic import BaseModel, Field


class SystemNameCreate(BaseModel):
    """创建系统名称"""
    name: str = Field(..., min_length=1, max_length=100, description="系统名称")


class SystemNameResponse(BaseModel):
    """系统名称响应"""
    id: int
    name: str

    class Config:
        from_attributes = True
