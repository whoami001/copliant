# TODOS

## Legal Declaration Features

### P3: 导出 PDF 功能
**Priority:** P3
**Status:** SKIPPED

**What:** 允许用户将法务声明导出为 PDF 文件

**Why:** 法务/安全团队可能需要离线存档或打印声明

**Cons:**
- 需要 PDF 生成库（如 jsPDF 或后端生成）
- 增加前端复杂度或后端负担

**Decision:** CEO review 决定跳过此功能，优先级低于其他核心功能。

---

## Completed

### 组件系统详情批量编辑功能
**Completed:** 2026-03-22

**What:** 在「组件导入」页面的「按系统分组」视图中，点击「操作」列的「查看详情」按钮后，打开批量编辑模态框（与上传 SPDX 文件后的预览界面相同）

**Why:** 研发人员可能未完成填写就保存了进度，需要从这里继续编辑未完成的草稿记录

**Implementation:**
- 前端：新增 `viewComponentSystemDetail()` 函数，从 API 加载系统下所有草稿状态的记录
- 数据流：将 `ComplianceRecord` 转换为批量编辑格式，包含 `declaration` 数据
- 编辑模式：通过 `window.isEditMode` 标记区分新建/编辑模式
- 提交逻辑：编辑模式下调用 `PUT /api/legal-declarations/{id}` 更新已有声明
- 只读回退：当系统下没有草稿记录时，显示 `viewComponentSystemDetailReadonly()` 只读弹窗

---

## Completed

### 历史复用提醒功能
**Completed:** 2026-03-22

**What:** 当研发填写法务声明时，系统自动提示"这个组件在 X 个系统中已获批"，并显示审批详情列表

**Why:** 避免同一组件在不同项目中重复审批，提高研发填写效率和信心

**Implementation:**
- 后端：`GET /api/legal-declarations/{declaration_id}/history-suggestions` 端点
- 服务：`DeclarationHistoryService.get_history_suggestions()` 查询同一组件（name+version）的已批准声明
- 前端：声明表单 Modal 中的 `history-reminder` 组件和 `loadHistorySuggestions()` 函数
- 数据库：Component 表已有 `uq_component_name_version` 复合约束支持快速查询

---

### 审批时间线显示（简化版）
**Completed:** 2026-03-22

**What:** 在法务声明查看模态框中显示审批时间线（安全审批时间、法务审批时间、各阶段审批人）

**Why:** 用户需要知道声明的审批历史，了解谁在什么时候审批了此声明

**Implementation:**
- 数据：ComplianceRecord 模型已有 `security_reviewed_at`, `reviewed_by_security`, `legal_approved_at`, `approved_by_legal` 字段
- 后端：`GET /api/compliance-records/{record_id}/declaration` 返回 `approval_timeline` 字段
- 前端：声明表单 Modal 中的 `decl-approval-timeline-container` 渲染时间线 UI

---

### SPDX 批量导入（完整版）
**Completed:** 2026-03-22

**What:** 研发上传 SPDX 文件，系统自动解析并批量创建法务声明草稿，自动填充 80% 字段

**Why:** 减少研发填写几百个组件的负担，从 SPDX 解析自动填充许可证、下载链接等字段

**Implementation:**
- 服务：`app/services/spdx_parser.py` — SPDX 解析服务（支持 JSON 和 tag-value 格式）
- 服务：`app/services/declaration_auto_filler.py` — 自动填充服务（SPDX 数据 + 历史记录 + AI 辅助）
- 后端：`POST /api/legal-declarations/bulk-import` — 批量导入端点
- 后端：`POST /api/legal-declarations/bulk-import/preview` — 预览端点（带预填充数据）
- 前端：SPDX 导入模态框，支持分页浏览、批量编辑、进度显示

---

### 组件全局审批（方案 A）
**Completed:** 2026-03-22

### 组件全局审批（方案 A）
**Completed:** 2026-03-22

**What:** 当任何项目的合规记录被法务审批通过后，自动标记组件为全局已审批（`Component.is_approved = true`）

**Why:** 避免同一组件在不同项目中重复审批，提高效率

**Implementation:**
- 修改 `app/routes/records.py` `approve_record()` 函数
- 法务审批通过时自动更新 `record.component.is_approved = True`

---

### Component 模型新增来源字段
**Completed:** 2026-03-22

**What:** 为 Component 模型添加 `source` 字段，标识组件来源（Black Duck 导入/手动创建/批量导入）

**Why:** 追踪组件数据来源，便于后续管理和审计

**Implementation:**
- 模型字段：`source = Column(String(50), default="blackduck", comment="组件来源：blackduck/manual/import")`
- 数据库迁移：`migrations/versions/005_add_source_field_to_component.py`

---
