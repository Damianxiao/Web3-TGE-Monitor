"""
微博平台适配器
按照MULTI_PLATFORM_DEVELOPMENT_PLAN.md第3.1节实现
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import structlog
import re
import os
import sys

from ..base_platform import AbstractPlatform, PlatformError
from ..models import RawContent, Platform, ContentType

logger = structlog.get_logger()


class WeiboPlatform(AbstractPlatform):
    """
    微博平台适配器
    支持微博内容搜索和数据转换
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        # 先设置platform_name，因为父类构造函数需要使用它
        self.platform_name = Platform.WEIBO
        
        super().__init__(config)
        self.logger = logger.bind(platform=self.platform_name.value)
        
        # 微博特定配置
        self.search_type = os.getenv("WEIBO_SEARCH_TYPE", "综合")
        self.max_pages = int(os.getenv("WEIBO_MAX_PAGES", "10"))
        self.rate_limit = int(os.getenv("WEIBO_RATE_LIMIT", "60"))
        
        # MediaCrawler集成
        self._crawler = None
        self._mediacrawler_path = os.getenv("MEDIACRAWLER_PATH", "../mediacrawler")
        
    def get_platform_name(self) -> Platform:
        """获取平台名称"""
        return self.platform_name
    
    async def is_available(self) -> bool:
        """检查微博平台是否可用"""
        try:
            # 检查登录状态
            login_status = await self._check_login_status()
            
            if not login_status:
                self.logger.warning("Weibo login check failed")
                return False
                
            self.logger.info("Weibo platform is available")
            return True
            
        except Exception as e:
            self.logger.error("Weibo platform availability check failed", error=str(e))
            return False
    
    async def crawl(
        self, 
        keywords: List[str], 
        max_count: int = 50,
        **kwargs
    ) -> List[RawContent]:
        """
        爬取微博内容
        
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
        validated_keywords = await self.validate_keywords(keywords)
        
        # 执行实际爬取
        raw_data = await self._execute_crawl(validated_keywords, max_count, **kwargs)
        
        # 转换数据格式
        raw_contents = []
        for item in raw_data:
            try:
                content = self._convert_to_raw_content(item)
                raw_contents.append(content)
            except Exception as e:
                self.logger.warning("Failed to transform weibo content", 
                                  content_id=item.get('id', 'unknown'),
                                  error=str(e))
        
        # 过滤内容
        filtered_contents = await self.filter_content(raw_contents)
        
        self.logger.info("Weibo crawl completed",
                        keywords=validated_keywords,
                        raw_count=len(raw_data),
                        filtered_count=len(filtered_contents))
        
        return filtered_contents
    
    async def _execute_crawl(
        self, 
        keywords: List[str], 
        max_count: int, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """执行微博搜索爬取"""
        
        try:
            # 初始化MediaCrawler
            crawler = await self._get_crawler()
            
            # 构建搜索关键词
            search_keyword = " ".join(keywords)
            
            # 计算页数
            max_pages = min(max_count // 20 + 1, self.max_pages)
            
            self.logger.info("Starting weibo search",
                           keyword=search_keyword,
                           max_pages=max_pages,
                           search_type=self.search_type)
            
            # 执行搜索
            results = await crawler.search_notes(
                keyword=search_keyword,
                max_pages=max_pages,
                search_type=self.search_type
            )
            
            # 限制结果数量
            if len(results) > max_count:
                results = results[:max_count]
            
            self.logger.info("Weibo search completed", 
                           results_count=len(results))
            
            return results
            
        except Exception as e:
            self.logger.error("Weibo search failed", error=str(e))
            raise PlatformError(
                platform=self.platform_name.value,
                message=f"Search failed: {str(e)}",
                error_code="SEARCH_FAILED"
            )
    
    def _convert_to_raw_content(self, weibo_data: Dict[str, Any]) -> RawContent:
        """
        将微博数据转换为统一的RawContent格式
        按照文档3.1.2节实现细节
        """
        
        # 提取基本信息
        content_id = str(weibo_data.get('id', ''))
        text_content = weibo_data.get('text', '')
        user_info = weibo_data.get('user', {})
        
        # 构建URL
        user_id = user_info.get('id', '')
        source_url = f"https://weibo.com/{user_id}/{content_id}" if user_id and content_id else ""
        
        # 解析互动数据
        like_count = self._parse_count(weibo_data.get('attitudes_count', 0))
        comment_count = self._parse_count(weibo_data.get('comments_count', 0))
        share_count = self._parse_count(weibo_data.get('reposts_count', 0))
        
        # 提取图片URLs
        image_urls = weibo_data.get('pic_urls', [])
        if isinstance(image_urls, list):
            image_urls = [url for url in image_urls if isinstance(url, str)]
        else:
            image_urls = []
        
        # 解析发布时间
        publish_time = self._parse_timestamp(weibo_data.get('created_at'))
        
        # 提取标签
        hashtags = self._extract_hashtags(text_content)
        
        return RawContent(
            platform=self.platform_name,
            content_id=content_id,
            content_type=ContentType.MIXED if image_urls else ContentType.TEXT,
            title=text_content[:100] if text_content else "",  # 微博无标题，使用内容前100字符
            content=text_content,
            raw_content=str(weibo_data),
            author_id=str(user_info.get('id', '')),
            author_name=user_info.get('screen_name', ''),
            author_avatar=user_info.get('profile_image_url', ''),
            publish_time=publish_time,
            crawl_time=datetime.utcnow(),
            like_count=like_count,
            comment_count=comment_count,
            share_count=share_count,
            image_urls=image_urls,
            hashtags=hashtags,
            source_url=source_url,
            ip_location=weibo_data.get('location', ''),
            platform_metadata={
                'weibo_type': weibo_data.get('type', ''),
                'is_verified': user_info.get('verified', False),
                'followers_count': user_info.get('followers_count', 0),
                'original_data': weibo_data
            }
        )
    
    def _parse_timestamp(self, time_value: Any) -> datetime:
        """解析微博时间戳"""
        if not time_value:
            return datetime.utcnow()
            
        try:
            # 处理Unix时间戳
            if isinstance(time_value, (int, float)):
                if time_value > 10**12:  # 毫秒时间戳
                    return datetime.fromtimestamp(time_value / 1000)
                else:  # 秒时间戳
                    return datetime.fromtimestamp(time_value)
            
            # 处理字符串时间格式
            if isinstance(time_value, str):
                # ISO格式
                if 'T' in time_value:
                    return datetime.fromisoformat(time_value.replace('Z', '+00:00'))
                
                # 其他可能的格式可以在这里添加
                
        except Exception as e:
            self.logger.warning("Failed to parse timestamp", 
                              timestamp=time_value, 
                              error=str(e))
        
        return datetime.utcnow()
    
    def _parse_count(self, count_value: Any) -> int:
        """解析微博数量字段（处理中文数字如'1.2万'）"""
        if isinstance(count_value, int):
            return count_value
            
        if isinstance(count_value, str):
            count_str = count_value.strip()
            
            # 处理中文数字
            if '万' in count_str:
                try:
                    num = float(count_str.replace('万', ''))
                    return int(num * 10000)
                except ValueError:
                    pass
            elif '千' in count_str:
                try:
                    num = float(count_str.replace('千', ''))
                    return int(num * 1000)
                except ValueError:
                    pass
            elif count_str.isdigit():
                return int(count_str)
        
        return 0
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """从微博文本中提取话题标签"""
        if not text:
            return []
        
        # 微博话题格式: #话题名称#
        hashtag_pattern = r'#([^#]+)#'
        hashtags = re.findall(hashtag_pattern, text)
        
        # 清理和去重
        cleaned_hashtags = []
        for tag in hashtags:
            tag = tag.strip()
            if tag and tag not in cleaned_hashtags:
                cleaned_hashtags.append(tag)
        
        return cleaned_hashtags
    
    async def _check_login_status(self) -> bool:
        """检查微博登录状态"""
        try:
            # 实际实现中需要检查MediaCrawler的登录状态
            # 这里先返回True作为模拟
            return True
        except Exception as e:
            self.logger.error("Login status check failed", error=str(e))
            return False
    
    async def _get_crawler(self):
        """获取MediaCrawler实例"""
        if self._crawler is None:
            # 实际实现中需要初始化MediaCrawler
            # 这里创建一个模拟对象
            self._crawler = MockWeiboClient()
        return self._crawler


class MockWeiboClient:
    """
    模拟微博客户端
    实际实现时需要替换为真实的MediaCrawler客户端
    """
    
    async def search_notes(self, keyword: str, max_pages: int, search_type: str) -> List[Dict[str, Any]]:
        """模拟搜索微博"""
        # 返回模拟数据用于测试
        mock_data = [
            {
                'id': '123456',
                'text': f'测试微博内容关于{keyword}代币发行',
                'user': {
                    'screen_name': '测试用户',
                    'id': 'user123',
                    'verified': False,
                    'followers_count': 1000,
                    'profile_image_url': 'http://example.com/avatar.jpg'
                },
                'created_at': '2025-07-13T10:00:00',
                'reposts_count': 10,
                'comments_count': 5,
                'attitudes_count': 20,
                'pic_urls': ['http://example.com/pic1.jpg'],
                'location': '北京',
                'type': 'normal'
            }
        ]
        
        return mock_data