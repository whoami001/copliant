# 部署文档

## 环境要求

- Docker & Docker Compose（推荐）
- 或 Python 3.11+ & PostgreSQL 14+

---

## 方式一：Docker Compose 部署（推荐）

### 1. 准备环境

```bash
cd compliance-hub
cp .env.production.example .env
# 编辑 .env 配置生产环境变量
```

### 2. 启动服务

```bash
docker-compose up -d
```

### 3. 初始化数据库

```bash
docker-compose exec app alembic upgrade head
```

### 4. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 健康检查
curl http://localhost:8000/health
```

### 5. 停止服务

```bash
docker-compose down
# 如需删除数据卷（谨慎）
docker-compose down -v
```

---

## 方式二：手动部署

### 1. 准备 PostgreSQL

```bash
# 创建数据库和用户
psql -U postgres << EOF
CREATE DATABASE compliance_hub;
CREATE USER compliance WITH PASSWORD 'CHANGE_ME';
GRANT ALL PRIVILEGES ON DATABASE compliance_hub TO compliance;
EOF
```

### 2. 安装应用

```bash
# 创建虚拟环境
python3 -m venv /opt/compliance-hub/venv
source /opt/compliance-hub/venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制代码
cp -r . /opt/compliance-hub/app

# 配置环境
cp .env.production.example /opt/compliance-hub/.env
# 编辑 .env
```

### 3. 初始化数据库

```bash
cd /opt/compliance-hub
alembic upgrade head
```

### 4. 配置 systemd 服务

```bash
sudo tee /etc/systemd/system/compliance-hub.service > /dev/null <<'EOF'
[Unit]
Description=Compliance Hub API
After=network.target postgresql.service

[Service]
Type=notify
User=compliance
Group=compliance
WorkingDirectory=/opt/compliance-hub
Environment="PATH=/opt/compliance-hub/venv/bin"
ExecStart=/opt/compliance-hub/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable compliance-hub
sudo systemctl start compliance-hub
```

### 5. 配置 Nginx 反向代理

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

## 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health

# 预期响应
{"status":"healthy","version":"0.1.0"}
```

---

## 日志查看

### Docker 部署

```bash
# 查看应用日志
docker-compose logs -f app

# 查看数据库日志
docker-compose logs -f db
```

### 手动部署

```bash
# 使用 journalctl
sudo journalctl -u compliance-hub -f

# 或查看日志文件（如果配置了文件日志）
tail -f /var/log/compliance-hub/app.log
```

---

## 备份与恢复

### 数据库备份

```bash
# 备份
pg_dump -U compliance compliance_hub > backup-$(date +%Y%m%d).sql

# 恢复
psql -U compliance compliance_hub < backup-20260320.sql
```

### Docker 数据卷备份

```bash
docker run --rm \
  -v compliance-hub_postgres_data:/data:ro \
  -v $(pwd):/backup alpine \
  tar czf /backup/postgres-backup-$(date +%Y%m%d).tar.gz /data
```

---

## 故障排查

### 常见问题

**1. 数据库连接失败**

```bash
# 检查数据库是否运行
docker-compose ps db

# 检查连接字符串
docker-compose exec app env | grep DATABASE_URL

# 测试数据库连接
docker-compose exec app python -c "from app.database import engine; print(engine.connect())"
```

**2. 迁移失败**

```bash
# 查看当前迁移状态
docker-compose exec app alembic current

# 回滚到上一个版本
docker-compose exec app alembic downgrade -1

# 重新应用
docker-compose exec app alembic upgrade head
```

**3. 应用无法启动**

```bash
# 查看详细日志
docker-compose logs app

# 检查端口占用
netstat -tlnp | grep 8000

# 重启服务
docker-compose restart app
```

---

## 安全建议

1. **修改默认密钥** - `SECRET_KEY` 必须使用强随机字符串
2. **限制 CORS** - 生产环境应限制允许的来源
3. **启用 HTTPS** - 使用 Let's Encrypt 或其他证书
4. **数据库防火墙** - 限制数据库只允许应用访问
5. **定期备份** - 配置自动备份策略
6. **日志审计** - 保留审计日志至少 6 个月

---

## 监控建议

1. **应用监控** - Prometheus + Grafana
2. **日志聚合** - ELK Stack 或 Loki
3. **告警** - PagerDuty 或钉钉/企业微信
4. **数据库监控** - pg_stat_statements

---

Last updated: 2026-03-20 - Frontend now includes authentication UI with role-based access
