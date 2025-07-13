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

from crawler.base_platform import AbstractPlatform, PlatformError
from crawler.models import RawContent, Platform, ContentType

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
        self.cookie = os.getenv("WEIBO_COOKIE", "")
        self.login_method = os.getenv("WEIBO_LOGIN_METHOD", "cookie")
        self.headless = os.getenv("WEIBO_HEADLESS", "true").lower() == "true"
        
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
            
            # 导入微博相关模块
            from media_platform.weibo.client import WeiboClient
            from media_platform.weibo.field import SearchType
            
            self._mediacrawler_modules = {
                'WeiboClient': WeiboClient,
                'SearchType': SearchType
            }
            
            self.logger.info("MediaCrawler weibo modules imported successfully")
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
        """检查微博平台是否可用"""
        try:
            # 检查Cookie配置
            if not self.cookie:
                self.logger.warning("Weibo cookie not configured")
                return False
            
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
            # 获取微博客户端
            client = await self._get_weibo_client()
            
            # 构建搜索关键词
            search_keyword = " ".join(keywords)
            
            # 计算页数
            max_pages = min(max_count // 20 + 1, self.max_pages)
            
            # 映射搜索类型
            search_type = self._map_search_type(self.search_type)
            
            self.logger.info("Starting weibo search",
                           keyword=search_keyword,
                           max_pages=max_pages,
                           search_type=self.search_type)
            
            all_results = []
            
            # 分页搜索
            for page in range(1, max_pages + 1):
                try:
                    # 执行搜索
                    response = await client.get_note_by_keyword(
                        keyword=search_keyword,
                        page=page,
                        search_type=search_type
                    )
                    
                    # 解析搜索结果
                    page_results = self._parse_search_response(response)
                    
                    if not page_results:
                        self.logger.info("No more results found", page=page)
                        break
                    
                    all_results.extend(page_results)
                    
                    # 检查是否达到最大数量
                    if len(all_results) >= max_count:
                        all_results = all_results[:max_count]
                        break
                    
                    self.logger.info("Page search completed", 
                                   page=page, 
                                   page_results=len(page_results),
                                   total_results=len(all_results))
                    
                    # 延迟避免被限流
                    await self._delay_between_requests()
                    
                except Exception as e:
                    self.logger.error("Page search failed", 
                                    page=page, 
                                    error=str(e))
                    continue
            
            self.logger.info("Weibo search completed", 
                           total_results=len(all_results))
            
            return all_results
            
        except Exception as e:
            self.logger.error("Weibo search failed", error=str(e))
            raise PlatformError(
                platform=self.platform_name.value,
                message=f"Search failed: {str(e)}",
                error_code="SEARCH_FAILED"
            )
    
    def _parse_search_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析微博搜索响应"""
        try:
            # 微博API返回的数据结构
            data = response.get('data', {})
            cards = data.get('cards', [])
            
            results = []
            for card in cards:
                # 过滤掉非微博内容卡片
                if card.get('card_type') == 9:  # 微博内容卡片
                    mblog = card.get('mblog', {})
                    if mblog:
                        results.append(mblog)
            
            return results
            
        except Exception as e:
            self.logger.error("Failed to parse search response", error=str(e))
            return []
    
    def _map_search_type(self, search_type_str: str):
        """映射搜索类型字符串到枚举"""
        # 尝试导入SearchType
        modules = self._import_mediacrawler_modules()
        
        if modules and 'SearchType' in modules:
            SearchType = modules['SearchType']
            type_mapping = {
                "综合": SearchType.DEFAULT,
                "实时": SearchType.REAL_TIME,
                "热门": SearchType.POPULAR,
                "视频": SearchType.VIDEO
            }
            return type_mapping.get(search_type_str, SearchType.DEFAULT)
        else:
            # 如果MediaCrawler不可用，使用简化的字符串映射
            type_mapping = {
                "综合": "1",
                "实时": "61", 
                "热门": "60",
                "视频": "64"
            }
            return type_mapping.get(search_type_str, "1")
    
    async def _delay_between_requests(self):
        """请求间延迟"""
        import asyncio
        delay = 60.0 / self.rate_limit  # 根据rate_limit计算延迟
        await asyncio.sleep(delay)
    
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
        pic_infos = weibo_data.get('pic_infos', {})
        image_urls = []
        if pic_infos:
            for pic_info in pic_infos.values():
                if 'url' in pic_info:
                    image_urls.append(pic_info['url'])
        
        # 如果pic_infos为空，尝试从pic_urls获取
        if not image_urls:
            pic_urls = weibo_data.get('pic_urls', [])
            if isinstance(pic_urls, list):
                image_urls = [url for url in pic_urls if isinstance(url, str)]
        
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
                
                # 微博特有的时间格式，如"Sat Jul 13 10:00:00 +0800 2025"
                import time
                try:
                    time_struct = time.strptime(time_value, "%a %b %d %H:%M:%S %z %Y")
                    return datetime.fromtimestamp(time.mktime(time_struct))
                except ValueError:
                    pass
                
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
            # 检查Cookie是否配置
            if not self.cookie:
                return False
            
            # 通过发送简单API请求验证Cookie有效性
            import httpx
            
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15",
                "Cookie": self.cookie,
                "Origin": "https://m.weibo.cn",
                "Referer": "https://m.weibo.cn/",
                "Accept": "application/json, text/plain, */*",
            }
            
            # 使用一个简单的验证端点
            url = "https://m.weibo.cn/api/config"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        # 如果返回正常的配置信息，说明Cookie有效
                        if 'data' in result:
                            self.logger.info("Cookie validation successful")
                            return True
                    except:
                        pass
                
                # 如果状态码是403或者其他错误，Cookie可能无效
                if response.status_code == 403:
                    self.logger.warning("Cookie appears to be invalid or expired")
                    return False
                elif response.status_code == 302:
                    self.logger.warning("Cookie requires login verification")
                    return False
                
                # 其他错误情况，可能是网络问题，暂时认为Cookie有效
                self.logger.warning(f"Cookie validation uncertain, status: {response.status_code}")
                return True
            
        except Exception as e:
            self.logger.error("Login status check failed", error=str(e))
            # 网络错误等情况下，暂时认为Cookie有效，让后续操作来验证
            return True
    
    async def _get_weibo_client(self):
        """获取微博客户端实例 - 客户端工厂方法"""
        if self._crawler is None:
            self.logger.info(f"Creating Weibo client with login method: {self.login_method}")
            
            # 优先尝试Cookie登录
            if self.login_method == "cookie" and self.cookie:
                self.logger.info("Using SimplifiedWeiboClient with cookie authentication")
                self._crawler = SimplifiedWeiboClient(
                    cookie=self.cookie,
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15",
                    logger=self.logger
                )
            elif self.login_method == "qrcode" or not self.cookie:
                # 当明确指定二维码模式，或Cookie未配置时，使用二维码登录
                try:
                    from crawler.clients.browser_weibo_client import BrowserWeiboClient
                    
                    if not self.cookie:
                        self.logger.info("Cookie not configured, falling back to QR code login")
                    else:
                        self.logger.info("QR code login explicitly requested")
                        
                    self.logger.info("Initializing BrowserWeiboClient for QR code login")
                    self._crawler = BrowserWeiboClient(
                        mediacrawler_path=self._mediacrawler_path,
                        headless=self.headless,
                        logger=self.logger
                    )
                    
                    # 初始化并登录
                    await self._crawler.initialize()
                    await self._crawler.login_with_qrcode()
                    
                    self.logger.info("BrowserWeiboClient initialized and logged in successfully")
                    
                except ImportError as e:
                    self.logger.error(f"Failed to import BrowserWeiboClient: {e}")
                    if self.cookie:
                        self.logger.info("Falling back to SimplifiedWeiboClient with available cookie")
                        self._crawler = SimplifiedWeiboClient(
                            cookie=self.cookie,
                            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15",
                            logger=self.logger
                        )
                    else:
                        raise PlatformError(
                            platform=self.platform_name.value,
                            message="No authentication method available: Cookie not configured and QR code login failed",
                            error_code="AUTH_UNAVAILABLE"
                        )
                except Exception as e:
                    self.logger.error(f"Failed to initialize BrowserWeiboClient: {e}")
                    if self.cookie:
                        self.logger.info("Falling back to SimplifiedWeiboClient with available cookie")
                        self._crawler = SimplifiedWeiboClient(
                            cookie=self.cookie,
                            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15",
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
                self.logger.info("Using SimplifiedWeiboClient as default")
                self._crawler = SimplifiedWeiboClient(
                    cookie=self.cookie or "",
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15",
                    logger=self.logger
                )
                
        return self._crawler


class SimplifiedWeiboClient:
    """
    简化的微博客户端
    不依赖浏览器环境，只使用HTTP请求
    """
    
    def __init__(self, cookie: str, user_agent: str, logger):
        self.cookie = cookie
        self.user_agent = user_agent
        self.logger = logger
        self._host = "https://m.weibo.cn"
        
        # 导入httpx
        try:
            import httpx
            self.httpx = httpx
        except ImportError:
            raise ImportError("httpx is required for simplified weibo client")
    
    async def get_note_by_keyword(self, keyword: str, page: int = 1, search_type=None) -> Dict:
        """搜索微博内容"""
        try:
            # 构建搜索URL和参数
            search_type_value = getattr(search_type, 'value', '1') if search_type else '1'
            containerid = f"100103type={search_type_value}&q={keyword}"
            
            url = f"{self._host}/api/container/getIndex"
            params = {
                "containerid": containerid,
                "page_type": "searchall",
                "page": page,
            }
            
            headers = {
                "User-Agent": self.user_agent,
                "Cookie": self.cookie,
                "Origin": "https://m.weibo.cn",
                "Referer": "https://m.weibo.cn",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            
            self.logger.info("Making weibo search request", 
                           url=url, 
                           keyword=keyword, 
                           page=page)
            
            async with self.httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                
                self.logger.info("Weibo search request successful", 
                               status_code=response.status_code,
                               has_data='data' in result)
                
                return result
                
        except Exception as e:
            self.logger.error("Weibo search request failed", 
                            keyword=keyword, 
                            page=page, 
                            error=str(e))
            raise