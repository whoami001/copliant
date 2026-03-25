"""
添加 system_names 表到数据库
"""

from sqlalchemy import create_engine, inspect
from app.database import Base, engine
from app.models.system_name import SystemName

def add_system_names_table():
    """添加 system_names 表（如果不存在）"""

    # 检查表是否已存在
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "system_names" in existing_tables:
        print("✓ system_names 表已存在")
        return

    # 只创建 SystemName 表
    SystemName.__table__.create(bind=engine)
    print("✓ system_names 表创建成功")

if __name__ == "__main__":
    add_system_names_table()
