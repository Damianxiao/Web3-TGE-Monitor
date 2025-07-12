"""
API路由模块
提供API各个功能路由
"""
from . import projects, crawler, ai_processing, system

__all__ = [
    'projects',
    'crawler', 
    'ai_processing',
    'system'
]