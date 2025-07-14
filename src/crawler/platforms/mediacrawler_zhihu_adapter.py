"""
MediaCrawler知乎客户端适配器 - 完整集成版本
使用Playwright浏览器自动化 + JS签名算法实现真正的MediaCrawler集成
"""
import asyncio
import sys
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

# 添加mediacrawler路径
mediacrawler_path = os.getenv("MEDIACRAWLER_PATH", "../MediaCrawler")
if mediacrawler_path not in sys.path:
    sys.path.insert(0, mediacrawler_path)

from crawler.platforms.zhihu_constants import (
    ZHIHU_URL, ZHIHU_ZHUANLAN_URL, 
    ANSWER_NAME, ARTICLE_NAME, VIDEO_NAME
)

logger = structlog.get_logger()


class MediaCrawlerZhihuAdapter:
    """MediaCrawler知乎客户端适配器 - 完整版本"""
    
    def __init__(self, cookie: str, logger=None):
        self.cookie = cookie
        self.logger = logger or structlog.get_logger()
        self._client = None
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._available = False
        
    async def initialize(self) -> bool:
        """初始化Playwright浏览器和MediaCrawler客户端"""
        try:
            # 尝试导入MediaCrawler模块 (优雅降级)
            mc_available = await self._check_mediacrawler_availability()
            
            if mc_available:
                return await self._initialize_full_mediacrawler()
            else:
                return await self._initialize_fallback_client()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize adapter: {e}")
            return False
    
    async def _check_mediacrawler_availability(self) -> bool:
        """检查MediaCrawler模块可用性"""
        try:
            # 检查关键文件存在
            zhihu_js_path = os.path.join(os.getcwd(), "libs", "zhihu.js")
            if not os.path.exists(zhihu_js_path):
                self.logger.warning("zhihu.js signature file not found")
                return False
            
            # 尝试导入MediaCrawler常量
            from constant.zhihu import ZHIHU_URL as MC_ZHIHU_URL
            self.logger.info("MediaCrawler modules available")
            return True
            
        except ImportError as e:
            self.logger.warning(f"MediaCrawler modules not available: {e}")
            return False
        except Exception as e:
            self.logger.warning(f"MediaCrawler check failed: {e}")
            return False
    
    async def _initialize_full_mediacrawler(self) -> bool:
        """初始化完整的MediaCrawler集成"""
        try:
            from playwright.async_api import async_playwright
            
            self.logger.info("Initializing full MediaCrawler integration with Playwright")
            
            # 启动Playwright
            self._playwright = await async_playwright().start()
            
            # 启动浏览器 (使用chromium以获得最佳兼容性)
            self._browser = await self._playwright.chromium.launch(
                headless=True,  # 无头模式以减少资源消耗
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # 创建浏览器上下文
            self._context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            
            # 添加Cookie
            if self.cookie:
                cookies = self._parse_cookie_string(self.cookie)
                await self._context.add_cookies(cookies)
            
            # 创建页面
            self._page = await self._context.new_page()
            
            # 创建MediaCrawler风格的客户端
            self._client = FullMediaCrawlerClient(
                page=self._page,
                context=self._context,
                cookie=self.cookie,
                logger=self.logger
            )
            
            self._available = True
            self.logger.info("Full MediaCrawler integration initialized successfully")
            return True
            
        except ImportError as e:
            self.logger.warning(f"Playwright not available: {e}, falling back to simplified client")
            return await self._initialize_fallback_client()
        except Exception as e:
            self.logger.error(f"Failed to initialize full MediaCrawler: {e}")
            return await self._initialize_fallback_client()
    
    async def _initialize_fallback_client(self) -> bool:
        """初始化降级客户端"""
        try:
            self.logger.info("Initializing fallback simplified client")
            
            self._client = SimplifiedZhihuClient(
                cookie=self.cookie,
                logger=self.logger
            )
            
            self._available = True
            self.logger.info("Fallback client initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize fallback client: {e}")
            return False
    
    def _parse_cookie_string(self, cookie_string: str) -> List[Dict[str, Any]]:
        """解析Cookie字符串为Playwright格式"""
        cookies = []
        for item in cookie_string.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies.append({
                    'name': key,
                    'value': value,
                    'domain': '.zhihu.com',
                    'path': '/'
                })
        return cookies
    
    async def search_by_keyword(
        self, 
        keyword: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """使用关键词搜索"""
        if not self._available or not self._client:
            raise Exception("MediaCrawler adapter not initialized")
        
        try:
            return await self._client.search_content(
                keyword=keyword,
                page=page,
                page_size=page_size
            )
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            raise
    
    async def ping(self) -> bool:
        """检查客户端连接状态"""
        if not self._available or not self._client:
            return False
        
        try:
            return await self._client.ping()
        except Exception as e:
            self.logger.error(f"Ping failed: {e}")
            return False
    
    async def close(self):
        """清理资源"""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")


class FullMediaCrawlerClient:
    """完整的MediaCrawler客户端实现"""
    
    def __init__(self, page, context, cookie: str, logger):
        self.page = page
        self.context = context
        self.cookie = cookie
        self.logger = logger
        self._signature_client = None
        self._init_signature_client()
    
    def _init_signature_client(self):
        """初始化JS签名客户端"""
        try:
            import execjs
            
            zhihu_js_path = os.path.join(os.getcwd(), "libs", "zhihu.js")
            if os.path.exists(zhihu_js_path):
                with open(zhihu_js_path, 'r', encoding='utf-8') as f:
                    js_code = f.read()
                self._signature_client = execjs.compile(js_code)
                self.logger.info("JS signature client initialized")
            else:
                self.logger.warning("zhihu.js not found, signature features disabled")
                
        except ImportError:
            self.logger.warning("execjs not available, signature features disabled")
        except Exception as e:
            self.logger.warning(f"Failed to initialize signature client: {e}")
    
    async def search_content(
        self, 
        keyword: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索知乎内容 - 使用Playwright浏览器请求"""
        try:
            # 构建搜索URL
            offset = (page - 1) * page_size
            base_url = "https://www.zhihu.com/api/v4/search_v3"
            
            # 使用MediaCrawler的完整参数集
            params = {
                "gk_version": "gz-gaokao",
                "t": "general",
                "q": keyword,
                "correction": "1",
                "offset": str(offset),
                "limit": str(min(page_size, 20)),
                "filter_fields": "",
                "lc_idx": str(offset),
                "show_all_topics": "0",
                "search_source": "Filter",
                "time_interval": "0",  # SearchTime.DEFAULT
                "sort": "default",     # SearchSort.DEFAULT  
                "vertical": "default"  # SearchType.DEFAULT
            }
            
            # 构建查询字符串
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{base_url}?{query_string}"
            
            # 生成签名头
            headers = await self._generate_signed_headers(full_url)
            
            self.logger.info(f"Searching with Playwright: {keyword}")
            self.logger.debug(f"Request URL: {full_url}")
            
            # 使用Playwright进行请求
            response = await self.page.request.get(
                full_url,
                headers=headers
            )
            
            self.logger.info(f"Response status: {response.status}")
            
            if response.status == 200:
                data = await response.json()
                
                # 检查API错误
                if 'error' in data:
                    self.logger.error(f"API返回错误: {data['error']}")
                    return []
                
                results = data.get('data', [])
                
                # 转换结果格式
                converted_results = []
                for item in results:
                    converted_item = self._convert_search_result(item)
                    if converted_item:
                        converted_results.append(converted_item)
                
                self.logger.info(f"Successfully retrieved {len(converted_results)} results")
                return converted_results
            else:
                response_text = await response.text()
                self.logger.warning(f"Search request failed with status: {response.status}")
                self.logger.debug(f"Response: {response_text[:300]}")
                return []
                
        except Exception as e:
            self.logger.error(f"Playwright search failed: {e}")
            return []
    
    async def _generate_signed_headers(self, url: str) -> Dict[str, str]:
        """生成带签名的请求头"""
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Cookie": self.cookie,
            "Host": "www.zhihu.com",
            "Pragma": "no-cache",
            "Referer": "https://www.zhihu.com/search?type=content",
            "Sec-Ch-Ua": '"Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "X-Api-Version": "3.0.91",
            "X-App-Za": "OS=Web"
        }
        
        # 添加XSRF token
        xsrf_token = self._extract_xsrf_token()
        if xsrf_token:
            headers["X-Xsrftoken"] = xsrf_token
        
        # 如果有签名客户端，生成签名
        if self._signature_client:
            try:
                sign_result = self._signature_client.call("get_sign", url, self.cookie)
                headers["x-zst-81"] = sign_result.get("x-zst-81", "")
                headers["x-zse-96"] = sign_result.get("x-zse-96", "")
                self.logger.debug("Generated signature headers")
            except Exception as e:
                self.logger.warning(f"Failed to generate signature: {e}")
        
        return headers
    
    def _extract_xsrf_token(self) -> str:
        """从Cookie中提取XSRF token"""
        if '_xsrf=' in self.cookie:
            for part in self.cookie.split(';'):
                if '_xsrf=' in part:
                    return part.split('=')[1].strip()
        return ""
    
    def _convert_search_result(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """转换搜索结果到统一格式"""
        try:
            content_type = item.get('type', 'unknown')
            
            # 统一的转换逻辑
            return {
                'id': item.get('id', ''),
                'type': content_type,
                'content': item.get('content', ''),
                'title': self._extract_title(item, content_type),
                'url': item.get('url', ''),
                'created_time': item.get('created_time', 0),
                'updated_time': item.get('updated_time', 0),
                'voteup_count': item.get('voteup_count', 0) or item.get('like_count', 0),
                'comment_count': item.get('comment_count', 0) or item.get('answer_count', 0),
                'author': {
                    'id': item.get('author', {}).get('id', ''),
                    'name': item.get('author', {}).get('name', ''),
                    'headline': item.get('author', {}).get('headline', ''),
                    'follower_count': item.get('author', {}).get('follower_count', 0)
                }
            }
        except Exception as e:
            self.logger.warning(f"Failed to convert search result: {e}")
            return None
    
    def _extract_title(self, item: Dict[str, Any], content_type: str) -> str:
        """根据内容类型提取标题"""
        if content_type == 'answer':
            return item.get('question', {}).get('title', '')
        elif content_type in ['article', 'question']:
            return item.get('title', '')
        else:
            return item.get('title', '')
    
    async def ping(self) -> bool:
        """检查连接状态"""
        try:
            response = await self.page.request.get(
                "https://www.zhihu.com/api/v4/me",
                headers={"Cookie": self.cookie}
            )
            return response.status in [200, 401, 403]  # 这些状态码表示服务可达
        except Exception as e:
            self.logger.error(f"Ping failed: {e}")
            return False


class SimplifiedZhihuClient:
    """简化的知乎客户端，专注于搜索功能"""
    
    def __init__(self, cookie: str, logger):
        self.cookie = cookie
        self.logger = logger
        self._base_url = ZHIHU_URL
        
    async def search_content(
        self, 
        keyword: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索知乎内容 - 简化版本"""
        try:
            import httpx
            import urllib.parse
            import random
            
            # URL编码关键词
            encoded_keyword = urllib.parse.quote(keyword)
            
            # 构建搜索URL
            url = f"{self._base_url}/api/v4/search_v3"
            
            # 构建请求参数
            offset = (page - 1) * page_size
            params = {
                "t": "general",
                "q": keyword,
                "correction": "1",
                "offset": str(offset),
                "limit": str(min(page_size, 20)),
                "lc_idx": str(offset)
            }
            
            # 构建请求头
            headers = {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cookie": self.cookie,
                "Host": "www.zhihu.com",
                "Referer": f"{self._base_url}/search?type=content&q={encoded_keyword}",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "X-Requested-With": "fetch"
            }
            
            # 添加XSRF token
            xsrf_token = self._extract_xsrf_token()
            if xsrf_token:
                headers["X-Xsrftoken"] = xsrf_token
            
            self.logger.info(f"Simplified search for: {keyword}")
            
            # 添加随机延迟
            await asyncio.sleep(random.uniform(1, 3))
            
            # 发送请求
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        data = result.get('data', [])
                        
                        converted_results = []
                        for item in data:
                            converted_item = self._convert_search_result(item)
                            if converted_item:
                                converted_results.append(converted_item)
                        
                        return converted_results
                    except Exception as e:
                        self.logger.error(f"Failed to parse response: {e}")
                        return []
                else:
                    self.logger.warning(f"Request failed with status: {response.status_code}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Simplified search failed: {e}")
            return []
    
    def _extract_xsrf_token(self) -> str:
        """从Cookie中提取XSRF token"""
        if '_xsrf=' in self.cookie:
            for part in self.cookie.split(';'):
                if '_xsrf=' in part:
                    return part.split('=')[1].strip()
        return ""
    
    def _convert_search_result(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """转换搜索结果"""
        try:
            content_type = item.get('type', 'unknown')
            
            return {
                'id': item.get('id', ''),
                'type': content_type,
                'content': item.get('content', ''),
                'title': item.get('title', '') or item.get('question', {}).get('title', ''),
                'url': item.get('url', ''),
                'created_time': item.get('created_time', 0),
                'updated_time': item.get('updated_time', 0),
                'voteup_count': item.get('voteup_count', 0) or item.get('like_count', 0),
                'comment_count': item.get('comment_count', 0),
                'author': item.get('author', {})
            }
        except Exception as e:
            self.logger.warning(f"Failed to convert result: {e}")
            return None
    
    async def ping(self) -> bool:
        """检查连接状态"""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self._base_url}/api/v4/me",
                    headers={"Cookie": self.cookie}
                )
                return response.status_code in [200, 401, 403]
        except Exception:
            return False