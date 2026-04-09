"""
系统名称管理路由 - 仅供 Admin 用户管理系统的列表
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.system_name import SystemNameCreate, SystemNameResponse
from app.models.system_name import SystemName
from app.models.user import User, UserRole
from app.core.permissions import get_current_user_from_token, require_role
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=List[SystemNameResponse])
async def list_system_names(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """获取所有系统名称列表（所有登录用户可读取）"""
    query = db.query(SystemName).order_by(SystemName.name.asc())
    return query.all()


@router.post("", response_model=SystemNameResponse)
@require_role(UserRole.ADMIN)
async def create_system_name(
    system_name_data: SystemNameCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """创建新的系统名称（仅 Admin）"""
    # 检查是否已存在
    existing = db.query(SystemName).filter(SystemName.name == system_name_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="系统名称已存在")

    system_name = SystemName(name=system_name_data.name)
    db.add(system_name)
    db.commit()
    db.refresh(system_name)

    logger.info(f"Admin {current_user.id} 创建系统名称：{system_name.name}")
    return system_name


@router.put("/{system_name_id}", response_model=SystemNameResponse)
@require_role(UserRole.ADMIN)
async def update_system_name(
    system_name_id: int,
    update_data: SystemNameCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """更新系统名称（仅 Admin）"""
    system_name = db.query(SystemName).filter(SystemName.id == system_name_id).first()
    if not system_name:
        raise HTTPException(status_code=404, detail="系统名称不存在")

    # 检查新名称是否与其他名称冲突
    existing = db.query(SystemName).filter(
        SystemName.name == update_data.name,
        SystemName.id != system_name_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="系统名称已存在")

    system_name.name = update_data.name
    db.commit()
    db.refresh(system_name)

    logger.info(f"Admin {current_user.id} 更新系统名称：{system_name.name}")
    return system_name


@router.delete("/{system_name_id}")
@require_role(UserRole.ADMIN)
async def delete_system_name(
    system_name_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """删除系统名称（仅 Admin）"""
    system_name = db.query(SystemName).filter(SystemName.id == system_name_id).first()
    if not system_name:
        raise HTTPException(status_code=404, detail="系统名称不存在")

    db.delete(system_name)
    db.commit()

    logger.info(f"Admin {current_user.id} 删除系统名称：{system_name.name}")
    return {"success": True}
