"""
知乎平台适配器
按照MULTI_PLATFORM_DEVELOPMENT_PLAN.md第3.2节实现
支持知乎特有的问答、文章、想法等内容类型
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

logger = structlog.get_logger()


class ZhihuPlatform(AbstractPlatform):
    """
    知乎平台适配器
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
        
        # MediaCrawler集成
        self._crawler = None
        self._mediacrawler_path = os.getenv("MEDIACRAWLER_PATH", "./mediacrawler")
        self._mediacrawler_modules = None
        
        # 延迟导入MediaCrawler组件，避免初始化时的配置问题
        
    def _import_mediacrawler_modules(self):
        """延迟导入MediaCrawler模块"""
        if self._mediacrawler_modules is not None:
            return self._mediacrawler_modules
            
        try:
            # 添加MediaCrawler路径到系统路径
            if self._mediacrawler_path not in sys.path:
                sys.path.insert(0, self._mediacrawler_path)
            
            # 导入知乎相关模块
            from media_platform.zhihu.client import ZhihuClient
            from media_platform.zhihu.field import SearchType
            
            self._mediacrawler_modules = {
                'ZhihuClient': ZhihuClient,
                'SearchType': SearchType
            }
            
            self.logger.info("MediaCrawler zhihu modules imported successfully")
            return self._mediacrawler_modules
            
        except ImportError as e:
            self.logger.warning(f"Failed to import MediaCrawler modules: {e}")
            self.logger.info("Using simplified HTTP client instead")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error importing MediaCrawler: {e}")
            return None
        
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
            
            # 检查登录状态
            login_status = await self._check_login_status()
            
            if not login_status:
                self.logger.warning("Zhihu login check failed")
                return False
                
            self.logger.info("Zhihu platform is available")
            return True
            
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
        爬取知乎内容
        
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
            # 执行爬取
            raw_data = await self._execute_crawl(valid_keywords, max_count, **kwargs)
            
            # 转换为统一格式
            raw_contents = []
            for item in raw_data:
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
            
            self.logger.info("Zhihu crawl completed",
                           keywords=valid_keywords,
                           raw_count=len(raw_data),
                           filtered_count=len(filtered_contents))
        
            return filtered_contents
            
        except Exception as e:
            self.logger.error("Zhihu search failed", error=str(e))
            raise PlatformError(
                platform=self.platform_name.value,
                message=f"Search failed: {str(e)}",
                error_code="SEARCH_FAILED"
            )
    
    async def _execute_crawl(
        self, 
        keywords: List[str], 
        max_count: int, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """执行知乎搜索爬取"""
        
        try:
            # 获取知乎客户端
            client = await self._get_zhihu_client()
            
            # 构建搜索关键词
            search_keyword = " ".join(keywords)
            
            # 获取搜索类型
            search_type = self._map_search_type(self.search_type)
            
            # 计算需要爬取的页数
            items_per_page = max(max_count // self.max_pages, 5)  # 每页至少5条
            pages_needed = min((max_count + items_per_page - 1) // items_per_page, self.max_pages)
            
            self.logger.info("Starting zhihu search",
                           keyword=search_keyword,
                           search_type=self.search_type,
                           max_pages=pages_needed)
            
            all_results = []
            
            for page in range(1, pages_needed + 1):
                try:
                    # 请求间延迟
                    if page > 1:
                        await self._delay_between_requests()
                    
                    # 调用客户端搜索
                    page_results = await client.get_note_by_keyword(
                        keyword=search_keyword,
                        page=page,
                        search_type=search_type
                    )
                    
                    if page_results and 'data' in page_results:
                        page_data = self._parse_search_response(page_results)
                        all_results.extend(page_data)
                        
                        self.logger.info("Zhihu search page completed",
                                       page=page,
                                       results_count=len(page_data))
                        
                        # 检查是否已获得足够结果
                        if len(all_results) >= max_count:
                            break
                    else:
                        self.logger.warning("No data in page response", page=page)
                        
                except Exception as e:
                    self.logger.error("Failed to process page", page=page, error=str(e))
                    continue
            
            # 限制结果数量
            limited_results = all_results[:max_count]
            
            self.logger.info("Zhihu search completed",
                           total_results=len(limited_results))
            
            return limited_results
            
        except Exception as e:
            self.logger.error("Execute crawl failed", error=str(e))
            raise
    
    def _parse_search_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析知乎搜索响应"""
        try:
            results = []
            data = response.get('data', [])
            
            if isinstance(data, list):
                for item in data:
                    # 知乎搜索结果可能包含多种类型的内容
                    if self._is_valid_content_item(item):
                        processed_item = self._process_content_item(item)
                        if processed_item:
                            results.append(processed_item)
            
            return results
            
        except Exception as e:
            self.logger.error("Failed to parse search response", error=str(e))
            return []
    
    def _is_valid_content_item(self, item: Dict[str, Any]) -> bool:
        """检查是否为有效的内容项"""
        # 必须包含基本字段
        if not item.get('id') or not item.get('type'):
            return False
        
        # 支持的内容类型
        valid_types = ['answer', 'article', 'pin', 'question']
        return item.get('type') in valid_types
    
    def _process_content_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理单个内容项"""
        try:
            content_type = item.get('type')
            
            if content_type == 'answer':
                return self._process_answer_item(item)
            elif content_type == 'article':
                return self._process_article_item(item)
            elif content_type == 'pin':
                return self._process_pin_item(item)  # 想法
            elif content_type == 'question':
                return self._process_question_item(item)
            else:
                self.logger.warning("Unknown content type", type=content_type)
                return None
                
        except Exception as e:
            self.logger.error("Failed to process content item", error=str(e))
            return None
    
    def _process_answer_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """处理回答类型内容"""
        return {
            'id': item.get('id'),
            'type': 'answer',
            'content': item.get('content', ''),
            'author': item.get('author', {}),
            'question': item.get('question', {}),
            'created_time': item.get('created_time', 0),
            'voteup_count': item.get('voteup_count', 0),
            'comment_count': item.get('comment_count', 0),
            'updated_time': item.get('updated_time', 0),
            'url': item.get('url', '')
        }
    
    def _process_article_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """处理文章类型内容"""
        return {
            'id': item.get('id'),
            'type': 'article',
            'title': item.get('title', ''),
            'content': item.get('content', ''),
            'author': item.get('author', {}),
            'created_time': item.get('created_time', 0),
            'voteup_count': item.get('voteup_count', 0),
            'comment_count': item.get('comment_count', 0),
            'url': item.get('url', '')
        }
    
    def _process_pin_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """处理想法类型内容"""
        return {
            'id': item.get('id'),
            'type': 'pin',
            'content': item.get('content', ''),
            'author': item.get('author', {}),
            'created_time': item.get('created_time', 0),
            'like_count': item.get('like_count', 0),
            'comment_count': item.get('comment_count', 0),
            'url': item.get('url', '')
        }
    
    def _process_question_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """处理问题类型内容"""
        return {
            'id': item.get('id'),
            'type': 'question',
            'title': item.get('title', ''),
            'content': item.get('detail', ''),  # 问题描述
            'author': item.get('author', {}),
            'created_time': item.get('created_time', 0),
            'answer_count': item.get('answer_count', 0),
            'follower_count': item.get('follower_count', 0),
            'url': item.get('url', '')
        }
    
    def _convert_to_raw_content(self, zhihu_data: Dict[str, Any]) -> RawContent:
        """将知乎数据转换为统一的RawContent格式"""
        try:
            content_type_map = {
                'answer': ContentType.ANSWER,
                'article': ContentType.ARTICLE,
                'pin': ContentType.POST,  # 想法映射为POST
                'question': ContentType.QUESTION
            }
            
            content_type = content_type_map.get(
                zhihu_data.get('type'), 
                ContentType.POST
            )
            
            # 清理HTML标签
            content_text = self._clean_html_content(zhihu_data.get('content', ''))
            
            # 处理标题
            title = ""
            if zhihu_data.get('title'):
                title = zhihu_data['title']
            elif zhihu_data.get('question', {}).get('title'):
                title = zhihu_data['question']['title']
            
            # 处理作者信息
            author = zhihu_data.get('author', {})
            author_name = author.get('name', '')
            author_id = author.get('id', '')
            
            # 处理时间
            publish_time = None
            if zhihu_data.get('created_time'):
                publish_time = datetime.fromtimestamp(zhihu_data['created_time'])
            
            # 处理互动数据
            like_count = zhihu_data.get('voteup_count', 0) or zhihu_data.get('like_count', 0)
            comment_count = zhihu_data.get('comment_count', 0)
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
                author_name=author_name,
                author_id=author_id,
                publish_time=publish_time,
                like_count=like_count,
                comment_count=comment_count,
                share_count=share_count,
                source_url=source_url,
                hashtags=hashtags,
                image_urls=[],  # 知乎图片需要特殊处理，暂时留空
                metadata={
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
            if content.metadata and content.metadata.get('professional_score', 0) < 0.3:
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
    
    def _map_search_type(self, search_type_str: str):
        """映射搜索类型字符串到枚举"""
        # 尝试导入SearchType
        modules = self._import_mediacrawler_modules()
        
        if modules and 'SearchType' in modules:
            SearchType = modules['SearchType']
            type_mapping = {
                "综合": SearchType.GENERAL,
                "问题": SearchType.QUESTION,
                "回答": SearchType.ANSWER,
                "文章": SearchType.ARTICLE,
                "想法": SearchType.PIN
            }
            return type_mapping.get(search_type_str, SearchType.GENERAL)
        else:
            # 如果MediaCrawler不可用，使用简化的字符串映射
            type_mapping = {
                "综合": "general",
                "问题": "question",
                "回答": "answer",
                "文章": "article",
                "想法": "pin"
            }
            return type_mapping.get(search_type_str, "general")
    
    async def _delay_between_requests(self):
        """请求间延迟"""
        import asyncio
        delay = 60 / self.rate_limit  # 根据速率限制计算延迟
        await asyncio.sleep(delay)
    
    async def _check_login_status(self) -> bool:
        """检查知乎登录状态"""
        try:
            # 检查Cookie是否配置
            if not self.cookie:
                return False
            
            # 通过发送简单API请求验证Cookie有效性
            import httpx
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Cookie": self.cookie,
                "Origin": "https://www.zhihu.com",
                "Referer": "https://www.zhihu.com/",
                "Accept": "application/json, text/plain, */*",
            }
            
            # 使用知乎的配置接口验证
            url = "https://www.zhihu.com/api/v4/me"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        # 如果返回用户信息，说明Cookie有效
                        if 'id' in result:
                            self.logger.info("Cookie validation successful")
                            return True
                    except:
                        pass
                
                # 如果状态码是401，Cookie无效
                if response.status_code == 401:
                    self.logger.warning("Cookie appears to be invalid or expired")
                    return False
                elif response.status_code == 403:
                    self.logger.warning("Cookie requires verification")
                    return False
                
                # 其他错误情况，可能是网络问题，暂时认为Cookie有效
                self.logger.warning(f"Cookie validation uncertain, status: {response.status_code}")
                return True
            
        except Exception as e:
            self.logger.error("Login status check failed", error=str(e))
            # 网络错误等情况下，暂时认为Cookie有效，让后续操作来验证
            return True
    
    async def _get_zhihu_client(self):
        """获取知乎客户端实例 - 客户端工厂方法"""
        if self._crawler is None:
            self.logger.info(f"Creating Zhihu client with login method: {self.login_method}")
            
            # 优先尝试Cookie登录
            if self.login_method == "cookie" and self.cookie:
                self.logger.info("Using SimplifiedZhihuClient with cookie authentication")
                self._crawler = SimplifiedZhihuClient(
                    cookie=self.cookie,
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    logger=self.logger
                )
            elif self.login_method == "qrcode" or not self.cookie:
                # 当明确指定二维码模式，或Cookie未配置时，使用二维码登录
                try:
                    from crawler.clients.browser_zhihu_client import BrowserZhihuClient
                    
                    if not self.cookie:
                        self.logger.info("Cookie not configured, falling back to QR code login")
                    else:
                        self.logger.info("QR code login explicitly requested")
                        
                    self.logger.info("Initializing BrowserZhihuClient for QR code login")
                    self._crawler = BrowserZhihuClient(
                        mediacrawler_path=self._mediacrawler_path,
                        headless=self.headless,
                        logger=self.logger
                    )
                    
                    # 初始化并登录
                    await self._crawler.initialize()
                    await self._crawler.login_with_qrcode()
                    
                    self.logger.info("BrowserZhihuClient initialized and logged in successfully")
                    
                except ImportError as e:
                    self.logger.error(f"Failed to import BrowserZhihuClient: {e}")
                    if self.cookie:
                        self.logger.info("Falling back to SimplifiedZhihuClient with available cookie")
                        self._crawler = SimplifiedZhihuClient(
                            cookie=self.cookie,
                            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                            logger=self.logger
                        )
                    else:
                        raise PlatformError(
                            platform=self.platform_name.value,
                            message="No authentication method available: Cookie not configured and QR code login failed",
                            error_code="AUTH_UNAVAILABLE"
                        )
                except Exception as e:
                    self.logger.error(f"Failed to initialize BrowserZhihuClient: {e}")
                    if self.cookie:
                        self.logger.info("Falling back to SimplifiedZhihuClient with available cookie")
                        self._crawler = SimplifiedZhihuClient(
                            cookie=self.cookie,
                            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                            logger=self.logger
                        )
                    else:
                        raise PlatformError(
                            platform=self.platform_name.value,
                            message=f"Authentication failed: {str(e)}",
                            error_code="AUTH_FAILED"
                        )
            else:
                # 默认降级到Cookie模式
                self.logger.info("Using SimplifiedZhihuClient as default")
                self._crawler = SimplifiedZhihuClient(
                    cookie=self.cookie or "",
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    logger=self.logger
                )
                
        return self._crawler


class SimplifiedZhihuClient:
    """
    简化的知乎客户端
    不依赖浏览器环境，只使用HTTP请求
    """
    
    def __init__(self, cookie: str, user_agent: str, logger):
        self.cookie = cookie
        self.user_agent = user_agent
        self.logger = logger
        self._host = "https://www.zhihu.com"
    
    async def get_note_by_keyword(self, keyword: str, page: int = 1, search_type=None) -> Dict:
        """根据关键词搜索知乎内容"""
        try:
            import httpx
            
            # 构建搜索类型参数
            search_type_value = getattr(search_type, 'value', 'general') if search_type else 'general'
            
            # 知乎搜索API
            url = f"{self._host}/api/v4/search_v3"
            params = {
                "t": search_type_value,
                "q": keyword,
                "correction": "1",
                "offset": (page - 1) * 20,
                "limit": "20",
                "lc_idx": str(page),
                "show_all_topics": "0"
            }
            
            headers = {
                "User-Agent": self.user_agent,
                "Cookie": self.cookie,
                "Origin": self._host,
                "Referer": f"{self._host}/search?type=content&q={keyword}",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "x-requested-with": "fetch"
            }
            
            self.logger.info("Making zhihu search request",
                           keyword=keyword,
                           page=page,
                           search_type=search_type_value,
                           url=url)
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params, headers=headers)
                
                self.logger.info("Zhihu search request completed",
                               status_code=response.status_code,
                               has_data=len(response.text) > 0)
                
                if response.status_code == 200:
                    result = response.json()
                    return result
                else:
                    self.logger.warning("Search request failed",
                                      status_code=response.status_code,
                                      response_text=response.text[:200])
                    return {}
                    
        except Exception as e:
            self.logger.error("Search request failed", error=str(e))
            raise