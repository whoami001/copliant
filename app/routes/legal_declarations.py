"""法务声明相关路由"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.legal_declaration import LegalDeclaration, UsageType, IsModified
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.component import Component
from app.schemas.legal_declaration import (
    LegalDeclarationCreate,
    LegalDeclarationUpdate,
    LegalDeclarationResponse,
    LegalDeclarationDetailResponse,
    LegalDeclarationSubmit,
    BulkImportResult,
    BulkImportItemResult,
    HistorySuggestionResponse,
)
from app.services.spdx_parser import parse_spdx_file, SpdxParseError
from app.services.declaration_history import get_declaration_history_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _is_valid_url(url: str) -> bool:
    """简易 URL 格式验证"""
    if not url:
        return True  # 空值允许（字段可能非必填）
    return url.startswith(("http://", "https://", "ftp://"))


@router.post("", response_model=LegalDeclarationResponse)
async def create_declaration(
    declaration_data: LegalDeclarationCreate,
    db: Session = Depends(get_db),
):
    """创建/提交法务声明

    仅允许 DRAFT 状态的合规记录创建声明。
    """
    # 检查合规记录是否存在
    record = db.query(ComplianceRecord).filter(
        ComplianceRecord.id == declaration_data.compliance_record_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="合规记录不存在")

    # 检查是否已有声明
    existing = db.query(LegalDeclaration).filter(
        LegalDeclaration.compliance_record_id == declaration_data.compliance_record_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该合规记录已有声明，请先删除 existing 声明")

    # 检查状态
    if record.status != RecordStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态不能创建声明：{record.status.value}，仅 DRAFT 状态可创建"
        )

    declaration = LegalDeclaration(
        compliance_record_id=declaration_data.compliance_record_id,
        purpose_of_use=declaration_data.purpose_of_use,
        url_to_source=declaration_data.url_to_source,
        license_info_url=declaration_data.license_info_url,
        license_text_url=declaration_data.license_text_url,
        license_name=declaration_data.license_name,
        is_modified=declaration_data.is_modified,
        usage_type=declaration_data.usage_type,
        submitted_at=datetime.utcnow(),
    )

    db.add(declaration)
    db.commit()
    db.refresh(declaration)

    logger.info(f"创建法务声明：{declaration.id}, 合规记录：{record.id}")
    return declaration


@router.get("/{declaration_id}", response_model=LegalDeclarationResponse)
async def get_declaration(
    declaration_id: int,
    db: Session = Depends(get_db),
):
    """获取法务声明详情"""
    declaration = db.query(LegalDeclaration).filter(
        LegalDeclaration.id == declaration_id
    ).first()
    if not declaration:
        raise HTTPException(status_code=404, detail="声明不存在")
    return declaration


@router.get("/records/{record_id}/declaration", response_model=LegalDeclarationDetailResponse)
async def get_declaration_by_record(
    record_id: int,
    db: Session = Depends(get_db),
):
    """通过合规记录 ID 获取声明（含关联信息）"""
    declaration = db.query(LegalDeclaration).filter(
        LegalDeclaration.compliance_record_id == record_id
    ).first()
    if not declaration:
        raise HTTPException(status_code=404, detail="声明不存在")

    # 获取关联信息
    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == record_id).first()
    component = db.query(Component).filter(Component.id == record.component_id).first() if record else None

    return LegalDeclarationDetailResponse(
        id=declaration.id,
        compliance_record_id=declaration.compliance_record_id,
        purpose_of_use=declaration.purpose_of_use,
        url_to_source=declaration.url_to_source,
        license_info_url=declaration.license_info_url,
        license_text_url=declaration.license_text_url,
        license_name=declaration.license_name,
        is_modified=declaration.is_modified,
        usage_type=declaration.usage_type,
        submitted_at=declaration.submitted_at,
        created_at=declaration.created_at,
        updated_at=declaration.updated_at,
        compliance_record=record,
        component=component,
    )


@router.put("/{declaration_id}", response_model=LegalDeclarationResponse)
async def update_declaration(
    declaration_id: int,
    update_data: LegalDeclarationUpdate,
    db: Session = Depends(get_db),
):
    """更新法务声明

    仅允许 DRAFT 状态的合规记录更新声明。
    """
    declaration = db.query(LegalDeclaration).filter(
        LegalDeclaration.id == declaration_id
    ).first()
    if not declaration:
        raise HTTPException(status_code=404, detail="声明不存在")

    # 检查关联记录状态
    record = db.query(ComplianceRecord).filter(
        ComplianceRecord.id == declaration.compliance_record_id
    ).first()
    if record and record.status != RecordStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态不能修改声明：{record.status.value}，仅 DRAFT 状态可修改"
        )

    # 更新字段
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(declaration, field, value)

    declaration.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(declaration)

    logger.info(f"更新法务声明：{declaration.id}")
    return declaration


@router.post("/{declaration_id}/submit", response_model=LegalDeclarationResponse)
async def submit_declaration(
    declaration_id: int,
    submit_data: LegalDeclarationSubmit,
    db: Session = Depends(get_db),
):
    """提交法务声明（进入审批流程）

    将合规记录从 DRAFT 状态转为 PENDING_SECURITY。
    """
    declaration = db.query(LegalDeclaration).filter(
        LegalDeclaration.id == declaration_id
    ).first()
    if not declaration:
        raise HTTPException(status_code=404, detail="声明不存在")

    record = db.query(ComplianceRecord).filter(
        ComplianceRecord.id == declaration.compliance_record_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="关联的合规记录不存在")

    if record.status != RecordStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态不能提交：{record.status.value}，仅 DRAFT 状态可提交"
        )

    # 更新记录状态
    record.status = RecordStatus.PENDING_SECURITY
    record.submitted_at = datetime.utcnow()

    db.commit()
    db.refresh(declaration)

    logger.info(f"提交法务声明：{declaration.id}, 记录状态：{record.status.value}")
    return declaration


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_declarations(
    file: UploadFile = File(...),
    system_name: str = Query(..., description="系统名称"),
    db: Session = Depends(get_db),
):
    """批量导入法务声明

    上传 SPDX 文件，解析并创建声明草稿。

    返回结果包含成功/失败数量及详细信息。
    """
    # 读取文件内容
    content = await file.read()
    try:
        content_str = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码错误，请使用 UTF-8 编码")

    # 解析 SPDX
    try:
        components = parse_spdx_file(content_str)
    except SpdxParseError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not components:
        raise HTTPException(status_code=400, detail="SPDX 文件中没有找到组件")

    results: List[BulkImportItemResult] = []
    success_count = 0
    failed_count = 0

    for spdx_comp in components:
        try:
            # 查找或创建组件（处理并发冲突）
            component = db.query(Component).filter(
                Component.name == spdx_comp.name,
                Component.version == spdx_comp.version,
            ).first()

            if not component:
                component = Component(
                    name=spdx_comp.name,
                    version=spdx_comp.version,
                    license=spdx_comp.license_concluded if spdx_comp.license_concluded != "UNKNOWN" else None,
                    copyright=spdx_comp.copyright_text,
                )
                db.add(component)
                try:
                    db.flush()
                except IntegrityError:
                    # 并发创建了相同组件，重新查询
                    db.rollback()
                    component = db.query(Component).filter(
                        Component.name == spdx_comp.name,
                        Component.version == spdx_comp.version,
                    ).first()
                    if not component:
                        raise Exception("无法获取组件")

            # 创建合规记录
            record = ComplianceRecord(
                component_id=component.id,
                system_name=system_name,
                status=RecordStatus.DRAFT,
            )
            db.add(record)
            db.flush()

            # 创建法务声明（草稿）
            url_to_source = spdx_comp.download_location or ""
            license_info_url = spdx_comp.license_info_from_files or ""

            # 轻量级 URL 验证
            if url_to_source and not _is_valid_url(url_to_source):
                raise ValueError(f"无效的下载链接：{url_to_source}")
            if license_info_url and not _is_valid_url(license_info_url):
                raise ValueError(f"无效的许可证说明链接：{license_info_url}")

            declaration = LegalDeclaration(
                compliance_record_id=record.id,
                purpose_of_use="",  # 需要 R&D 手动填写
                url_to_source=url_to_source,
                license_info_url=license_info_url,
                license_text_url="",  # 需要手动填写
                license_name=spdx_comp.license_concluded or "UNKNOWN",
                is_modified=IsModified.NO,
                usage_type=UsageType.OTHER,  # 需要手动选择
                submitted_at=datetime.utcnow(),
            )
            db.add(declaration)
            db.flush()

            results.append(BulkImportItemResult(
                component_name=spdx_comp.name,
                component_version=spdx_comp.version,
                success=True,
                declaration_id=declaration.id,
            ))
            success_count += 1

        except Exception as e:
            logger.warning(f"导入组件 {spdx_comp.name}@{spdx_comp.version} 失败：{e}")
            results.append(BulkImportItemResult(
                component_name=spdx_comp.name,
                component_version=spdx_comp.version,
                success=False,
                error=str(e),
            ))
            failed_count += 1

    db.commit()

    logger.info(f"批量导入完成：成功 {success_count}, 失败 {failed_count}")
    return BulkImportResult(
        success_count=success_count,
        failed_count=failed_count,
        results=results,
    )


@router.get("/{declaration_id}/history-suggestions", response_model=HistorySuggestionResponse)
async def get_history_suggestions(
    declaration_id: int,
    db: Session = Depends(get_db),
):
    """获取历史复用建议

    查询同一组件在其他系统中的已批准声明。
    """
    declaration = db.query(LegalDeclaration).filter(
        LegalDeclaration.id == declaration_id
    ).first()
    if not declaration:
        raise HTTPException(status_code=404, detail="声明不存在")

    # 获取关联记录
    record = db.query(ComplianceRecord).filter(
        ComplianceRecord.id == declaration.compliance_record_id
    ).first()
    if not record:
        return HistorySuggestionResponse(has_history=False, suggestions=[])

    # 查询历史建议
    history_service = get_declaration_history_service(db)
    return history_service.get_history_suggestions(record.component_id)
