"""
多平台爬虫模块
"""
from crawler.platform_factory import PlatformFactory, auto_register_platforms
from crawler.crawler_manager import crawler_manager
from crawler.models import Platform, RawContent, CrawlTask, CrawlResult

# 自动注册平台
auto_register_platforms()

__all__ = [
    'PlatformFactory',
    'crawler_manager',
    'Platform',
    'RawContent',
    'CrawlTask', 
    'CrawlResult'
]