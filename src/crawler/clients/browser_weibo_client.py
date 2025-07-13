"""
基于浏览器的微博客户端
集成MediaCrawler的完整浏览器功能，支持二维码登录
"""
import asyncio
import sys
import os
from typing import Dict, Any, Optional
import structlog

from .weibo_client_interface import WeiboClientInterface


class BrowserWeiboClient(WeiboClientInterface):
    """
    基于浏览器的微博客户端
    集成MediaCrawler的WeiboLogin和WeiboCrawler
    支持二维码登录和完整的浏览器自动化功能
    """
    
    def __init__(self, mediacrawler_path: str, headless: bool = True, logger=None):
        """
        初始化客户端
        
        Args:
            mediacrawler_path: MediaCrawler安装路径
            headless: 是否使用无头模式（二维码登录需要设为False）
            logger: 日志记录器
        """
        self.mediacrawler_path = mediacrawler_path
        self.headless = headless
        self.logger = logger or structlog.get_logger()
        
        # MediaCrawler组件
        self._weibo_crawler = None
        self._weibo_login = None
        self._browser_context = None
        self._context_page = None
        
        # 登录状态
        self._is_logged_in = False
        
    async def initialize(self):
        """初始化MediaCrawler组件"""
        try:
            # 添加MediaCrawler路径到系统路径
            if self.mediacrawler_path not in sys.path:
                sys.path.insert(0, self.mediacrawler_path)
            
            # 导入MediaCrawler组件
            from media_platform.weibo.core import WeiboCrawler
            from media_platform.weibo.login import WeiboLogin
            from playwright.async_api import async_playwright
            
            self.logger.info("Starting browser for WeiboCrawler...")
            
            # 创建Playwright实例
            self._playwright = await async_playwright().start()
            
            # 启动浏览器
            browser = await self._playwright.chromium.launch(
                headless=self.headless,
                channel="chrome"  # 使用系统Chrome
            )
            
            # 创建浏览器上下文
            self._browser_context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            
            # 创建页面
            self._context_page = await self._browser_context.new_page()
            
            # 初始化登录组件
            self._weibo_login = WeiboLogin(
                login_type="qrcode",
                browser_context=self._browser_context,
                context_page=self._context_page
            )
            
            # 初始化爬虫组件
            self._weibo_crawler = WeiboCrawler()
            
            self.logger.info("BrowserWeiboClient initialized successfully")
            
        except ImportError as e:
            self.logger.error(f"Failed to import MediaCrawler components: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize browser client: {e}")
            raise
    
    async def login_with_qrcode(self):
        """使用二维码登录"""
        try:
            if not self._weibo_login:
                await self.initialize()
            
            self.logger.info("Starting QR code login process...")
            
            # 执行二维码登录
            await self._weibo_login.begin()
            
            self._is_logged_in = True
            self.logger.info("QR code login completed successfully")
            
        except Exception as e:
            self.logger.error(f"QR code login failed: {e}")
            self._is_logged_in = False
            raise
    
    async def get_note_by_keyword(self, keyword: str, page: int = 1, search_type=None) -> Dict[str, Any]:
        """
        使用MediaCrawler完整功能搜索微博内容
        
        Args:
            keyword: 搜索关键词
            page: 页数
            search_type: 搜索类型
            
        Returns:
            包含搜索结果的字典
        """
        try:
            if not self._weibo_crawler:
                await self.initialize()
            
            if not self._is_logged_in:
                await self.login_with_qrcode()
            
            # 确保搜索类型正确
            if search_type is None:
                # 导入搜索类型枚举
                from media_platform.weibo.field import SearchType
                search_type = SearchType.GENERAL  # 默认综合搜索
            
            self.logger.info(f"Searching for keyword: {keyword}, page: {page}")
            
            # 使用MediaCrawler搜索
            results = await self._weibo_crawler.search_info_by_keyword(
                keyword=keyword,
                page=page,
                search_type=search_type
            )
            
            self.logger.info(f"Search completed, found {len(results.get('cards', []))} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            raise
    
    async def close(self):
        """关闭客户端并清理资源"""
        try:
            if self._browser_context:
                await self._browser_context.close()
                self.logger.info("Browser context closed")
            
            if hasattr(self, '_playwright') and self._playwright:
                await self._playwright.stop()
                self.logger.info("Playwright stopped")
                
        except Exception as e:
            self.logger.error(f"Error closing browser client: {e}")
    
    def __del__(self):
        """析构函数，确保资源清理"""
        if hasattr(self, '_browser_context') and self._browser_context:
            try:
                # 在事件循环中安排清理任务
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except:
                pass  # 忽略析构时的错误