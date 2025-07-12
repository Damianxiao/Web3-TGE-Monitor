"""
API响应模型
定义统一的API响应格式
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Union, TypeVar, Generic
from datetime import datetime

# 泛型类型定义
T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """通用API响应模型"""
    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})
    
    success: bool = Field(True, description="请求是否成功")
    message: str = Field("成功", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间")
    request_id: Optional[str] = Field(None, description="请求ID")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: bool = Field(True, description="是否为错误")
    message: str = Field(..., description="错误消息")
    status_code: int = Field(..., description="HTTP状态码")
    path: str = Field(..., description="请求路径")
    details: Optional[List[Dict[str, Any]]] = Field(None, description="详细错误信息")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="错误时间")
    request_id: Optional[str] = Field(None, description="请求ID")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    items: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页数量")
    pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        size: int
    ) -> 'PaginatedResponse[T]':
        """创建分页响应"""
        import math
        pages = math.ceil(total / size) if total > 0 else 0
        
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class TaskResponse(BaseModel):
    """任务响应基类"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    message: Optional[str] = Field(None, description="任务消息")


class BatchOperationResponse(BaseModel):
    """批量操作响应模型"""
    total_items: int = Field(..., description="总处理项数")
    successful: int = Field(..., description="成功处理数")
    failed: int = Field(..., description="失败处理数")
    skipped: int = Field(0, description="跳过处理数")
    processing_time: float = Field(..., description="处理时间（秒）")
    errors: Optional[List[str]] = Field(None, description="错误信息列表")


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="健康状态")
    timestamp: float = Field(..., description="检查时间戳")
    services: Dict[str, str] = Field(..., description="各服务状态")
    version: str = Field(..., description="API版本")
    uptime: Optional[float] = Field(None, description="运行时间")


class SystemStatsResponse(BaseModel):
    """系统统计响应模型"""
    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})
    
    total_projects: int = Field(..., description="总项目数")
    processed_projects: int = Field(..., description="已处理项目数")
    unprocessed_projects: int = Field(..., description="未处理项目数")
    platform_stats: Dict[str, int] = Field(..., description="平台统计")
    category_stats: Dict[str, int] = Field(..., description="分类统计")
    recent_24h: int = Field(..., description="24小时内项目数")
    recent_7d: int = Field(..., description="7天内项目数")
    api_version: str = Field(..., description="API版本")
    uptime: float = Field(..., description="运行时间")
    last_updated: datetime = Field(..., description="最后更新时间")


# 便捷函数
def success_response(
    data: T = None, 
    message: str = "成功",
    request_id: Optional[str] = None
) -> ApiResponse[T]:
    """创建成功响应"""
    return ApiResponse(
        success=True,
        message=message,
        data=data,
        request_id=request_id
    )


def error_response(
    message: str,
    status_code: int = 400,
    path: str = "",
    details: Optional[List[Dict[str, Any]]] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """创建错误响应"""
    return ErrorResponse(
        error=True,
        message=message,
        status_code=status_code,
        path=path,
        details=details,
        request_id=request_id
    )


def paginated_response(
    items: List[T],
    total: int,
    page: int,
    size: int
) -> PaginatedResponse[T]:
    """创建分页响应"""
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        size=size
    )