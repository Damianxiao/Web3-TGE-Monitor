"""
爬虫平台基类
定义统一的接口规范
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import structlog

from .models import RawContent, CrawlTask, CrawlResult, Platform

logger = structlog.get_logger()


class AbstractPlatform(ABC):
    """抽象平台基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logger.bind(platform=self.get_platform_name())
    
    @abstractmethod
    def get_platform_name(self) -> Platform:
        """获取平台名称"""
        pass
    
    @abstractmethod
    async def crawl(
        self, 
        keywords: List[str], 
        max_count: int = 50,
        **kwargs
    ) -> List[RawContent]:
        """
        爬取内容
        
        Args:
            keywords: 搜索关键词列表
            max_count: 最大爬取数量
            **kwargs: 其他平台特定参数
            
        Returns:
            爬取到的内容列表
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """检查平台是否可用"""
        pass
    
    async def validate_keywords(self, keywords: List[str]) -> List[str]:
        """
        验证和过滤关键词
        
        Args:
            keywords: 原始关键词列表
            
        Returns:
            验证后的关键词列表
        """
        # 基础验证：移除空关键词
        valid_keywords = [kw.strip() for kw in keywords if kw.strip()]
        
        if not valid_keywords:
            raise ValueError("No valid keywords provided")
        
        self.logger.info("Keywords validated", 
                        original_count=len(keywords),
                        valid_count=len(valid_keywords))
        
        return valid_keywords
    
    async def filter_content(self, contents: List[RawContent]) -> List[RawContent]:
        """
        过滤内容（基础过滤逻辑）
        
        Args:
            contents: 原始内容列表
            
        Returns:
            过滤后的内容列表
        """
        # 基础过滤：移除空内容
        filtered = []
        
        for content in contents:
            if self._is_valid_content(content):
                filtered.append(content)
            else:
                self.logger.debug("Content filtered out", 
                                content_id=content.content_id,
                                reason="invalid_content")
        
        self.logger.info("Content filtered",
                        original_count=len(contents),
                        filtered_count=len(filtered))
        
        return filtered
    
    def _is_valid_content(self, content: RawContent) -> bool:
        """检查内容是否有效"""
        # 基础有效性检查
        if not content.content_id:
            return False
        
        if not content.title and not content.content:
            return False
        
        # 内容长度检查
        total_content = (content.title or "") + (content.content or "")
        if len(total_content.strip()) < 10:
            return False
        
        return True
    
    async def transform_to_raw_content(self, platform_data: Dict[str, Any]) -> RawContent:
        """
        将平台原始数据转换为统一格式
        子类需要实现具体的转换逻辑
        """
        raise NotImplementedError("Subclasses must implement transform_to_raw_content")
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """获取速率限制配置"""
        return self.config.get('rate_limit', {
            'requests_per_minute': 30,
            'delay_between_requests': 2.0
        })
    
    def get_retry_config(self) -> Dict[str, Any]:
        """获取重试配置"""
        return self.config.get('retry', {
            'max_retries': 3,
            'backoff_factor': 1.5,
            'retry_on_errors': ['timeout', 'connection_error']
        })


class PlatformError(Exception):
    """平台相关错误基类"""
    
    def __init__(self, platform: str, message: str, error_code: str = None):
        self.platform = platform
        self.message = message
        self.error_code = error_code
        super().__init__(f"[{platform}] {message}")


class PlatformUnavailableError(PlatformError):
    """平台不可用错误"""
    pass


class PlatformAuthError(PlatformError):
    """平台认证错误"""
    pass


class PlatformRateLimitError(PlatformError):
    """平台限流错误"""
    pass


class ContentParseError(PlatformError):
    """内容解析错误"""
    pass