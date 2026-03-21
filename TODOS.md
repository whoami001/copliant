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

*None yet*
