"""
,k!W�
���(s�
"""
from .platform_factory import PlatformFactory, auto_register_platforms
from .crawler_manager import crawler_manager
from .models import Platform, RawContent, CrawlTask, CrawlResult

# ��s�
auto_register_platforms()

__all__ = [
    'PlatformFactory',
    'crawler_manager',
    'Platform',
    'RawContent',
    'CrawlTask', 
    'CrawlResult'
]