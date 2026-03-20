"""数据库会话管理"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_settings

settings = get_settings()

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # 连接健康检查
    pool_size=10,
    max_overflow=20,
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()


def get_db() -> Session:
    """获取数据库会话（依赖注入用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
