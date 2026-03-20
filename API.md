# API 使用文档

**版本**: 0.1.0
**基础 URL**: `http://localhost:8000/api`

---

## 认证

MVP 版本使用简化的 JWT 认证。

### 登录

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@company.com",
  "code": "123456"
}
```

响应:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 获取当前用户

```http
GET /api/auth/me
Authorization: Bearer <token>
```

---

## 组件管理

### 获取组件列表

```http
GET /api/components?skip=0&limit=20&search=lodash&license_risk=safe
```

查询参数:
- `skip` - 跳过数量（分页）
- `limit` - 每页数量（1-100）
- `search` - 按组件名搜索
- `license_risk` - 按风险等级过滤（safe/caution/warning/unknown）

响应:
```json
[
  {
    "id": 1,
    "name": "lodash",
    "version": "4.17.21",
    "license": "MIT",
    "copyright": "Copyright (c) JS Foundation",
    "usage_type": "direct",
    "license_risk_level": "safe",
    "is_approved": true,
    "created_at": "2026-03-20T10:00:00Z"
  }
]
```

### 导入 Black Duck 报告

```http
POST /api/components/blackduck
Content-Type: application/json

{
  "report_id": "report-123",
  "system_name": "order-system"
}
```

响应:
```json
[
  {
    "id": 1,
    "name": "lodash",
    "version": "4.17.21",
    "license": "MIT",
    "license_risk_level": "safe"
  }
]
```

### 组件匹配检查

```http
POST /api/components/match?name=lodash&version=4.17.21
```

响应 - 找到匹配:
```json
{
  "matched": true,
  "existing_component": {...},
  "message": "找到历史合规结论，可以一键复用"
}
```

响应 - 未找到:
```json
{
  "matched": false,
  "message": "首次发现此组件，请填写合规信息"
}
```

---

## 合规记录

### 获取记录列表

```http
GET /api/compliance-records?skip=0&limit=20&status=draft&system_name=order
```

查询参数:
- `status` - 按状态过滤
- `system_name` - 按系统名过滤

### 创建合规记录

```http
POST /api/compliance-records
Content-Type: application/json

{
  "component_id": 1,
  "system_name": "order-system",
  "comments": "用于订单数据处理"
}
```

### 提交审批

```http
POST /api/compliance-records/1/submit
```

### 审批通过

```http
POST /api/compliance-records/1/approve
Content-Type: application/json

{
  "comments": "审批通过"
}
```

### 审批驳回

```http
POST /api/compliance-records/1/reject
Content-Type: application/json

{
  "comments": "许可证信息不完整，请补充"
}
```

### 要求修改（法务用）

```http
POST /api/compliance-records/1/request-changes
Content-Type: application/json

{
  "comments": "需要补充版权声明"
}
```

---

## 审批历史

### 获取审批历史

```http
GET /api/approvals/1/history
```

响应:
```json
[
  {
    "id": 1,
    "record_id": 1,
    "action": "submit",
    "role": "engineer",
    "actor_name": "张三",
    "previous_status": "draft",
    "new_status": "pending_security",
    "comments": null,
    "created_at": "2026-03-20T10:00:00Z"
  },
  {
    "id": 2,
    "record_id": 1,
    "action": "approve",
    "role": "security",
    "actor_name": "李四",
    "previous_status": "pending_security",
    "new_status": "pending_legal",
    "comments": "安全检查通过",
    "created_at": "2026-03-20T11:00:00Z"
  }
]
```

---

## 仪表板

### 获取待办事项

```http
GET /api/dashboard/todo
```

响应:
```json
{
  "items": [
    {
      "id": 1,
      "record_name": "lodash@4.17.21",
      "system_name": "order-system",
      "status": "pending_legal",
      "requires_action": true
    }
  ],
  "total": 1
}
```

### 获取统计信息

```http
GET /api/dashboard/stats
```

响应:
```json
{
  "pending_my_action": 3,
  "approved_this_month": 23,
  "avg_processing_days": 2.3,
  "total_records": 150
}
```

---

## 状态码说明

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问（权限不足） |
| 404 | 资源不存在 |
| 409 | 冲突（如重复数据） |
| 500 | 服务器内部错误 |
| 502 | Black Duck API 错误 |

---

## 错误响应格式

```json
{
  "error": "Validation failed",
  "code": "VALIDATION_ERROR",
  "details": {...}
}
```

---

## cURL 示例

### 完整流程示例

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","code":"1234"}' | jq -r '.access_token')

# 2. 导入 Black Duck 报告
curl -X POST http://localhost:8000/api/components/blackduck \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"report_id":"test-123","system_name":"test-system"}'

# 3. 创建合规记录
RECORD_ID=$(curl -s -X POST http://localhost:8000/api/compliance-records \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"component_id":1,"system_name":"test-system"}' | jq -r '.id')

# 4. 提交审批
curl -X POST http://localhost:8000/api/compliance-records/$RECORD_ID/submit \
  -H "Authorization: Bearer $TOKEN"

# 5. 安全审批通过
curl -X POST http://localhost:8000/api/compliance-records/$RECORD_ID/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"comments":"安全校验通过"}'

# 6. 法务审批通过
curl -X POST http://localhost:8000/api/compliance-records/$RECORD_ID/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"comments":"法务审批通过"}'

# 7. 查看审批历史
curl http://localhost:8000/api/approvals/$RECORD_ID/history \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Python SDK 示例

```python
import httpx

BASE_URL = "http://localhost:8000/api"

# 登录
with httpx.Client() as client:
    resp = client.post(f"{BASE_URL}/auth/login", json={
        "email": "test@test.com",
        "code": "1234"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 获取组件列表
    resp = client.get(f"{BASE_URL}/components", headers=headers)
    components = resp.json()

    # 创建合规记录
    resp = client.post(f"{BASE_URL}/compliance-records", headers=headers, json={
        "component_id": components[0]["id"],
        "system_name": "my-system"
    })
    record = resp.json()

    # 提交审批
    resp = client.post(f"{BASE_URL}/compliance-records/{record['id']}/submit", headers=headers)

    print(f"记录已提交，状态：{record['status']}")
```

---

Last updated: 2026-03-20 - Added frontend authentication UI, comprehensive test coverage (196 tests)
