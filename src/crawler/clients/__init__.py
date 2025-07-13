"""
微博客户端模块
提供不同的微博客户端实现
"""

from .weibo_client_interface import WeiboClientInterface
from .browser_weibo_client import BrowserWeiboClient

__all__ = [
    'WeiboClientInterface',
    'BrowserWeiboClient'
]