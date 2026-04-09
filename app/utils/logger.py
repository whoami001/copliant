"""日志工具"""

import logging
import sys
from typing import Optional

from pythonjsonlogger import jsonlogger

from app.config import get_settings

settings = get_settings()


def setup_logger(name: str = "compliance_hub") -> logging.Logger:
    """设置日志"""

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)

    if settings.log_format == "json":
        # 生产环境：JSON 格式
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    else:
        # 开发环境：文本格式
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# 默认 logger
logger = setup_logger()


def get_logger(name: str) -> logging.Logger:
    """获取命名 logger"""
    return setup_logger(name)
