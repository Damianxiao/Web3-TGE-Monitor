"""
API数据模型模块
提供API请求响应数据模型
"""
from .requests import (
    # 枚举类型
    PlatformType,
    ProjectCategory,
    RiskLevel,
    TaskStatus,
    InvestmentRecommendation,
    
    # 基础模型
    PaginationParams,
    
    # 爬虫请求
    CrawlTaskRequest,
    CrawlTaskResponse,
    CrawlResultResponse,
    MultiPlatformCrawlRequest,
    MultiPlatformCrawlResponse,
    BatchCrawlStatusResponse,
    
    # AI处理请求
    AIProcessRequest,
    BatchAIProcessRequest,
    AIAnalysisResponse,
    
    # 项目查询请求
    ProjectSearchRequest,
    ProjectSummaryResponse,
    ProjectDetailResponse,
)

from .responses import (
    ApiResponse,
    ErrorResponse,
    PaginatedResponse,
    TaskResponse,
    BatchOperationResponse,
    HealthCheckResponse,
    SystemStatsResponse,
    
    # 工具函数
    success_response,
    error_response,
    paginated_response
)

__all__ = [
    # 枚举类型
    'PlatformType',
    'ProjectCategory',
    'RiskLevel',
    'TaskStatus',
    'InvestmentRecommendation',
    
    # 请求模型
    'PaginationParams',
    'CrawlTaskRequest',
    'MultiPlatformCrawlRequest',
    'AIProcessRequest',
    'BatchAIProcessRequest',
    'ProjectSearchRequest',
    
    # 响应模型
    'ApiResponse',
    'ErrorResponse',
    'PaginatedResponse',
    'TaskResponse',
    'BatchOperationResponse',
    'HealthCheckResponse',
    'CrawlTaskResponse',
    'CrawlResultResponse',
    'MultiPlatformCrawlResponse',
    'BatchCrawlStatusResponse',
    'AIAnalysisResponse',
    'ProjectSummaryResponse',
    'ProjectDetailResponse',
    'SystemStatsResponse',
    
    # 工具函数
    'success_response',
    'error_response',
    'paginated_response'
]