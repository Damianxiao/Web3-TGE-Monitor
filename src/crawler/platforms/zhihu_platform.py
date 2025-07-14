"""
知乎平台适配器 - 使用MediaCrawler集成层
基于实际验证的MediaCrawler成功方案重构
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import structlog
import re
import html

from crawler.base_platform import AbstractPlatform, PlatformError
from crawler.models import RawContent, Platform, ContentType
from crawler.platforms.mediacrawler_zhihu_integration import (
    MediaCrawlerZhihuIntegration, 
    create_mediacrawler_integration
)

logger = structlog.get_logger()


class ZhihuPlatform(AbstractPlatform):
    """
    知乎平台适配器 - 使用MediaCrawler集成层
    基于实际测试验证的成功方案实现
    支持问答、文章、想法等多种内容类型
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        # 先设置platform_name，因为父类构造函数需要使用它
        self.platform_name = Platform.ZHIHU
        
        super().__init__(config)
        self.logger = logger.bind(platform=self.platform_name.value)
        
        # MediaCrawler集成实例
        self._mediacrawler_integration = None
        
    def get_platform_name(self) -> Platform:
        """获取平台名称"""
        return self.platform_name
    
    async def _get_mediacrawler_integration(self) -> MediaCrawlerZhihuIntegration:
        """获取或创建MediaCrawler集成实例"""
        if self._mediacrawler_integration is None:
            try:
                self._mediacrawler_integration = await create_mediacrawler_integration()
                self.logger.info("MediaCrawler integration initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize MediaCrawler integration: {e}")
                raise PlatformError(self.platform_name.value, f"MediaCrawler initialization failed: {e}")
        
        return self._mediacrawler_integration
    
    async def search(self, keywords: str, max_results: int = 50) -> List[RawContent]:
        """
        搜索知乎内容
        
        Args:
            keywords: 搜索关键词
            max_results: 最大结果数量
            
        Returns:
            List[RawContent]: 原始内容列表
        """
        self.logger.info(f"Starting zhihu search: keywords='{keywords}', max_results={max_results}")
        
        try:
            # 获取MediaCrawler集成实例
            integration = await self._get_mediacrawler_integration()
            
            # 执行搜索
            raw_results = await integration.search_content(keywords, max_results)
            
            # 转换为RawContent格式
            contents = []
            for item in raw_results:
                content = self._convert_to_raw_content(item, keywords)
                if content:
                    contents.append(content)
            
            self.logger.info(f"Zhihu search completed: {len(contents)} contents found")
            return contents
            
        except Exception as e:
            self.logger.error(f"Zhihu search failed: {e}")
            raise PlatformError(self.platform_name.value, f"Search failed: {e}")
    
    async def get_content_details(self, content_id: str) -> Optional[RawContent]:
        """
        获取内容详情
        
        Args:
            content_id: 内容ID
            
        Returns:
            Optional[RawContent]: 内容详情或None
        """
        self.logger.info(f"Getting zhihu content details: {content_id}")
        
        try:
            # 获取MediaCrawler集成实例
            integration = await self._get_mediacrawler_integration()
            
            # 获取详情
            details = await integration.get_content_details(content_id)
            if not details:
                self.logger.warning(f"Content not found: {content_id}")
                return None
            
            # 转换为RawContent格式
            content = self._convert_to_raw_content(details)
            self.logger.info(f"Content details retrieved: {content_id}")
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to get content details: {e}")
            raise PlatformError(self.platform_name.value, f"Get content details failed: {e}")
    
    def _convert_to_raw_content(self, item: Dict[str, Any], source_keywords: str = "") -> Optional[RawContent]:
        """
        将MediaCrawler数据转换为RawContent格式
        
        Args:
            item: MediaCrawler数据项
            source_keywords: 搜索关键词
            
        Returns:
            Optional[RawContent]: 转换后的内容或None
        """
        try:
            # 确定内容类型
            content_type = self._determine_content_type(item.get('content_type', ''))
            
            # 清理和处理文本内容
            cleaned_text = self._clean_content_text(item.get('content', ''))
            title = self._clean_content_text(item.get('title', ''))
            
            # 提取作者信息
            author_info = item.get('author', {})
            
            # 提取互动数据
            stats = item.get('stats', {})
            
            # 创建RawContent对象
            raw_content = RawContent(
                platform=self.platform_name,
                content_id=item.get('id', ''),
                content_type=content_type,
                title=title,
                content=cleaned_text,
                raw_content=item.get('content', ''),  # 保留原始内容
                author_id=author_info.get('id', ''),
                author_name=author_info.get('nickname', ''),
                author_avatar=author_info.get('avatar', ''),
                publish_time=self._convert_timestamp(item.get('created_time')) or datetime.now(),
                crawl_time=datetime.now(),
                last_update_time=self._convert_timestamp(item.get('updated_time')),
                like_count=stats.get('voteup_count', 0),
                comment_count=stats.get('comment_count', 0),
                share_count=0,  # 知乎API不提供分享数
                collect_count=0,  # 知乎API不提供收藏数
                source_url=item.get('url', ''),
                tags=[],  # 可以后续从内容中提取
                hashtags=[],  # 可以后续从内容中提取
                image_urls=[],  # 可以后续从内容中提取
                video_urls=[],  # 可以后续从内容中提取
                source_keywords=[source_keywords] if source_keywords else [],
                platform_metadata={
                    'source_keywords': source_keywords or item.get('metadata', {}).get('source_keyword', ''),
                    'question_id': item.get('metadata', {}).get('question_id', ''),
                    'description': item.get('metadata', {}).get('description', ''),
                    'author_profile_url': author_info.get('profile_url', ''),
                    'mediacrawler_data': item.get('metadata', {})
                }
            )
            
            # 验证必需字段
            if not raw_content.content_id or not raw_content.title:
                self.logger.warning(f"Skipping content with missing required fields: {item}")
                return None
            
            return raw_content
            
        except Exception as e:
            self.logger.error(f"Failed to convert item to RawContent: {e}")
            return None
    
    def _determine_content_type(self, mediacrawler_type: str) -> ContentType:
        """
        根据MediaCrawler的content_type确定我们的ContentType
        
        Args:
            mediacrawler_type: MediaCrawler的内容类型
            
        Returns:
            ContentType: 对应的内容类型
        """
        type_mapping = {
            'answer': ContentType.ANSWER,
            'article': ContentType.ARTICLE,
            'pin': ContentType.PIN,
            'question': ContentType.QUESTION,
            'zvideo': ContentType.VIDEO
        }
        
        return type_mapping.get(mediacrawler_type.lower(), ContentType.POST)
    
    def _clean_content_text(self, text: str) -> str:
        """
        清理内容文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
        
        # HTML解码
        text = html.unescape(text)
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 清理多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 移除特殊字符
        text = re.sub(r'[\\n\\r\\t]', ' ', text)
        
        return text
    
    def _convert_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """
        转换时间戳为datetime对象
        
        Args:
            timestamp: 时间戳（可能是int、str或None）
            
        Returns:
            Optional[datetime]: 转换后的datetime对象或None
        """
        if not timestamp:
            return None
        
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                return datetime.fromtimestamp(int(timestamp))
            else:
                return None
        except (ValueError, TypeError, OSError):
            self.logger.warning(f"Failed to convert timestamp: {timestamp}")
            return None
    
    async def crawl(self, **kwargs) -> List[RawContent]:
        """
        通用爬取方法 - 实现AbstractPlatform接口
        
        Args:
            **kwargs: 爬取参数，支持keywords和max_results
            
        Returns:
            List[RawContent]: 原始内容列表
        """
        keywords = kwargs.get('keywords', '')
        max_results = kwargs.get('max_results', 50)
        
        if not keywords:
            raise ValueError("Keywords are required for crawling")
        
        return await self.search(keywords, max_results)
    
    async def is_available(self) -> bool:
        """
        检查平台是否可用
        
        Returns:
            bool: 平台是否可用
        """
        try:
            # 尝试创建MediaCrawler集成实例
            integration = await self._get_mediacrawler_integration()
            return integration is not None
        except Exception as e:
            self.logger.error(f"Platform availability check failed: {e}")
            return False
    
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户信息（暂不支持）
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict]: 用户信息或None
        """
        self.logger.warning("get_user_info not implemented for MediaCrawler integration")
        return None
    
    async def get_trending_topics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热门话题（暂不支持）
        
        Args:
            limit: 限制数量
            
        Returns:
            List[Dict]: 热门话题列表
        """
        self.logger.warning("get_trending_topics not implemented for MediaCrawler integration")
        return []
    
    def cleanup(self):
        """清理资源"""
        if self._mediacrawler_integration:
            self._mediacrawler_integration.cleanup()
            self._mediacrawler_integration = None
        
        self.logger.info("ZhihuPlatform resources cleaned up")
    
    def __del__(self):
        """析构函数，确保资源清理"""
        self.cleanup()


# 知乎平台特定的辅助功能

class ZhihuContentAnalyzer:
    """知乎内容分析器"""
    
    @staticmethod
    def calculate_professional_score(content: RawContent) -> float:
        """
        计算内容专业度分数
        
        Args:
            content: 内容对象
            
        Returns:
            float: 专业度分数 (0-1)
        """
        score = 0.0
        factors = []
        
        # 标题质量分析
        if content.title:
            title_length = len(content.title)
            if 10 <= title_length <= 100:
                factors.append(0.2)
            
        # 内容长度分析
        if content.content:
            content_length = len(content.content)
            if content_length > 200:
                factors.append(0.3)
            if content_length > 1000:
                factors.append(0.2)
        
        # 互动数据分析
        stats = content.metadata.get('stats', {})
        voteup_count = stats.get('voteup_count', 0)
        if voteup_count > 10:
            factors.append(0.2)
        if voteup_count > 100:
            factors.append(0.1)
        
        return min(sum(factors), 1.0)
    
    @staticmethod
    def extract_keywords(content: RawContent) -> List[str]:
        """
        提取内容关键词
        
        Args:
            content: 内容对象
            
        Returns:
            List[str]: 关键词列表
        """
        keywords = []
        
        # 从标题提取
        if content.title:
            # 简单的关键词提取（可以后续优化）
            title_words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', content.title)
            keywords.extend([w for w in title_words if len(w) > 1])
        
        # 从内容提取（取前100个字符）
        if content.content:
            content_preview = content.content[:100]
            content_words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', content_preview)
            keywords.extend([w for w in content_words if len(w) > 1])
        
        # 去重并限制数量
        return list(set(keywords))[:10]