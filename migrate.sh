#!/bin/bash
# Compliance Hub 数据库迁移脚本

set -e

echo "======================================"
echo "  Compliance Hub - 数据库迁移"
echo "======================================"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 运行迁移
echo "运行数据库迁移..."
alembic upgrade head

echo "迁移完成!"
