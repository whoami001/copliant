"""法务声明相关路由"""

from typing import List, Optional
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.legal_declaration import LegalDeclaration
from app.models.compliance_record import ComplianceRecord, RecordStatus
from app.models.component import Component
from app.models.user import User, UserRole
from app.schemas.legal_declaration import (
    LegalDeclarationCreate,
    LegalDeclarationUpdate,
    LegalDeclarationResponse,
    LegalDeclarationDetailResponse,
    LegalDeclarationSubmit,
    BulkImportResult,
    BulkImportItemResult,
    HistorySuggestionResponse,
    BulkAutofillResponse,
    BulkAutofillItem,
)
from app.services.spdx_parser import parse_spdx_file, SpdxParseError
from app.services.declaration_history import get_declaration_history_service
from app.services.declaration_auto_filler import get_auto_filler_service
from app.services.pdf_exporter import get_pdf_exporter
from app.core.permissions import get_current_user_from_token, require_role, can
from app.utils.logger import get_logger
from fastapi.responses import StreamingResponse

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
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """创建/提交法务声明

    仅允许 DRAFT 状态的合规记录创建声明。
    """
    # 检查权限：Engineer 和 Admin 可以创建声明
    if not can(current_user, "create_declaration"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "INSUFFICIENT_PERMISSION",
                "required_roles": ["engineer", "admin"],
                "message": "权限不足：只有研发和管理员可以创建法务声明"
            }
        )

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
    """通过合规记录 ID 获取声明（含关联信息和审批时间线）"""
    declaration = db.query(LegalDeclaration).filter(
        LegalDeclaration.compliance_record_id == record_id
    ).first()
    if not declaration:
        raise HTTPException(status_code=404, detail="声明不存在")

    # 获取关联信息
    record = db.query(ComplianceRecord).filter(ComplianceRecord.id == record_id).first()
    component = db.query(Component).filter(Component.id == record.component_id).first() if record else None

    # 构建审批时间线
    from app.schemas.legal_declaration import ApprovalTimelineEntry
    timeline = []

    # 安全审批阶段
    if record:
        if record.security_reviewed_at:
            # 获取安全审批人邮箱
            security_reviewer_email = None
            if record.reviewed_by_security:
                from app.models.user import User
                security_reviewer = db.query(User).filter(User.id == record.reviewed_by_security).first()
                security_reviewer_email = security_reviewer.email if security_reviewer else None

            timeline.append(ApprovalTimelineEntry(
                stage="security_review",
                stage_name="安全审批",
                approver_email=security_reviewer_email,
                approved_at=record.security_reviewed_at,
                status="approved"
            ))
        elif record.status in [RecordStatus.PENDING_SECURITY, RecordStatus.PENDING_LEGAL, RecordStatus.APPROVED]:
            timeline.append(ApprovalTimelineEntry(
                stage="security_review",
                stage_name="安全审批",
                approver_email=None,
                approved_at=None,
                status="pending"
            ))

        # 法务审批阶段
        if record.legal_approved_at:
            # 获取法务审批人邮箱
            legal_approver_email = None
            if record.approved_by_legal:
                from app.models.user import User
                legal_approver = db.query(User).filter(User.id == record.approved_by_legal).first()
                legal_approver_email = legal_approver.email if legal_approver else None

            timeline.append(ApprovalTimelineEntry(
                stage="legal_approve",
                stage_name="法务审批",
                approver_email=legal_approver_email,
                approved_at=record.legal_approved_at,
                status="approved"
            ))
        elif record.status in [RecordStatus.PENDING_LEGAL, RecordStatus.APPROVED]:
            timeline.append(ApprovalTimelineEntry(
                stage="legal_approve",
                stage_name="法务审批",
                approver_email=None,
                approved_at=None,
                status="pending"
            ))

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
        approval_timeline=timeline if timeline else None,
        current_status=record.status.value if record else None,
    )


@router.put("/{declaration_id}", response_model=LegalDeclarationResponse)
async def update_declaration(
    declaration_id: int,
    update_data: LegalDeclarationUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """更新法务声明

    仅允许 DRAFT 或 REJECTED 状态的合规记录更新声明。
    仅允许声明创建者（Engineer）和管理员更新。
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
    if record and record.status not in [RecordStatus.DRAFT, RecordStatus.REJECTED]:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态不能修改声明：{record.status.value}，仅 DRAFT 和 REJECTED 状态可修改"
        )

    # 检查权限：只有声明创建者（Engineer）和管理员可以更新
    if not can(current_user, "create_declaration"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "INSUFFICIENT_PERMISSION",
                "required_roles": ["engineer", "admin"],
                "message": "权限不足：只有研发和管理员可以更新法务声明"
            }
        )

    # 额外检查：工程师只能更新自己的声明
    # 注意：filled_by 为 None 时允许更新（批量导入场景），更新时会设置 filled_by
    if current_user.role == UserRole.ENGINEER and record.filled_by is not None and record.filled_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="权限不足：只能更新自己创建的声明"
        )

    # 如果 filled_by 为空，设置为当前用户（批量导入场景）
    if record.filled_by is None:
        record.filled_by = current_user.id

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
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """提交法务声明（进入审批流程）

    将合规记录从 DRAFT 状态转为 PENDING_SECURITY。

    使用事务确保原子性：如果提交失败，回滚所有更改。
    """
    try:
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

        # 检查权限：只有 Engineer 和 Admin 可以提交声明
        if not can(current_user, "submit_declaration"):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "INSUFFICIENT_PERMISSION",
                    "required_roles": ["engineer", "admin"],
                    "message": "权限不足：只有研发和管理员可以提交法务声明"
                }
            )

        if record.status not in [RecordStatus.DRAFT, RecordStatus.REJECTED]:
            raise HTTPException(
                status_code=400,
                detail=f"当前状态不能提交：{record.status.value}，仅 DRAFT 和 REJECTED 状态可提交"
            )

        # 更新记录状态
        record.status = RecordStatus.PENDING_SECURITY
        record.submitted_at = datetime.utcnow()

        # 如果 filled_by 为空，设置为当前用户（批量导入场景）
        if record.filled_by is None:
            record.filled_by = current_user.id

        db.commit()
        db.refresh(declaration)

        logger.info(f"提交法务声明：{declaration.id}, 记录状态：{record.status.value}")
        return declaration

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"提交法务声明失败：{e}")
        raise HTTPException(status_code=500, detail="提交失败，请稍后重试")


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_declarations(
    file: UploadFile = File(...),
    system_name: str = Query(..., description="系统名称"),
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """批量导入法务声明

    上传 SPDX 文件，解析并创建声明草稿。

    返回结果包含成功/失败数量及详细信息。
    """
    # 检查权限：只有 Engineer 和 Admin 可以批量导入
    if not can(current_user, "bulk_import"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "INSUFFICIENT_PERMISSION",
                "required_roles": ["engineer", "admin"],
                "message": "权限不足：只有研发和管理员可以批量导入法务声明"
            }
        )

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

            # 检查是否已存在相同组件和系统的合规记录（避免重复导入）
            existing_record = db.query(ComplianceRecord).filter(
                ComplianceRecord.component_id == component.id,
                ComplianceRecord.system_name == system_name,
            ).first()

            if existing_record:
                # 已存在，跳过
                logger.info(f"组件 {spdx_comp.name}@{spdx_comp.version} 在系统 {system_name} 中已存在合规记录，跳过导入")
                results.append(BulkImportItemResult(
                    component_name=spdx_comp.name,
                    component_version=spdx_comp.version,
                    success=True,
                    declaration_id=None,
                    skipped=True,
                    message="已存在合规记录",
                ))
                continue

            # 创建合规记录
            record = ComplianceRecord(
                component_id=component.id,
                system_name=system_name,
                status=RecordStatus.DRAFT,
            )
            db.add(record)
            db.flush()

            # 创建法务声明（草稿）
            # SPDX 文件中的 NOASSERTION 是合法值，表示无法确定下载位置，应视为空字符串
            url_to_source = spdx_comp.download_location or ""
            if url_to_source == "NOASSERTION":
                url_to_source = ""
            license_info_url = spdx_comp.license_info_from_files or ""
            if license_info_url == "NOASSERTION":
                license_info_url = ""

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
                is_modified="no",
                usage_type="other",  # 需要手动选择
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
            # 回滚当前事务，继续处理下一个组件
            db.rollback()

    db.commit()

    logger.info(f"批量导入完成：成功 {success_count}, 失败 {failed_count}")
    return BulkImportResult(
        success_count=success_count,
        failed_count=failed_count,
        results=results,
    )


@router.post("/bulk-import/preview", response_model=BulkAutofillResponse)
async def preview_bulk_import_with_autofill(
    file: UploadFile,
    system_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """批量导入预览（带智能预填充）

    1. 解析 SPDX 文件
    2. 为每个组件自动填充字段（从 SPDX 数据 + 历史记录）
    3. 返回预览数据，供前端批量编辑

    仅 ENGINEER 和 ADMIN 角色可以使用。
    """
    # 权限检查
    if not can(current_user, "bulk_import"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "INSUFFICIENT_PERMISSION",
                "required_roles": ["engineer", "admin"],
                "message": "权限不足：只有研发和管理员可以批量导入法务声明"
            }
        )

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

    # 获取自动填充服务
    auto_filler = get_auto_filler_service(db)

    # 批量获取预填充数据
    spdx_data = [
        {
            "name": comp.name,
            "version": comp.version,
            "license_concluded": comp.license_concluded,
            "download_location": comp.download_location,
            "license_info_from_files": comp.license_info_from_files,
        }
        for comp in components
    ]

    autofill_items = auto_filler.get_batch_autofill(spdx_data, system_name)

    # 转换为响应格式
    items = [
        BulkAutofillItem(
            component_name=item["component_name"],
            component_version=item["component_version"],
            license_name=item.get("license_name", ""),
            url_to_source=item.get("url_to_source", ""),
            license_info_url=item.get("license_info_url", ""),
            license_text_url=item.get("license_text_url", ""),
            is_modified=item.get("is_modified", "no"),
            usage_type=item.get("usage_type", ""),
            purpose_of_use=item.get("purpose_of_use", ""),
            purpose_of_use_suggestion=item.get("purpose_of_use_suggestion", ""),
            source=item.get("source", "spdx"),
        )
        for item in autofill_items
    ]

    return BulkAutofillResponse(items=items)


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
    return history_service.get_history_suggestions(record.component_id, current_record_id=record.id)


@router.get("/{declaration_id}/export-pdf")
async def export_declaration_pdf(
    declaration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """导出法务声明为 PDF

    仅允许有权限查看声明的用户导出（声明创建者、安全、法务、管理员）。
    """
    # 获取声明
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
        raise HTTPException(status_code=404, detail="关联的合规记录不存在")

    # 获取组件信息
    component = db.query(Component).filter(
        Component.id == record.component_id
    ).first()
    if not component:
        raise HTTPException(status_code=404, detail="关联的组件不存在")

    # 权限检查：只有相关角色可以导出
    allowed_roles = [UserRole.ENGINEER, UserRole.SECURITY, UserRole.LEGAL, UserRole.ADMIN]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "INSUFFICIENT_PERMISSION",
                "required_roles": ["engineer", "security", "legal", "admin"],
                "message": "权限不足：无法导出法务声明"
            }
        )

    # 工程师只能导出自己的声明
    if current_user.role == UserRole.ENGINEER:
        if record.filled_by != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="权限不足：只能导出自己创建的声明"
            )

    # 构建审批时间线
    approval_timeline = []

    # 安全审批阶段
    if record.security_reviewed_at:
        security_reviewer_email = None
        if record.reviewed_by_security:
            security_reviewer = db.query(User).filter(User.id == record.reviewed_by_security).first()
            security_reviewer_email = security_reviewer.email if security_reviewer else None

        approval_timeline.append({
            "stage_name": "安全审批",
            "approver_email": security_reviewer_email,
            "approved_at": record.security_reviewed_at,
            "status": "approved"
        })
    elif record.status in [RecordStatus.PENDING_SECURITY, RecordStatus.PENDING_LEGAL, RecordStatus.APPROVED]:
        approval_timeline.append({
            "stage_name": "安全审批",
            "approver_email": None,
            "approved_at": None,
            "status": "pending"
        })

    # 法务审批阶段
    if record.legal_approved_at:
        legal_approver_email = None
        if record.approved_by_legal:
            legal_approver = db.query(User).filter(User.id == record.approved_by_legal).first()
            legal_approver_email = legal_approver.email if legal_approver else None

        approval_timeline.append({
            "stage_name": "法务审批",
            "approver_email": legal_approver_email,
            "approved_at": record.legal_approved_at,
            "status": "approved"
        })
    elif record.status in [RecordStatus.PENDING_LEGAL, RecordStatus.APPROVED]:
        approval_timeline.append({
            "stage_name": "法务审批",
            "approver_email": None,
            "approved_at": None,
            "status": "pending"
        })

    # 生成 PDF
    exporter = get_pdf_exporter()
    declaration_data = {
        "purpose_of_use": declaration.purpose_of_use,
        "url_to_source": declaration.url_to_source,
        "license_info_url": declaration.license_info_url,
        "license_text_url": declaration.license_text_url,
        "license_name": declaration.license_name,
        "is_modified": declaration.is_modified,
        "usage_type": declaration.usage_type,
    }

    try:
        pdf_data = exporter.generate_pdf(
            declaration_data=declaration_data,
            component_name=component.name,
            component_version=component.version,
            system_name=record.system_name,
            approval_timeline=approval_timeline
        )

    except Exception as e:
        logger.error(f"生成 PDF 失败：{e}")
        raise HTTPException(status_code=500, detail=f"PDF 生成失败：{str(e)}")

    # 返回 PDF 文件
    # 使用 RFC 5987 编码处理中文文件名 (HTTP header 只支持 latin-1)
    from urllib.parse import quote
    filename_ascii = f"{component.name.replace('/', '-').replace(' ', '_')}-{component.version}-declaration.pdf"
    filename_utf8 = quote(f"{component.name.replace('/', '-')}-{component.version}-法务声明.pdf")

    return StreamingResponse(
        BytesIO(pdf_data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename_ascii}\"; filename*=UTF-8''{filename_utf8}"
        }
    )
