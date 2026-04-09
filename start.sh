#!/bin/bash
# Compliance Hub 启动脚本

set -e

echo "======================================"
echo "  Compliance Hub - 启动脚本"
echo "======================================"

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本：$python_version"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -q -r requirements.txt

# 检查环境文件
if [ ! -f ".env" ]; then
    echo "创建环境配置..."
    cp .env.example .env
    echo "请编辑 .env 文件配置数据库连接"
fi

# 初始化数据库
echo "初始化数据库..."
alembic upgrade head

# 启动服务
echo ""
echo "======================================"
echo "  启动服务..."
echo "  API 文档：http://localhost:8000/docs"
echo "  前端页面：http://localhost:8000/"
echo "======================================"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
