"""
错误处理中间件
统一处理应用中的异常和错误
"""
import traceback
import json
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from ..models.responses import ErrorResponse
from ...config.settings import settings

logger = structlog.get_logger()


# 自定义JSON编码器处理datetime
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    错误处理中间件
    捕获和处理应用中的未处理异常
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            return await self._handle_exception(request, e)
    
    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """
        处理异常并返回统一格式的错误响应
        """
        # 获取请求ID（如果有）
        request_id = getattr(request.state, 'request_id', None)
        
        # 错误类型和消息
        error_type = type(exc).__name__
        error_message = str(exc)
        
        # 记录详细错误信息
        logger.error(
            "Unhandled exception in middleware",
            request_id=request_id,
            error_type=error_type,
            error_message=error_message,
            path=request.url.path,
            method=request.method,
            traceback=traceback.format_exc() if settings.app_debug else None
        )
        
        # 根据异常类型返回不同的错误响应
        if isinstance(exc, ValueError):
            return self._create_error_response(
                message=f"参数错误: {error_message}",
                status_code=400,
                request=request,
                request_id=request_id
            )
        
        elif isinstance(exc, PermissionError):
            return self._create_error_response(
                message="没有权限访问该资源",
                status_code=403,
                request=request,
                request_id=request_id
            )
        
        elif isinstance(exc, FileNotFoundError):
            return self._create_error_response(
                message="请求的资源不存在",
                status_code=404,
                request=request,
                request_id=request_id
            )
        
        elif isinstance(exc, TimeoutError):
            return self._create_error_response(
                message="请求超时，请稍后重试",
                status_code=408,
                request=request,
                request_id=request_id
            )
        
        # 数据库相关错误
        elif 'database' in error_type.lower() or 'connection' in error_message.lower():
            return self._create_error_response(
                message="数据库连接错误，请稍后重试",
                status_code=503,
                request=request,
                request_id=request_id
            )
        
        # AI服务相关错误
        elif 'ai' in error_type.lower() or 'openai' in error_message.lower():
            return self._create_error_response(
                message="AI服务暂时不可用，请稍后重试",
                status_code=503,
                request=request,
                request_id=request_id
            )
        
        # 网络相关错误
        elif 'network' in error_message.lower() or 'connection' in error_message.lower():
            return self._create_error_response(
                message="网络连接错误，请检查网络设置",
                status_code=502,
                request=request,
                request_id=request_id
            )
        
        # 默认内部服务器错误
        else:
            # 在开发模式下返回详细错误信息
            message = (
                f"内部服务器错误: {error_message}" 
                if settings.app_debug 
                else "内部服务器错误，请联系管理员"
            )
            
            details = None
            if settings.app_debug:
                details = [{
                    "error_type": error_type,
                    "error_message": error_message,
                    "traceback": traceback.format_exc().split('\n')[-10:]  # 只显示最后10行
                }]
            
            return self._create_error_response(
                message=message,
                status_code=500,
                request=request,
                request_id=request_id,
                details=details
            )
    
    def _create_error_response(
        self, 
        message: str, 
        status_code: int, 
        request: Request,
        request_id: str = None,
        details: list = None
    ) -> JSONResponse:
        """
        创建统一格式的错误响应
        """
        error_response = ErrorResponse(
            error=True,
            message=message,
            status_code=status_code,
            path=str(request.url),
            request_id=request_id,
            details=details
        )
        
        return JSONResponse(
            status_code=status_code,
            content=json.loads(json.dumps(error_response.dict(exclude_none=True), cls=CustomJSONEncoder))
        )


def add_error_handlers(app):
    """添加错误处理中间件到FastAPI应用"""
    app.add_middleware(ErrorHandlerMiddleware)