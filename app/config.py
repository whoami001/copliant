from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    app_name: str = "Compliance Hub"
    debug: bool = True
    api_prefix: str = "/api"

    # 数据库配置
    database_url: str = "postgresql://user:password@localhost:5432/compliance_hub"

    # JWT 配置
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 小时

    # Black Duck API 配置
    black_duck_url: str = ""
    black_duck_token: str = ""

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "text"  # text or json

    # CORS 配置
    allowed_hosts: str = "*"  # 生产环境改为具体域名，逗号分隔

    # 分页配置
    default_page_size: int = 20
    max_page_size: int = 100

    # 混合模式阈值
    black_duck_sync_max_components: int = 50  # >50 用异步

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
