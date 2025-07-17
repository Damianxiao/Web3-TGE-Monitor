"""
API数据模型
定义所有API端点的请求和响应模型
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


# 基础枚举类
class PlatformType(str, Enum):
    """支持的平台类型"""
    XHS = "xhs"
    DOUYIN = "douyin"
    WEIBO = "weibo"
    BILIBILI = "bilibili"
    ZHIHU = "zhihu"
    KUAISHOU = "kuaishou"
    TIEBA = "tieba"


class ProjectCategory(str, Enum):
    """项目分类"""
    DEFI = "DeFi"
    GAMEFI = "GameFi"
    NFT = "NFT"
    LAYER2 = "Layer2"
    DAO = "DAO"
    OTHER = "Other"


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InvestmentRecommendation(str, Enum):
    """投资建议"""
    WATCH = "关注"
    CAUTION = "谨慎"
    AVOID = "避免"


# 通用模型
class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码，从1开始")
    size: int = Field(20, ge=1, le=100, description="每页数量，最大1，最大100")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class ApiResponse(BaseModel):
    """通用API响应模型"""
    success: bool = Field(True, description="请求是否成功")
    message: str = Field("成功", description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: bool = Field(True, description="是否为错误")
    message: str = Field(..., description="错误消息")
    status_code: int = Field(..., description="HTTP状态码")
    path: str = Field(..., description="请求路径")
    details: Optional[List[Dict[str, Any]]] = Field(None, description="详细错误信息")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="错误时间")


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: List[Any] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页数量")
    pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


# 爬虫相关模型
class CrawlTaskRequest(BaseModel):
    """爬虫任务请求模型"""
    platform: PlatformType = Field(..., description="目标平台")
    keywords: Optional[List[str]] = Field(
        None, 
        description="搜索关键词列表，空则使用默认关键词",
        max_items=10
    )
    max_count: int = Field(
        50, 
        ge=1, 
        le=200, 
        description="最大爬取数量，范围1-200"
    )
    priority: str = Field("normal", description="任务优先级（low/normal/high）")
    
    @validator('keywords')
    def validate_keywords(cls, v):
        if v is not None:
            # 过滤空关键词
            v = [kw.strip() for kw in v if kw.strip()]
            if not v:
                return None
        return v


class MultiPlatformCrawlRequest(BaseModel):
    """多平台爬虫任务请求模型"""
    platforms: Optional[List[PlatformType]] = Field(
        None,
        description="目标平台列表，空则爬取所有可用平台",
        max_items=10
    )
    keywords: Optional[List[str]] = Field(
        None, 
        description="搜索关键词列表，空则使用默认关键词",
        max_items=10
    )
    max_count_per_platform: int = Field(
        20, 
        ge=1, 
        le=100, 
        description="每个平台最大爬取数量，范围1-100"
    )
    enable_ai_analysis: bool = Field(True, description="是否启用AI分析和总结")
    priority: str = Field("normal", description="任务优先级（low/normal/high）")
    
    @validator('keywords')
    def validate_keywords(cls, v):
        if v is not None:
            # 过滤空关键词
            v = [kw.strip() for kw in v if kw.strip()]
            if not v:
                return None
        return v


class CrawlTaskResponse(BaseModel):
    """爬虫任务响应模型"""
    task_id: str = Field(..., description="任务ID")
    platform: PlatformType = Field(..., description="目标平台")
    status: TaskStatus = Field(..., description="任务状态")
    keywords: List[str] = Field(..., description="使用的关键词")
    max_count: int = Field(..., description="最大爬取数量")
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    progress: int = Field(0, ge=0, le=100, description="任务进度百分比")
    error_message: Optional[str] = Field(None, description="错误信息")


class MultiPlatformCrawlResponse(BaseModel):
    """多平台爬虫响应模型"""
    batch_id: str = Field(..., description="批次ID")
    platforms: List[PlatformType] = Field(..., description="爬取的平台列表")
    task_ids: List[str] = Field(..., description="各平台任务ID列表")
    total_tasks: int = Field(..., description="总任务数")
    keywords: List[str] = Field(..., description="使用的关键词")
    max_count_per_platform: int = Field(..., description="每平台最大爬取数量")
    enable_ai_analysis: bool = Field(..., description="是否启用AI分析")
    created_at: datetime = Field(..., description="创建时间")
    overall_status: str = Field("pending", description="整体状态")


class BatchCrawlStatusResponse(BaseModel):
    """批次爬虫状态响应模型"""
    batch_id: str = Field(..., description="批次ID")
    overall_status: str = Field(..., description="整体状态")
    total_tasks: int = Field(..., description="总任务数")
    completed_tasks: int = Field(..., description="已完成任务数")
    failed_tasks: int = Field(..., description="失败任务数")
    overall_progress: int = Field(..., description="整体进度百分比")
    platform_status: Dict[str, Dict] = Field(..., description="各平台状态详情")
    ai_analysis_status: Optional[str] = Field(None, description="AI分析状态")
    total_content_found: int = Field(0, description="总共找到的内容数")
    ai_summary: Optional[Union[str, Dict[str, Any]]] = Field(None, description="AI生成的内容总结")


class CrawlResultResponse(BaseModel):
    """爬虫结果响应模型"""
    task_id: str = Field(..., description="任务ID")
    platform: PlatformType = Field(..., description="平台类型")
    total_count: int = Field(..., description="总共找到的内容数")
    success_count: int = Field(..., description="成功保存的内容数")
    duplicate_count: int = Field(..., description="重复跳过的内容数")
    error_count: int = Field(..., description="处理错误的内容数")
    execution_time: float = Field(..., description="执行时间（秒）")
    keywords_used: List[str] = Field(..., description="实际使用的关键词")


# AI处理相关模型
class AIProcessRequest(BaseModel):
    """
AI处理请求模型
    """
    project_id: int = Field(..., ge=1, description="项目ID")
    include_sentiment: bool = Field(True, description="是否包含情感分析")
    force_reprocess: bool = Field(False, description="是否强制重新处理")


class BatchAIProcessRequest(BaseModel):
    """批量AI处理请求模型"""
    batch_size: int = Field(10, ge=1, le=50, description="批次处理数量")
    max_concurrent: int = Field(3, ge=1, le=10, description="最大并发数")
    include_sentiment: bool = Field(True, description="是否包含情感分析")


class AIAnalysisResponse(BaseModel):
    """
AI分析响应模型
    """
    project_id: int = Field(..., description="项目ID")
    project_name: str = Field(..., description="项目名称")
    
    # TGE分析结果
    token_symbol: Optional[str] = Field(None, description="代币符号")
    project_category: ProjectCategory = Field(..., description="项目分类")
    tge_date: Optional[str] = Field(None, description="TGE日期")
    risk_level: RiskLevel = Field(..., description="风险等级")
    
    # 投资建议
    investment_rating: int = Field(..., ge=1, le=5, description="投资评级（1-5分）")
    investment_recommendation: InvestmentRecommendation = Field(..., description="投资建议")
    potential_score: int = Field(..., ge=1, le=5, description="潜力评分（1-5分）")
    overall_score: float = Field(..., description="综合评分")
    
    # 情感分析
    sentiment_score: Optional[float] = Field(None, ge=-1, le=1, description="情感评分（-1到1）")
    sentiment_label: Optional[str] = Field(None, description="情感标签")
    
    # 元数据
    analysis_confidence: float = Field(..., ge=0, le=1, description="分析置信度")
    analysis_timestamp: datetime = Field(..., description="分析时间")


# 项目相关模型
class ProjectSearchRequest(BaseModel):
    """项目搜索请求模型"""
    query: Optional[str] = Field(None, description="搜索关键词")
    category: Optional[ProjectCategory] = Field(None, description="项目分类过滤")
    risk_level: Optional[RiskLevel] = Field(None, description="风险等级过滤")
    platform: Optional[PlatformType] = Field(None, description="来源平台过滤")
    has_tge_date: Optional[bool] = Field(None, description="是否有TGE日期")
    is_processed: Optional[bool] = Field(None, description="是否已AI分析")
    
    # 排序参数
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", description="排序方向（asc/desc）")
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        allowed_fields = [
            'created_at', 'project_name', 'investment_rating', 
            'overall_score', 'engagement_score', 'tge_date'
        ]
        if v not in allowed_fields:
            raise ValueError(f"sort_by must be one of {allowed_fields}")
        return v
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v.lower() not in ['asc', 'desc']:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v.lower()


class ProjectSummaryResponse(BaseModel):
    """项目概要响应模型"""
    id: int = Field(..., description="项目ID")
    project_name: str = Field(..., description="项目名称")
    token_symbol: Optional[str] = Field(None, description="代币符号")
    project_category: ProjectCategory = Field(..., description="项目分类")
    risk_level: Optional[RiskLevel] = Field(None, description="风险等级")
    source_platform: PlatformType = Field(..., description="来源平台")
    
    # 投资相关
    investment_rating: Optional[int] = Field(None, description="投资评级")
    investment_recommendation: Optional[InvestmentRecommendation] = Field(None, description="投资建议")
    overall_score: Optional[float] = Field(None, description="综合评分")
    
    # 统计信息
    engagement_score: Optional[float] = Field(None, description="用户参与度")
    created_at: datetime = Field(..., description="创建时间")
    tge_date: Optional[str] = Field(None, description="TGE日期")
    is_processed: bool = Field(..., description="是否已AI分析")


class ProjectDetailResponse(BaseModel):
    """项目详情响应模型"""
    # 基本信息
    id: int = Field(..., description="项目ID")
    project_name: str = Field(..., description="项目名称")
    token_symbol: Optional[str] = Field(None, description="代币符号")
    project_category: ProjectCategory = Field(..., description="项目分类")
    risk_level: Optional[RiskLevel] = Field(None, description="风险等级")
    tge_date: Optional[str] = Field(None, description="TGE日期")
    
    # 来源信息
    source_platform: PlatformType = Field(..., description="来源平台")
    source_url: Optional[str] = Field(None, description="来源链接")
    source_username: Optional[str] = Field(None, description="来源用户")
    
    # 内容信息
    raw_content: str = Field(..., description="原始内容")
    tge_summary: Optional[str] = Field(None, description="TGE简介")
    key_features: Optional[List[str]] = Field(None, description="关键特性")
    
    # AI分析结果
    investment_rating: Optional[int] = Field(None, description="投资评级")
    investment_recommendation: Optional[InvestmentRecommendation] = Field(None, description="投资建议")
    investment_reason: Optional[str] = Field(None, description="投资建议理由")
    key_advantages: Optional[List[str]] = Field(None, description="主要优势")
    key_risks: Optional[List[str]] = Field(None, description="主要风险")
    potential_score: Optional[int] = Field(None, description="潜力评分")
    overall_score: Optional[float] = Field(None, description="综合评分")
    
    # 情感分析
    sentiment_score: Optional[float] = Field(None, description="情感评分")
    sentiment_label: Optional[str] = Field(None, description="情感标签")
    market_sentiment: Optional[str] = Field(None, description="市场情绪")
    
    # 统计信息
    engagement_score: Optional[float] = Field(None, description="参与度评分")
    keyword_matches: Optional[str] = Field(None, description="匹配的关键词")
    
    # 元数据
    content_hash: str = Field(..., description="内容哈希")
    is_processed: bool = Field(..., description="是否已AI分析")
    analysis_confidence: Optional[float] = Field(None, description="分析置信度")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


# 系统相关模型
class SystemStatsResponse(BaseModel):
    """系统统计响应模型"""
    # 项目统计
    total_projects: int = Field(..., description="总项目数")
    processed_projects: int = Field(..., description="已处理项目数")
    unprocessed_projects: int = Field(..., description="未处理项目数")
    
    # 平台统计
    platform_stats: Dict[str, int] = Field(..., description="各平台项目数")
    
    # 分类统计
    category_stats: Dict[str, int] = Field(..., description="各分类项目数")
    
    # 时间统计
    recent_24h: int = Field(..., description="近24小时新增项目")
    recent_7d: int = Field(..., description="近7天新增项目")
    
    # 系统信息
    api_version: str = Field(..., description="API版本")
    uptime: float = Field(..., description="运行时间（秒）")
    last_updated: datetime = Field(..., description="最后更新时间")