"""
组件管理相关路由
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.component import (
    ComponentCreate,
    ComponentResponse,
    ComponentMatchResponse,
    BlackDuckReportUpload,
    ComponentUpdate,
)
from app.services.black_duck import black_duck_service
from app.services.component_match import get_component_match_service
from app.models.component import Component
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=List[ComponentResponse])
async def list_components(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    license_risk: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取组件列表（支持搜索和过滤）"""
    query = db.query(Component)

    if search:
        query = query.filter(Component.name.ilike(f"%{search}%"))

    if license_risk:
        query = query.filter(Component.license_risk_level == license_risk)

    components = query.offset(skip).limit(limit).all()
    return components


@router.get("/{component_id}", response_model=ComponentResponse)
async def get_component(component_id: int, db: Session = Depends(get_db)):
    """获取组件详情"""
    component = db.query(Component).filter(Component.id == component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return component


@router.post("/blackduck", response_model=List[ComponentResponse])
async def upload_black_duck_report(
    request: BlackDuckReportUpload,
    db: Session = Depends(get_db),
):
    """
    上传 Black Duck 报告 ID，解析组件

    同步/异步模式：
    - <=50 个组件：同步处理，直接返回结果
    - >50 个组件：异步处理，返回任务 ID（需要轮询）
    """
    # 获取报告数据
    report_data = await black_duck_service.fetch_report(request.report_id)
    components_data = await black_duck_service.parse_components(report_data)

    # 检查是否应该用异步
    if black_duck_service.should_use_async(len(components_data)):
        # TODO: 实现异步处理
        logger.info(f"组件数量超过阈值，应该使用异步处理：{len(components_data)}")

    # 创建或更新组件
    created_components = []
    match_service = get_component_match_service(db)

    for comp_data in components_data:
        # 检查是否已存在
        existing, match, _ = match_service.get_match_result(
            comp_data["name"],
            comp_data["version"],
        )

        if existing:
            # 已存在，跳过或更新
            logger.info(f"组件已存在：{comp_data['name']}@{comp_data['version']}")
            continue

        # 创建新组件
        component = Component(
            name=comp_data["name"],
            version=comp_data["version"],
            license=comp_data["license"],
            copyright=comp_data["copyright"],
            usage_type=comp_data["usage_type"],
            license_risk_level=comp_data["license_risk_level"],
            black_duck_report_id=request.report_id,
        )
        db.add(component)
        created_components.append(component)

    db.commit()

    logger.info(f"成功创建 {len(created_components)} 个组件")
    return created_components


@router.post("/match", response_model=ComponentMatchResponse)
async def match_component(
    name: str = Query(...),
    version: str = Query(...),
    db: Session = Depends(get_db),
):
    """匹配组件（检查是否已存在）"""
    match_service = get_component_match_service(db)
    is_match, matched_component, similar = match_service.get_match_result(name, version)

    if is_match:
        return ComponentMatchResponse(
            matched=True,
            existing_component=matched_component,
            message="找到历史合规结论，可以一键复用",
        )
    elif similar:
        return ComponentMatchResponse(
            matched=False,
            existing_component=None,
            message=f"未找到完全匹配，但找到 {len(similar)} 个同名不同版本的组件",
        )
    else:
        return ComponentMatchResponse(
            matched=False,
            existing_component=None,
            message="首次发现此组件，请填写合规信息",
        )


@router.put("/{component_id}", response_model=ComponentResponse)
async def update_component(
    component_id: int,
    update_data: ComponentUpdate,
    db: Session = Depends(get_db),
):
    """更新组件信息"""
    component = db.query(Component).filter(Component.id == component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    # 更新字段
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(component, field, value)

    db.commit()
    db.refresh(component)

    return component
