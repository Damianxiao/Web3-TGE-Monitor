"""
MediaCrawler知乎客户端适配器
将MediaCrawler的ZhihuClient适配到我们的系统
"""
import asyncio
import sys
import os
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
    """MediaCrawler知乎客户端适配器"""
    
    def __init__(self, cookie: str, logger=None):
        self.cookie = cookie
        self.logger = logger or structlog.get_logger()
        self._client = None
        self._available = self._initialize_client()
    
    def _initialize_client(self) -> bool:
        """初始化MediaCrawler客户端"""
        try:
            # 尝试导入MediaCrawler核心模块
            from constant.zhihu import ZHIHU_URL as MC_ZHIHU_URL
            
            # 检查常量是否匹配
            if MC_ZHIHU_URL != ZHIHU_URL:
                self.logger.warning("MediaCrawler zhihu URL mismatch")
            
            self.logger.info("MediaCrawler constants loaded successfully")
            
        except ImportError as e:
            self.logger.warning(f"MediaCrawler modules not available: {e}, using fallback")
        except Exception as e:
            self.logger.warning(f"MediaCrawler import error: {e}, using fallback")
        
        # 创建简化的客户端（无论MediaCrawler是否可用）
        try:
            self._client = SimplifiedZhihuClient(
                cookie=self.cookie,
                logger=self.logger
            )
            
            self.logger.info("MediaCrawler ZhiHu adapter initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize adapter client: {e}")
            return False
    
    async def search_by_keyword(
        self, 
        keyword: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """使用关键词搜索"""
        if not self._client:
            raise Exception("MediaCrawler client not available")
        
        try:
            # 调用简化客户端的搜索方法
            results = await self._client.search_content(
                keyword=keyword,
                page=page,
                page_size=page_size
            )
            
            self.logger.info(f"MediaCrawler search completed: {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"MediaCrawler search failed: {e}")
            raise
    
    async def ping(self) -> bool:
        """检查客户端连接状态"""
        if not self._available or not self._client:
            return False
        
        try:
            return await self._client.ping()
        except Exception as e:
            self.logger.error(f"MediaCrawler ping failed: {e}")
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
        """搜索知乎内容"""
        try:
            import httpx
            import urllib.parse
            import time
            import random
            
            # URL编码关键词避免中文字符问题
            encoded_keyword = urllib.parse.quote(keyword)
            
            # 使用知乎的实际搜索API
            url = f"{self._base_url}/api/v4/search_v3"
            
            # 构建请求参数 - 更完整的参数
            offset = (page - 1) * page_size
            params = {
                "t": "general",
                "q": keyword,
                "correction": "1",
                "offset": str(offset),
                "limit": str(min(page_size, 20)),  # 知乎API限制
                "lc_idx": str(offset),
                "show_all_topics": "0",
                "search_hash_id": "",
                "vertical_info": ""
            }
            
            # 提取XSRF token
            xsrf_token = self._extract_xsrf_token()
            
            # 构建更完整的请求头
            headers = {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Cookie": self.cookie,
                "Host": "www.zhihu.com",
                "Pragma": "no-cache",
                "Referer": f"{self._base_url}/search?type=content&q={encoded_keyword}",
                "Sec-Ch-Ua": '"Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
                "X-Api-Version": "3.0.91",
                "X-App-Za": "OS=Web",
                "X-Requested-With": "fetch"
            }
            
            if xsrf_token:
                headers["X-Xsrftoken"] = xsrf_token
                headers["X-Zse-93"] = "101_3_3.0"
                
            self.logger.info(f"Searching zhihu for keyword: {keyword}, offset: {offset}")
            
            # 添加随机延迟避免过快请求
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # 发送请求
            async with httpx.AsyncClient(
                timeout=30.0, 
                verify=False,
                follow_redirects=True
            ) as client:
                response = await client.get(url, params=params, headers=headers)
                
                self.logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        
                        # 检查是否有错误信息
                        if 'error' in result:
                            self.logger.warning(f"API returned error: {result['error']}")
                            return []
                        
                        data = result.get('data', [])
                        self.logger.info(f"Raw data count: {len(data)}")
                        
                        # 转换为我们期望的格式
                        converted_results = []
                        for i, item in enumerate(data):
                            try:
                                converted_item = self._convert_search_result(item)
                                if converted_item:
                                    converted_results.append(converted_item)
                                    self.logger.debug(f"Converted item {i}: {converted_item.get('type', 'unknown')}")
                            except Exception as e:
                                self.logger.warning(f"Failed to convert item {i}: {e}")
                                continue
                        
                        self.logger.info(f"Successfully parsed {len(converted_results)} results")
                        return converted_results
                        
                    except Exception as e:
                        self.logger.error(f"Failed to parse response: {e}")
                        # 输出响应内容以便调试
                        self.logger.debug(f"Response text: {response.text[:500]}")
                        return []
                elif response.status_code == 403:
                    self.logger.warning("Access forbidden (403) - Anti-crawling detected or cookie invalid")
                    return []
                elif response.status_code == 401:
                    self.logger.warning("Unauthorized (401) - Authentication required")
                    return []
                elif response.status_code == 429:
                    self.logger.warning("Rate limited (429) - Too many requests")
                    return []
                else:
                    self.logger.warning(f"Search request failed with status: {response.status_code}")
                    self.logger.debug(f"Response: {response.text[:300]}")
                    return []
                    
        except UnicodeEncodeError as e:
            self.logger.error(f"Unicode encoding error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Search request error: {e}")
            return []  # 返回空列表而不是抛出异常
    
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
            # 获取基本信息
            content_type = item.get('type', 'unknown')
            content_id = item.get('id', '')
            
            # 根据类型提取不同的字段
            if content_type == 'answer':
                return self._convert_answer_result(item)
            elif content_type == 'article':
                return self._convert_article_result(item)
            elif content_type == 'question':
                return self._convert_question_result(item)
            elif content_type == 'pin':
                return self._convert_pin_result(item)
            else:
                # 通用转换
                return self._convert_generic_result(item)
                
        except Exception as e:
            self.logger.warning(f"Failed to convert search result: {e}")
            return None
    
    def _convert_answer_result(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """转换回答类型结果"""
        return {
            'id': item.get('id', ''),
            'type': 'answer',
            'content': item.get('content', ''),
            'title': item.get('question', {}).get('title', ''),
            'url': item.get('url', ''),
            'created_time': item.get('created_time', 0),
            'updated_time': item.get('updated_time', 0),
            'voteup_count': item.get('voteup_count', 0),
            'comment_count': item.get('comment_count', 0),
            'author': {
                'id': item.get('author', {}).get('id', ''),
                'name': item.get('author', {}).get('name', ''),
                'headline': item.get('author', {}).get('headline', ''),
                'follower_count': item.get('author', {}).get('follower_count', 0)
            }
        }
    
    def _convert_article_result(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """转换文章类型结果"""
        return {
            'id': item.get('id', ''),
            'type': 'article',
            'content': item.get('content', ''),
            'title': item.get('title', ''),
            'url': item.get('url', ''),
            'created_time': item.get('created_time', 0),
            'updated_time': item.get('updated_time', 0),
            'voteup_count': item.get('voteup_count', 0),
            'comment_count': item.get('comment_count', 0),
            'author': {
                'id': item.get('author', {}).get('id', ''),
                'name': item.get('author', {}).get('name', ''),
                'headline': item.get('author', {}).get('headline', ''),
                'follower_count': item.get('author', {}).get('follower_count', 0)
            }
        }
    
    def _convert_question_result(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """转换问题类型结果"""
        return {
            'id': item.get('id', ''),
            'type': 'question',
            'content': item.get('detail', ''),
            'title': item.get('title', ''),
            'url': item.get('url', ''),
            'created_time': item.get('created_time', 0),
            'updated_time': item.get('updated_time', 0),
            'voteup_count': 0,  # 问题没有点赞
            'comment_count': item.get('answer_count', 0),  # 用回答数替代评论数
            'author': {
                'id': item.get('author', {}).get('id', ''),
                'name': item.get('author', {}).get('name', ''),
                'headline': item.get('author', {}).get('headline', ''),
                'follower_count': item.get('author', {}).get('follower_count', 0)
            }
        }
    
    def _convert_pin_result(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """转换想法类型结果"""
        return {
            'id': item.get('id', ''),
            'type': 'pin',
            'content': item.get('content', ''),
            'title': '',  # 想法通常没有标题
            'url': item.get('url', ''),
            'created_time': item.get('created_time', 0),
            'updated_time': item.get('updated_time', 0),
            'voteup_count': item.get('like_count', 0),  # 想法用like_count
            'comment_count': item.get('comment_count', 0),
            'author': {
                'id': item.get('author', {}).get('id', ''),
                'name': item.get('author', {}).get('name', ''),
                'headline': item.get('author', {}).get('headline', ''),
                'follower_count': item.get('author', {}).get('follower_count', 0)
            }
        }
    
    def _convert_generic_result(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """通用结果转换"""
        return {
            'id': item.get('id', ''),
            'type': item.get('type', 'unknown'),
            'content': item.get('content', ''),
            'title': item.get('title', ''),
            'url': item.get('url', ''),
            'created_time': item.get('created_time', 0),
            'updated_time': item.get('updated_time', 0),
            'voteup_count': item.get('voteup_count', 0) or item.get('like_count', 0),
            'comment_count': item.get('comment_count', 0),
            'author': {
                'id': item.get('author', {}).get('id', ''),
                'name': item.get('author', {}).get('name', ''),
                'headline': item.get('author', {}).get('headline', ''),
                'follower_count': item.get('author', {}).get('follower_count', 0)
            }
        }
    
    async def ping(self) -> bool:
        """检查连接状态"""
        try:
            import httpx
            
            # 简单的健康检查请求
            url = f"{self._base_url}/api/v4/me"
            headers = {
                "Cookie": self.cookie,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                # 200表示成功，401表示未登录但服务可用，403表示需要验证但服务可用
                return response.status_code in [200, 401, 403]
                
        except Exception as e:
            self.logger.error(f"Ping failed: {e}")
            return False