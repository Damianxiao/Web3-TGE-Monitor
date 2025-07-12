"""
API依赖注入
提供公共的依赖和工具函数
"""
from typing import Optional
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.database import get_db_session
from ..config.settings import settings


def get_request_id(request: Request) -> Optional[str]:
    """获取请求ID"""
    return getattr(request.state, 'request_id', None)


async def get_db():
    """获取数据库会话"""
    async for session in get_db_session():
        yield session


def validate_api_access(request: Request) -> bool:
    """
    验证API访问权限
    目前为简单实现，可以扩展为JWT或其他认证方式
    """
    # 在开发模式下允许所有访问
    if settings.app_debug:
        return True
    
    # 这里可以添加实际的认证逻辑
    # 例如检查API Key、JWT Token等
    
    return True


def require_auth(request: Request = None) -> bool:
    """
    认证依赖
    在需要认证的端点上使用
    """
    if not validate_api_access(request):
        raise HTTPException(
            status_code=401,
            detail="无效的访问凭证"
        )
    return True