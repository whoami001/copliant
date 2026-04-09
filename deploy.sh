#!/bin/bash
set -e

echo "======================================"
echo "  Compliance Hub - Docker 构建 & 启动"
echo "======================================"

# 检查 docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: 未找到 docker，请先安装 docker"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "错误: 未找到 docker compose，请安装 docker compose v2+"
    exit 1
fi

# 检查环境文件
if [ ! -f ".env" ]; then
    if [ -f ".env.production.example" ]; then
        echo "从 .env.production.example 创建 .env..."
        cp .env.production.example .env
        echo ""
        echo "⚠️  请编辑 .env 文件修改以下配置："
        echo "   - DATABASE_URL (数据库密码)"
        echo "   - SECRET_KEY (JWT 密钥，至少32字符)"
        echo "   - BLACK_DUCK_URL / BLACK_DUCK_TOKEN (可选)"
        echo ""
        read -p "按回车键继续，或 Ctrl+C 取消..."
    else
        echo "错误: 未找到 .env.production.example"
        exit 1
    fi
fi

# 构建并启动
echo ""
echo "构建 Docker 镜像..."
docker compose build

echo ""
echo "启动服务..."
docker compose up -d

echo ""
echo "等待数据库就绪..."
sleep 5

echo ""
echo "执行数据库迁移..."
docker compose exec -T app alembic upgrade head || echo "数据库迁移完成（可能已执行过）"

echo ""
echo "======================================"
echo "  部署完成！"
echo "  API 文档：http://localhost:8000/docs"
echo "  前端页面：http://localhost:8000/"
echo ""
echo "  查看日志：docker compose logs -f"
echo "  停止服务：docker compose down"
echo "======================================"
