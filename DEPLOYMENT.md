# Compliance Hub - Docker 部署指南

## 前置要求

- Docker 20.10+
- Docker Compose v2+（`docker compose` 命令）
- 至少 1GB 可用磁盘空间
- 至少 512MB 可用内存

---

## 快速开始

### 1. 获取代码

```bash
git clone git@github.com:whoami001/copliant.git
cd copliant
```

### 2. 配置环境变量

```bash
cp .env.production.example .env
```

编辑 `.env` 文件，**必须修改**以下配置：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `DB_PASSWORD` | 数据库密码 | `MyS3cur3P@ssw0rd` |
| `SECRET_KEY` | JWT 签名密钥（至少32字符） | `openssl rand -hex 32` 生成 |

可选配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DB_USER` | 数据库用户名 | `compliance` |
| `DB_NAME` | 数据库名 | `compliance_hub` |
| `DB_PORT` | 数据库映射端口 | `5432` |
| `APP_PORT` | 应用映射端口 | `8000` |
| `BLACK_DUCK_URL` | Black Duck 地址 | 空 |
| `BLACK_DUCK_TOKEN` | Black Duck API Token | 空 |

### 3. 一键启动

```bash
chmod +x deploy.sh
./deploy.sh
```

或手动执行：

```bash
# 构建镜像
docker compose build

# 启动服务
docker compose up -d

# 执行数据库迁移
docker compose exec app alembic upgrade head
```

### 4. 验证部署

```bash
# 查看服务状态
docker compose ps

# 查看应用日志
docker compose logs -f app

# 健康检查
curl http://localhost:8000/health
```

访问：
- **前端页面**：http://localhost:8000/
- **API 文档**：http://localhost:8000/docs

---

## 常用操作

### 查看日志

```bash
# 所有服务
docker compose logs -f

# 仅应用日志
docker compose logs -f app

# 仅数据库日志
docker compose logs -f db
```

### 重启服务

```bash
docker compose restart app
```

### 停止服务

```bash
docker compose down
```

### 停止并删除数据（⚠️ 会丢失所有数据）

```bash
docker compose down -v
```

### 更新代码后重新部署

```bash
git pull
docker compose build --no-cache
docker compose up -d
docker compose exec app alembic upgrade head
```

### 进入容器调试

```bash
docker compose exec app bash
```

### 数据库备份

```bash
docker compose exec db pg_dump -U compliance compliance_hub > backup_$(date +%Y%m%d).sql
```

### 数据库恢复

```bash
docker compose exec -T db psql -U compliance compliance_hub < backup_20260409.sql
```

---

## 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 8000 | Compliance Hub | 前端 + API，可通过 `APP_PORT` 修改 |
| 5432 | PostgreSQL | 数据库，仅本地访问，可通过 `DB_PORT` 修改 |

---

## 故障排查

### 容器启动失败

```bash
# 查看完整日志
docker compose logs

# 重新构建并启动
docker compose down
docker compose build --no-cache
docker compose up -d
```

### 数据库连接失败

```bash
# 检查数据库是否就绪
docker compose exec db pg_isready -U compliance

# 查看数据库日志
docker compose logs db
```

### 迁移失败

```bash
# 查看当前迁移版本
docker compose exec app alembic current

# 回滚到上一版本
docker compose exec app alembic downgrade -1

# 重新执行
docker compose exec app alembic upgrade head
```

### 默认测试账户

登录代码为 `123456`，内置测试账户：

| 邮箱 | 角色 | 权限 |
|------|------|------|
| engineer@test.com | 工程师 | 创建声明、导入组件 |
| security@test.com | 安全评审 | 安全校验 |
| legal@test.com | 法务审批 | 法务审批 |
| admin@test.com | 管理员 | 全部权限 |

---

## 安全建议

1. **修改默认密钥** - `SECRET_KEY` 必须使用强随机字符串
2. **限制 CORS** - 生产环境应修改 `ALLOWED_HOSTS` 为具体域名
3. **启用 HTTPS** - 使用 Nginx 反向代理 + Let's Encrypt 证书
4. **数据库防火墙** - 限制数据库只允许应用容器访问
5. **定期备份** - 配置自动备份策略

---

## 生产环境部署（带 Nginx）

如需通过 Nginx 反向代理暴露服务：

```bash
sudo tee /etc/nginx/sites-available/compliance-hub > /dev/null <<'EOF'
server {
    listen 80;
    server_name compliance.yourcompany.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/compliance-hub/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/compliance-hub /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

Last updated: 2026-04-09
