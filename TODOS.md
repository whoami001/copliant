# TODOS

## Legal Declaration Features

### P2: 审批时间线显示
**Priority:** P2

**What:** 在法务声明查看模态框中显示审批时间线（安全审批时间、法务审批时间、各阶段审批人）

**Why:** 用户需要知道声明的审批历史，了解谁在什么时候审批了此声明

**Pros:**
- 提高审批流程透明度
- 方便追溯审批责任
- 用户更有信心

**Cons:**
- 需要后端 API 支持（返回审批历史）
- 前端需要额外的 UI 空间

**Context:** 从 CEO review  deferred。当前声明查看模态框只显示声明内容，不显示审批流程信息。

**Depends on:** 后端需要添加审批历史 API 或扩展现有 API 返回审批时间线数据

---

### P3: 导出 PDF 功能
**Priority:** P3

**What:** 允许用户将法务声明导出为 PDF 文件

**Why:** 法务/安全团队可能需要离线存档或打印声明

**Pros:**
- 方便存档
- 支持离线审查
- 符合某些企业的合规要求

**Cons:**
- 需要 PDF 生成库（如 jsPDF 或后端生成）
- 增加前端复杂度或后端负担

**Context:** 从 CEO review deferred。当前只有网页查看，无导出功能。

**Depends on:** 选择合适的 PDF 生成方案（前端 vs 后端）

---

## Completed

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
