"""
知乎平台适配器 - 使用MediaCrawler原生实现
按照MULTI_PLATFORM_DEVELOPMENT_PLAN.md第3.2节实现
集成MediaCrawler的原生知乎爬取能力
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import structlog
import re
import os
import sys
import html

from crawler.base_platform import AbstractPlatform, PlatformError
from crawler.models import RawContent, Platform, ContentType
from crawler.platforms.mediacrawler_zhihu_adapter import MediaCrawlerZhihuAdapter

logger = structlog.get_logger()


class ZhihuPlatform(AbstractPlatform):
    """
    知乎平台适配器 - 使用MediaCrawler原生实现
    支持问答、文章、想法等多种内容类型
    实现专业度评估和质量过滤机制
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        # 先设置platform_name，因为父类构造函数需要使用它
        self.platform_name = Platform.ZHIHU
        
        super().__init__(config)
        self.logger = logger.bind(platform=self.platform_name.value)
        
        # 知乎特定配置
        self.search_type = os.getenv("ZHIHU_SEARCH_TYPE", "综合")
        self.max_pages = int(os.getenv("ZHIHU_MAX_PAGES", "10"))
        self.rate_limit = int(os.getenv("ZHIHU_RATE_LIMIT", "60"))
        self.cookie = os.getenv("ZHIHU_COOKIE", "")
        self.login_method = os.getenv("ZHIHU_LOGIN_METHOD", "cookie")
        self.headless = os.getenv("ZHIHU_HEADLESS", "true").lower() == "true"
        
        # MediaCrawler适配器
        self._mediacrawler_adapter = None
        self._mediacrawler_path = os.getenv("MEDIACRAWLER_PATH", "./mediacrawler")
        
    def get_platform_name(self) -> Platform:
        """获取平台名称"""
        return self.platform_name
    
    async def is_available(self) -> bool:
        """检查知乎平台是否可用"""
        try:
            # 检查Cookie配置
            if not self.cookie:
                self.logger.warning("Zhihu cookie not configured")
                return False
            
            # 初始化MediaCrawler适配器
            adapter = await self._get_mediacrawler_adapter()
            if not adapter:
                return False
            
            # 检查连接状态
            ping_result = await adapter.ping()
            
            if ping_result:
                self.logger.info("Zhihu platform is available via MediaCrawler")
                return True
            else:
                self.logger.warning("MediaCrawler zhihu ping failed")
                return False
                
        except Exception as e:
            self.logger.error("Zhihu platform availability check failed", error=str(e))
            return False
    
    async def crawl(
        self, 
        keywords: List[str], 
        max_count: int = 50,
        **kwargs
    ) -> List[RawContent]:
        """
        爬取知乎内容 - 使用MediaCrawler
        
        Args:
            keywords: 搜索关键词列表
            max_count: 最大爬取数量
            **kwargs: 其他参数
            
        Returns:
            爬取到的内容列表
        """
        
        # 检查平台可用性
        if not await self.is_available():
            raise PlatformError(
                platform=self.platform_name.value,
                message="Platform not available",
                error_code="PLATFORM_UNAVAILABLE"
            )
        
        # 验证关键词
        if not keywords or not any(keyword.strip() for keyword in keywords):
            raise PlatformError(
                platform=self.platform_name.value,
                message="Keywords cannot be empty",
                error_code="INVALID_KEYWORDS"
            )
        
        # 清理和验证关键词
        valid_keywords = [kw.strip() for kw in keywords if kw.strip()]
        self.logger.info("Keywords validated", 
                        original_count=len(keywords), 
                        valid_count=len(valid_keywords))
        
        try:
            # 获取MediaCrawler适配器
            adapter = await self._get_mediacrawler_adapter()
            
            # 执行搜索
            all_raw_data = []
            for keyword in valid_keywords:
                try:
                    # 使用MediaCrawler进行搜索
                    search_results = await adapter.search_by_keyword(
                        keyword=keyword,
                        page=1,
                        page_size=min(max_count, 20)  # MediaCrawler单次最多20条
                    )
                    
                    self.logger.info(f"MediaCrawler search for '{keyword}' returned {len(search_results)} results")
                    all_raw_data.extend(search_results)
                    
                    # 延迟避免过快请求
                    await self._delay_between_requests()
                    
                except Exception as e:
                    self.logger.error(f"Failed to search keyword '{keyword}'", error=str(e))
                    continue
            
            # 限制总结果数量
            if len(all_raw_data) > max_count:
                all_raw_data = all_raw_data[:max_count]
            
            # 转换为统一格式
            raw_contents = []
            for item in all_raw_data:
                try:
                    content = self._convert_to_raw_content(item)
                    if content:
                        raw_contents.append(content)
                except Exception as e:
                    self.logger.warning("Failed to convert item", error=str(e), item_id=item.get('id'))
                    continue
            
            # 内容过滤
            filtered_contents = [
                content for content in raw_contents 
                if not self._should_filter_content(content)
            ]
            
            self.logger.info("Content filtered",
                           original_count=len(raw_contents),
                           filtered_count=len(filtered_contents))
            
            self.logger.info("Zhihu crawl completed via MediaCrawler",
                           keywords=valid_keywords,
                           raw_count=len(all_raw_data),
                           filtered_count=len(filtered_contents))
        
            return filtered_contents
            
        except Exception as e:
            self.logger.error("Zhihu search failed", error=str(e))
            raise PlatformError(
                platform=self.platform_name.value,
                message=f"Search failed: {str(e)}",
                error_code="SEARCH_FAILED"
            )
    
    async def _get_mediacrawler_adapter(self) -> Optional[MediaCrawlerZhihuAdapter]:
        """获取MediaCrawler适配器实例"""
        if self._mediacrawler_adapter is None:
            try:
                self._mediacrawler_adapter = MediaCrawlerZhihuAdapter(
                    cookie=self.cookie,
                    logger=self.logger
                )
                self.logger.info("MediaCrawler adapter created successfully")
            except Exception as e:
                self.logger.error(f"Failed to create MediaCrawler adapter: {e}")
                return None
        
        return self._mediacrawler_adapter
    
    async def _delay_between_requests(self):
        """请求间延迟"""
        import asyncio
        delay = 60 / self.rate_limit  # 根据速率限制计算延迟
        await asyncio.sleep(delay)
    
    def _convert_to_raw_content(self, zhihu_data: Dict[str, Any]) -> RawContent:
        """将知乎数据转换为统一的RawContent格式"""
        try:
            content_type_map = {
                'answer': ContentType.ANSWER,
                'article': ContentType.ARTICLE,
                'pin': ContentType.PIN,
                'question': ContentType.QUESTION,
                'zvideo': ContentType.POST  # 视频映射为POST
            }
            
            content_type = content_type_map.get(
                zhihu_data.get('type'), 
                ContentType.POST
            )
            
            # 清理HTML标签
            content_text = self._clean_html_content(zhihu_data.get('content', ''))
            
            # 处理标题
            title = zhihu_data.get('title', '')
            
            # 处理作者信息
            author = zhihu_data.get('author', {})
            author_name = author.get('name', '')
            author_id = str(author.get('id', ''))
            
            # 处理时间
            publish_time = None
            created_time = zhihu_data.get('created_time', 0)
            if created_time:
                if isinstance(created_time, int):
                    publish_time = datetime.fromtimestamp(created_time)
                else:
                    publish_time = datetime.now()
            else:
                publish_time = datetime.now()
            
            # 处理互动数据
            like_count = zhihu_data.get('voteup_count', 0) or 0
            comment_count = zhihu_data.get('comment_count', 0) or 0
            share_count = 0  # 知乎通常不显示分享数
            
            # 处理URL
            source_url = zhihu_data.get('url', '')
            
            # 处理标签（从内容中提取话题）
            hashtags = self._extract_hashtags_from_content(content_text)
            
            return RawContent(
                content_id=str(zhihu_data.get('id', '')),
                platform=self.platform_name,
                content_type=content_type,
                title=title,
                content=content_text,
                raw_content=zhihu_data.get('content', ''),  # 保留原始HTML内容
                author_name=author_name,
                author_id=author_id,
                publish_time=publish_time,
                crawl_time=datetime.now(),  # 当前爬取时间
                like_count=like_count,
                comment_count=comment_count,
                share_count=share_count,
                source_url=source_url,
                hashtags=hashtags,
                image_urls=[],  # 知乎图片需要特殊处理，暂时留空
                platform_metadata={
                    'zhihu_type': zhihu_data.get('type'),
                    'professional_score': self._calculate_professional_score(zhihu_data),
                    'author_headline': author.get('headline', ''),
                    'follower_count': author.get('follower_count', 0)
                }
            )
            
        except Exception as e:
            self.logger.error("Failed to convert zhihu data to RawContent", error=str(e))
            raise
    
    def _clean_html_content(self, content: str) -> str:
        """清理HTML标签并保留纯文本"""
        if not content:
            return ""
        
        # 解码HTML实体
        content = html.unescape(content)
        
        # 移除HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理多余的空白字符
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _extract_hashtags_from_content(self, content: str) -> List[str]:
        """从内容中提取话题标签"""
        hashtags = []
        
        # 知乎中的话题通常用「」包围
        topic_pattern = r'「([^」]+)」'
        topics = re.findall(topic_pattern, content)
        
        for topic in topics:
            topic = topic.strip()
            if topic and topic not in hashtags:
                hashtags.append(topic)
        
        return hashtags
    
    def _should_filter_content(self, content) -> bool:
        """判断内容是否应该被过滤掉"""
        if isinstance(content, RawContent):
            # 内容长度过滤
            if len(content.content) < 20:  # 知乎内容一般较长
                return True
            
            # 质量过滤：点赞数和评论数都很少的内容
            if content.like_count < 5 and content.comment_count < 2:
                return True
            
            # 专业度评估
            if content.platform_metadata and content.platform_metadata.get('professional_score', 0) < 0.3:
                return True
                
        elif isinstance(content, dict):
            # 直接从字典数据过滤
            text_content = content.get('content', '')
            if len(text_content) < 20:
                return True
            
            voteup_count = content.get('voteup_count', 0) or content.get('like_count', 0)
            comment_count = content.get('comment_count', 0)
            
            if voteup_count < 5 and comment_count < 2:
                return True
        
        return False
    
    def _calculate_professional_score(self, zhihu_data: Dict[str, Any]) -> float:
        """计算内容专业度分数"""
        score = 0.0
        
        # 作者专业度
        author = zhihu_data.get('author', {})
        headline = author.get('headline', '')
        follower_count = author.get('follower_count', 0)
        
        # 根据作者标题判断专业度
        professional_keywords = ['分析师', '投资', '研究员', '专家', '顾问', '基金', '经理']
        if any(keyword in headline for keyword in professional_keywords):
            score += 0.3
        
        # 根据粉丝数量判断影响力
        if follower_count > 10000:
            score += 0.2
        elif follower_count > 1000:
            score += 0.1
        
        # 根据互动数据判断质量
        voteup_count = zhihu_data.get('voteup_count', 0) or zhihu_data.get('like_count', 0)
        comment_count = zhihu_data.get('comment_count', 0)
        
        if voteup_count > 100:
            score += 0.2
        elif voteup_count > 50:
            score += 0.1
        
        if comment_count > 20:
            score += 0.1
        elif comment_count > 10:
            score += 0.05
        
        # 根据内容长度判断深度
        content_length = len(zhihu_data.get('content', ''))
        if content_length > 1000:
            score += 0.1
        elif content_length > 500:
            score += 0.05
        
        return min(score, 1.0)  # 最大值为1.0