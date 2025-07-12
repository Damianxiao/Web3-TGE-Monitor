"""
API路由模块
提供API各个功能路由
"""
from . import projects, crawler, ai_processing, system, tge_search

__all__ = [
    'projects',
    'crawler', 
    'ai_processing',
    'system',
    'tge_search'
]