"""
日志配置模块
"""
import sys
import structlog
from pathlib import Path
from typing import Any

from ..config.settings import settings


def configure_logging() -> None:
    """配置结构化日志"""
    
    # 确保日志目录存在
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置日志处理器
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # 根据环境选择输出格式
    if settings.app_debug:
        # 开发环境：彩色输出到控制台
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # 生产环境：JSON格式
        processors.append(structlog.processors.JSONRenderer())
    
    # 配置structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> Any:
    """获取日志记录器"""
    return structlog.get_logger(name)


# 自动配置日志
configure_logging()