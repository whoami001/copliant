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

### 站内通知中心
**Completed:** 2026-03-23

**What:** 研发人员可以通过站内通知中心收到安全/法务驳回、拒绝或催促的留言通知

**Why:**
- 之前安全和法务在审批时填写的留言，研发人员无法主动获知
- 需要登录 Dashboard 查看待办列表或点击"查看详情"才能看到留言
- 缺少主动通知机制

**Implementation:**
- 模型：新增 `Notification` 模型，支持 4 种通知类型（security_rejected、legal_rejected、legal_denied、urgency_added）
- 服务：`NotificationService` 提供创建通知、获取列表、标记已读等功能
- API：新增 `/api/notifications` 相关端点（列表、未读数、标记已读）
- 路由：records.py 在 reject 和 request_changes 时自动发送通知给研发人员
- 前端：新增"消息中心"页面，支持全部/未读标签切换、未读数角标显示
- 数据库迁移：`migrations/versions/008_create_notifications_table.py`

---

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

## Design Debt (from Design Plan Review 2026-03-23)

### DESIGN.md — 设计系统文档
**Priority:** P2
**Status:** PROPOSED

**What:** 创建正式的设计系统文档 (DESIGN.md)，包含视觉识别、组件库、交互模式

**Why:**
- 当前没有 DESIGN.md，设计决策散落在代码中
- 缺乏统一的设计语言导致 AI Slop 风险
- 新组件开发缺乏设计依据

**Pros:**
- 统一设计语言，提升产品专业感
- 减少设计决策重复讨论
- 便于前端组件化开发

**Cons:**
- 需要投入时间创建和维护文档
- 可能限制开发灵活性

**Context:** 2026-03-23 设计审查评分 5/10 的主要原因。计划通过 /design-consultation skill 创建。

**Depends on:** /design-consultation skill 执行

---

### 空状态设计优化
**Priority:** P2
**Status:** PROPOSED

**What:** 优化所有表格空状态，包含：图标、温暖文案、上下文说明、主要操作按钮

**Why:**
- 当前空状态仅显示"暂无记录"，缺乏引导
- 用户看到空状态时不知道下一步该做什么
- 与 Todo 空状态的优质设计不一致

**Pros:**
- 提升用户体验，减少困惑
- 增加功能发现性（通过空状态中的操作按钮）
- 统一设计语言

**Cons:**
- 需要为每个空状态设计合适的文案和操作
- 增加前端代码量

**Context:** 2026-03-23 设计审查发现。Todo 空状态是优质范例（"太棒了！所有合规记录都已处理完成" + 创建按钮）。

**Depends on:** 无

---

### 键盘无障碍导航
**Priority:** P1
**Status:** PROPOSED

**What:** 为所有模态框添加 ESC 键关闭 handlers 和焦点陷阱 (focus trap)

**Why:**
- CLAUDE.md 声称支持但实际未实现
- 键盘用户无法有效使用模态框
- 无障碍合规性缺失

**Pros:**
- 满足无障碍访问要求
- 提升键盘用户效率
- 修复文档与实际不符的问题

**Cons:**
- 需要为每个模态框添加事件监听
- 焦点陷阱实现有一定复杂度

**Context:** 2026-03-23 设计审查 Pass 6 发现。模态框包括：login, permission-denied, component-system-detail 等。

**Depends on:** 无

---

### 用户旅程地图
**Priority:** P2
**Status:** PROPOSED

**What:** 为三种用户角色（工程师、安全评审、法务审批）创建用户旅程地图，包含情感弧线和支撑点

**Why:**
- 当前没有用户旅程文档
- 不了解用户在各阶段的情感状态
- 错过提供支持的机会

**Pros:**
- 更好地理解用户需求
- 发现产品改进机会
- 增强团队同理心

**Cons:**
- 需要用户研究和访谈投入
- 文档维护成本

**Context:** 2026-03-23 设计审查 Pass 4 评分 3/10 的主要原因。

**Depends on:** 无

---

### 移动端导航优化
**Priority:** P3
**Status:** PROPOSED

**What:** 定义移动端导航模式 — 当前侧边栏在移动端变为顶栏，考虑汉堡菜单或底部导航

**Why:**
- 当前移动端导航体验一般
- 侧边栏内容在小屏幕上拥挤
- 缺乏明确的移动端交互模式

**Pros:**
- 提升移动端用户体验
- 更符合移动用户习惯
- 增加屏幕利用率

**Cons:**
- 需要重新设计移动端布局
- 可能增加前端复杂度

**Context:** 2026-03-23 设计审查 Pass 7 发现。当前响应式断点：768px, 480px。

**Depends on:** 无

---

### WCAG 色彩对比度验证
**Priority:** P2
**Status:** PROPOSED

**What:** 验证所有色彩对比度符合 WCAG AA 标准，并记录合规级别

**Why:**
- 当前未经验证色彩可访问性
- 可能存在可读性问题
- 企业产品需要满足无障碍标准

**Pros:**
- 满足无障碍法规要求
- 提升可读性，减少视觉疲劳
- 扩大用户适用范围

**Cons:**
- 可能需要调整现有配色
- 需要工具验证和人工检查

**Context:** 2026-03-23 设计审查 Pass 7 发现。当前使用 CSS 变量定义颜色。

**Depends on:** 无

---

### 错误状态规范
**Priority:** P2
**Status:** PROPOSED

**What:** 规范所有用户操作的错误状态（表单验证、网络错误、403/500 响应）

**Why:**
- 当前错误状态未系统定义
- 用户体验不一致
- 可能遗漏重要错误场景

**Pros:**
- 一致的用户体验
- 减少用户困惑
- 降低客服压力

**Cons:**
- 需要覆盖大量错误场景
- 增加错误处理代码

**Context:** 2026-03-23 设计审查 Pass 7 发现。当前仅有 toast 通知和 403 模态框。

**Depends on:** 无

---

### WCAG 警告颜色对比度修复
**Priority:** P2
**Status:** DEFERRED

**What:** 将警告颜色从 #D97706 改为 #B45309 (amber-700) 以满足 WCAG AA 对比度要求

**Why:** 当前警告颜色对比度 2.76:1，低于 WCAG AA 要求的 3:1 最小值

**Pros:**
- 满足无障碍法规要求
- 色弱用户更容易识别警告状态
- 提升产品专业性

**Cons:**
- 颜色稍深，视觉冲击力略强
- 需要全局替换颜色值

**Context:** 2026-03-23 设计审查 Pass 6 发现。用户选择暂时保持原色，但建议后续修复。

**Depends on:** 无

---

### 用户旅程地图
**Priority:** P2
**Status:** DEFERRED (from CEO Review cherry-pick)

**What:** 为三种用户角色（工程师、安全评审、法务审批）创建用户旅程地图，包含情感弧线和支撑点

**Why:**
- 当前没有用户旅程文档
- 不了解用户在各阶段的情感状态
- 错过提供支持的机会

**Pros:**
- 更好地理解用户需求
- 发现产品改进机会
- 增强团队同理心

**Cons:**
- 需要用户研究和访谈投入
- 文档维护成本

**Context:** 2026-03-23 CEO Review 决定接受此任务。设计审查 Pass 3 评分 4/10 的主要原因。

**Depends on:** 无

---

### DESIGN.md — 设计系统文档
**Priority:** P2
**Status:** DEFERRED

**What:** 创建正式的设计系统文档 (DESIGN.md)，包含视觉识别、组件库、交互模式

**Why:**
- 当前没有 DESIGN.md，设计决策散落在代码中
- 缺乏统一的设计语言导致 AI Slop 风险
- 新组件开发缺乏设计依据

**Pros:**
- 统一设计语言，提升产品专业感
- 减少设计决策重复讨论
- 便于前端组件化开发

**Cons:**
- 需要投入时间创建和维护文档
- 可能限制开发灵活性

**Context:** 2026-03-23 设计审查 Pass 5 评分 3/10 的主要原因。用户选择"function over form"，暂时跳过。

**Depends on:** 无

---

## Test Debt (from Engineering Review 2026-03-23)

### P0: 更新测试以适配虚拟用户移除
**Priority:** P0
**Status:** PROPOSED

**What:** 更新所有集成测试，使其创建真实用户并发送有效的 JWT token，而不是依赖虚拟用户 fallback

**Why:** 安全修复移除了 `permissions.py` 中的虚拟用户 fallback（允许伪造 JWT 获取任意角色），导致 47 个测试失败

**Pros:**
- 测试反映真实安全行为
- 防止未来认证回归
- 验证权限系统正常工作

**Cons:**
- 需要为每个测试添加 auth 头部
- 测试代码量增加约 20%

**Context:** 2026-03-23 工程审查发现。安全修复后，test_api.py、test_legal_declarations.py、test_records.py、test_components.py、test_dashboard.py 中的 47 个测试返回 401。需要添加 `auth_headers` fixture 到所有需要认证的测试。

**Effort:** M (human: ~2 hrs / CC: ~20 min)

**Depends on:** 无

---
