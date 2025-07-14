"""
小红书平台适配器 - 整合版
直接使用项目内部的mediacrawler模块
"""
import json
import sys
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import structlog

from ..base_platform import AbstractPlatform, PlatformError, PlatformUnavailableError
from ..models import RawContent, Platform, ContentType

logger = structlog.get_logger()


class XHSPlatform(AbstractPlatform):
    """小红书平台实现 - 整合版"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # 从配置获取mediacrawler路径，确保与其他平台一致
        self.mediacrawler_path = config.get('mediacrawler_path', '') if config else ''
        if not self.mediacrawler_path:
            # 如果配置中没有路径，尝试从环境变量获取
            import os
            from pathlib import Path
            # 首先尝试使用环境变量
            env_path = os.getenv('MEDIACRAWLER_PATH')
            if env_path:
                self.mediacrawler_path = env_path
            else:
                # 最后使用默认的相对路径
                project_root = Path(__file__).parent.parent.parent.parent
                self.mediacrawler_path = str(project_root / "external" / "MediaCrawler")
        
        # 确保路径是绝对路径
        import os
        from pathlib import Path
        if not os.path.isabs(self.mediacrawler_path):
            project_root = Path(__file__).parent.parent.parent.parent
            self.mediacrawler_path = str(project_root / self.mediacrawler_path)
            
        self._xhs_client = None
        
        # 确保mediacrawler在Python路径中
        self._ensure_mediacrawler_in_path()
        
    def _ensure_mediacrawler_in_path(self):
        """确保mediacrawler路径在Python路径中"""
        if self.mediacrawler_path not in sys.path:
            sys.path.insert(0, self.mediacrawler_path)
            self.logger.info("Added mediacrawler to Python path", path=self.mediacrawler_path)
        
    def get_platform_name(self) -> Platform:
        """获取平台名称"""
        return Platform.XHS
    
    async def is_available(self) -> bool:
        """检查平台是否可用"""
        original_cwd = os.getcwd()
        try:
            # 验证mediacrawler目录结构
            mediacrawler_path = Path(self.mediacrawler_path)
            required_files = [
                mediacrawler_path / "media_platform" / "xhs" / "core.py",
                mediacrawler_path / "media_platform" / "xhs" / "client.py",
                mediacrawler_path / "base" / "base_crawler.py"
            ]
            
            for required_file in required_files:
                if not required_file.exists():
                    self.logger.error("Required file not found", file=str(required_file))
                    return False
            
            # 切换到mediacrawler目录以确保相对路径正确
            os.chdir(self.mediacrawler_path)
            
            # 尝试导入mediacrawler的XHS模块
            from media_platform.xhs import client as xhs_client
            from media_platform.xhs import core as xhs_core
            
            self.logger.info("XHS platform modules imported successfully")
            return True
            
        except Exception as e:
            self.logger.error("XHS platform not available", error=str(e))
            return False
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def _get_xhs_client(self):
        """获取XHS爬虫实例（延迟初始化）"""
        if self._xhs_client is None:
            original_cwd = os.getcwd()
            try:
                # 切换到mediacrawler目录以确保相对路径正确
                os.chdir(self.mediacrawler_path)
                
                # 导入MediaCrawler的XHS核心爬虫
                from media_platform.xhs.core import XiaoHongShuCrawler
                
                # 创建爬虫实例
                self._xhs_client = XiaoHongShuCrawler()
                
                self.logger.info("XHS crawler initialized")
                
            except Exception as e:
                self.logger.error("Failed to initialize XHS crawler", error=str(e))
                raise PlatformError("xhs", f"Failed to initialize XHS crawler: {str(e)}")
            finally:
                # 恢复原工作目录
                os.chdir(original_cwd)
        
        return self._xhs_client
    
    async def crawl(
        self, 
        keywords: List[str], 
        max_count: int = 50,
        **kwargs
    ) -> List[RawContent]:
        """
        爬取小红书内容 - 新的共享库实现
        
        Args:
            keywords: 搜索关键词列表
            max_count: 最大爬取数量
            **kwargs: 其他参数
            
        Returns:
            爬取到的内容列表
        """
        original_cwd = os.getcwd()
        original_keywords = None
        config_file_path = None
        
        try:
            # 切换到mediacrawler目录
            os.chdir(self.mediacrawler_path)
            
            # 首先修改配置文件（在任何MediaCrawler导入之前）
            try:
                import sys
                
                # 清除所有MediaCrawler相关的模块缓存
                modules_to_remove = []
                for module_name in sys.modules.keys():
                    if any(keyword in module_name for keyword in ['config', 'media_platform', 'mediacrawler']):
                        modules_to_remove.append(module_name)
                        
                for module_name in modules_to_remove:
                    del sys.modules[module_name]
                
                # 读取并修改配置文件
                config_file_path = os.path.join(self.mediacrawler_path, "config", "base_config.py")
                
                with open(config_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 查找并替换KEYWORDS行
                import re
                pattern = r'KEYWORDS\s*=\s*"([^"]*)"'
                match = re.search(pattern, content)
                
                if match:
                    original_keywords = match.group(1)
                    new_keywords = ",".join(keywords)
                    new_content = re.sub(pattern, f'KEYWORDS = "{new_keywords}"', content)
                    
                    # 写入临时修改
                    with open(config_file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    self.logger.info("Updated MediaCrawler keywords before import", 
                                   original=original_keywords, 
                                   new=new_keywords)
                else:
                    self.logger.warning("Could not find KEYWORDS pattern in config file")
                    
            except Exception as e:
                self.logger.warning("Failed to update MediaCrawler keywords", error=str(e))
            
            # 验证关键词
            validated_keywords = await self.validate_keywords(keywords)
            
            self.logger.info("Starting XHS crawl with shared library",
                           keywords=validated_keywords,
                           max_count=max_count)
            
            # 获取XHS爬虫
            crawler = await self._get_xhs_client()
            
            # 使用完整的MediaCrawler方式进行搜索
            raw_data = await self._search_with_complete_mediacrawler(validated_keywords, max_count)
            
            # 转换数据格式
            raw_contents = []
            for item in raw_data:
                try:
                    content = await self.transform_to_raw_content(item)
                    raw_contents.append(content)
                except Exception as e:
                    self.logger.warning("Failed to transform content", 
                                      content_id=item.get('note_id', 'unknown'),
                                      error=str(e))
            
            # 过滤内容
            filtered_contents = await self.filter_content(raw_contents)
            
            self.logger.info("XHS crawl completed",
                            keywords=validated_keywords,
                            raw_count=len(raw_data),
                            transformed_count=len(raw_contents),
                            filtered_count=len(filtered_contents))
            
            return filtered_contents
            
        except Exception as e:
            self.logger.error("XHS crawl failed", error=str(e))
            
            # 如果原始异常包含详细错误信息，保留它们
            if hasattr(e, 'detailed_errors'):
                platform_error = PlatformError("xhs", f"Crawl failed: {str(e)}")
                platform_error.detailed_errors = e.detailed_errors
                raise platform_error
            else:
                raise PlatformError("xhs", f"Crawl failed: {str(e)}")
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
            
            # 恢复原始关键词配置
            try:
                if original_keywords is not None and config_file_path and os.path.exists(config_file_path):
                    with open(config_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 恢复原始关键词
                    import re
                    pattern = r'KEYWORDS\s*=\s*"([^"]*)"'
                    restored_content = re.sub(pattern, f'KEYWORDS = "{original_keywords}"', content)
                    
                    with open(config_file_path, 'w', encoding='utf-8') as f:
                        f.write(restored_content)
                    
                    self.logger.info("Restored original MediaCrawler keywords", keywords=original_keywords)
            except Exception as e:
                self.logger.warning("Failed to restore original keywords", error=str(e))
    
    async def _search_with_complete_mediacrawler(self, keywords: List[str], max_count: int) -> List[Dict[str, Any]]:
        """
        使用完整的MediaCrawler方式进行搜索，完全按照MediaCrawler的原生实现
        """
        original_cwd = os.getcwd()
        try:
            # 切换到mediacrawler目录
            os.chdir(self.mediacrawler_path)
            
            # 导入完整的MediaCrawler核心模块
            from media_platform.xhs.core import XiaoHongShuCrawler
            from playwright.async_api import async_playwright
            import config
            
            self.logger.info("Starting complete MediaCrawler search", keywords=keywords, max_count=max_count)
            
            # 创建完整的MediaCrawler爬虫实例
            xhs_crawler = XiaoHongShuCrawler()
            all_notes = []
            
            async with async_playwright() as playwright:
                # 启动浏览器，按照MediaCrawler的标准方式
                chromium = playwright.chromium
                xhs_crawler.browser_context = await xhs_crawler.launch_browser(
                    chromium, None, xhs_crawler.user_agent, headless=config.HEADLESS
                )
                
                # 添加初始化脚本
                await xhs_crawler.browser_context.add_init_script(path="libs/stealth.min.js")
                await xhs_crawler.browser_context.add_cookies([
                    {
                        "name": "webId",
                        "value": "xxx123", 
                        "domain": ".xiaohongshu.com",
                        "path": "/",
                    }
                ])
                
                # 创建页面
                xhs_crawler.context_page = await xhs_crawler.browser_context.new_page()
                await xhs_crawler.context_page.goto(xhs_crawler.index_url)
                
                # 创建客户端
                xhs_crawler.xhs_client = await xhs_crawler.create_xhs_client(None)
                
                # 检查登录状态
                if not await xhs_crawler.xhs_client.pong():
                    self.logger.info("MediaCrawler: connection test failed, performing login")
                    from media_platform.xhs.login import XiaoHongShuLogin
                    
                    login_obj = XiaoHongShuLogin(
                        login_type=config.LOGIN_TYPE,
                        login_phone="",
                        browser_context=xhs_crawler.browser_context,
                        context_page=xhs_crawler.context_page,
                        cookie_str=config.COOKIES,
                    )
                    await login_obj.begin()
                    await xhs_crawler.xhs_client.update_cookies(
                        browser_context=xhs_crawler.browser_context
                    )
                else:
                    self.logger.info("MediaCrawler: connection test passed")
                
                # 执行搜索，按照MediaCrawler的搜索逻辑
                from media_platform.xhs.field import SearchSortType
                from media_platform.xhs.help import get_search_id
                
                xhs_limit_count = 20  # XHS每页固定限制
                
                for keyword in keywords:
                    self.logger.info("MediaCrawler search for keyword", keyword=keyword)
                    
                    search_id = get_search_id()
                    page = 1
                    
                    try:
                        notes_res = await xhs_crawler.xhs_client.get_note_by_keyword(
                            keyword=keyword,
                            search_id=search_id,
                            page=page,
                            sort=SearchSortType.MOST_POPULAR  # 使用热门排序
                        )
                        
                        self.logger.info("MediaCrawler search result", 
                                       keyword=keyword,
                                       has_items=bool(notes_res and notes_res.get("items")),
                                       item_count=len(notes_res.get("items", [])) if notes_res else 0)
                        
                        if not notes_res or not notes_res.get("items"):
                            self.logger.warning("No notes found for keyword", keyword=keyword)
                            continue
                        
                        # 获取笔记详情
                        for post_item in notes_res.get("items", []):
                            if post_item.get("model_type") in ("rec_query", "hot_query"):
                                continue
                                
                            try:
                                note_detail = await xhs_crawler.xhs_client.get_note_by_id(
                                    note_id=post_item.get("id"),
                                    xsec_source=post_item.get("xsec_source"),
                                    xsec_token=post_item.get("xsec_token")
                                )
                                
                                if note_detail:
                                    # 添加来源关键词和额外信息
                                    note_detail['source_keyword'] = keyword
                                    note_detail.update({
                                        "xsec_token": post_item.get("xsec_token"), 
                                        "xsec_source": post_item.get("xsec_source")
                                    })
                                    all_notes.append(note_detail)
                                    
                                    self.logger.debug("Found note with complete MediaCrawler", 
                                                    note_id=post_item.get("id"),
                                                    keyword=keyword)
                                    
                                    # 控制总数
                                    if len(all_notes) >= max_count:
                                        break
                                        
                            except Exception as e:
                                self.logger.warning("Failed to get note detail", 
                                                  note_id=post_item.get("id"),
                                                  error=str(e))
                                continue
                        
                        self.logger.info("Found notes for keyword", 
                                       keyword=keyword, 
                                       count=len([n for n in all_notes if n.get('source_keyword') == keyword]))
                    
                    except Exception as e:
                        self.logger.error("Failed to search keyword with complete MediaCrawler", 
                                        keyword=keyword, 
                                        error=str(e))
                        continue
                    
                    # 控制总数
                    if len(all_notes) >= max_count:
                        break
                
                # 关闭浏览器
                await xhs_crawler.close()
            
            # 截取到指定数量
            result = all_notes[:max_count]
            
            self.logger.info("Complete MediaCrawler search completed", 
                           total_found=len(all_notes), 
                           returned=len(result))
            
            return result
            
        except Exception as e:
            self.logger.error("Complete MediaCrawler search failed", error=str(e))
            raise PlatformError("xhs", f"Complete MediaCrawler search failed: {str(e)}")
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def _search_notes_with_mediacrawler_style(
        self, 
        xhs_client, 
        keywords: List[str], 
        max_count: int
    ) -> List[Dict[str, Any]]:
        """
        使用MediaCrawler标准方式搜索笔记
        
        Args:
            crawler: XHS爬虫实例
            keywords: 关键词列表
            max_count: 最大数量
            
        Returns:
            原始数据列表
        """
        original_cwd = os.getcwd()
        try:
            # 切换到mediacrawler目录以确保相对路径正确
            os.chdir(self.mediacrawler_path)
            
            # 导入MediaCrawler的搜索相关模块
            from media_platform.xhs.field import SearchSortType
            from media_platform.xhs.help import get_search_id
            
            all_notes = []
            xhs_limit_count = 20  # XHS每页固定限制
            
            for keyword in keywords:
                self.logger.info("Searching for keyword with MediaCrawler style", keyword=keyword)
                
                try:
                    page = 1
                    search_id = get_search_id()
                    
                    # 使用MediaCrawler的标准搜索参数
                    notes_res = await xhs_client.get_note_by_keyword(
                        keyword=keyword,
                        search_id=search_id,
                        page=page,
                        page_size=min(xhs_limit_count, max_count),
                        sort=SearchSortType.MOST_POPULAR  # 使用热门排序，与MediaCrawler配置一致
                    )
                    
                    self.logger.info("MediaCrawler style search result", 
                                   keyword=keyword,
                                   has_items=bool(notes_res and notes_res.get("items")),
                                   item_count=len(notes_res.get("items", [])) if notes_res else 0)
                    
                    if not notes_res or not notes_res.get("items"):
                        self.logger.warning("No notes found for keyword", keyword=keyword)
                        continue
                    
                    # 获取笔记详情，跟MediaCrawler一样的逻辑
                    for post_item in notes_res.get("items", []):
                        if post_item.get("model_type") in ("rec_query", "hot_query"):
                            continue
                            
                        try:
                            note_detail = await xhs_client.get_note_by_id(
                                note_id=post_item.get("id"),
                                xsec_source=post_item.get("xsec_source"),
                                xsec_token=post_item.get("xsec_token")
                            )
                            
                            if note_detail:
                                # 添加来源关键词
                                note_detail['source_keyword'] = keyword
                                all_notes.append(note_detail)
                                
                                self.logger.debug("Found note with MediaCrawler style", 
                                                note_id=post_item.get("id"),
                                                keyword=keyword)
                                
                                # 控制总数
                                if len(all_notes) >= max_count:
                                    break
                                    
                        except Exception as e:
                            self.logger.warning("Failed to get note detail", 
                                              note_id=post_item.get("id"),
                                              error=str(e))
                            continue
                    
                    self.logger.info("Found notes for keyword", 
                                   keyword=keyword, 
                                   count=len([n for n in all_notes if n.get('source_keyword') == keyword]))
                
                except Exception as e:
                    self.logger.error("Failed to search keyword with MediaCrawler style", 
                                    keyword=keyword, 
                                    error=str(e))
                    continue
                
                # 控制总数
                if len(all_notes) >= max_count:
                    break
            
            # 截取到指定数量
            result = all_notes[:max_count]
            
            self.logger.info("MediaCrawler style search completed", 
                           total_found=len(all_notes), 
                           returned=len(result))
            
            return result
            
        except Exception as e:
            self.logger.error("MediaCrawler style search failed", error=str(e))
            raise PlatformError("xhs", f"MediaCrawler style search failed: {str(e)}")
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def _create_xhs_client_mediacrawler_style(self, crawler):
        """按照MediaCrawler方式创建XHS客户端"""
        original_cwd = os.getcwd()
        try:
            # 切换到mediacrawler目录以确保相对路径正确
            os.chdir(self.mediacrawler_path)
            
            # 导入MediaCrawler的XHS客户端
            from media_platform.xhs.client import XiaoHongShuClient
            from tools import utils
            
            # 创建浏览器上下文和页面（如果需要）
            if not hasattr(crawler, 'browser_context') or not crawler.browser_context:
                # 如果没有浏览器上下文，需要创建
                from playwright.async_api import async_playwright
                import config
                
                async with async_playwright() as playwright:
                    chromium = playwright.chromium
                    crawler.browser_context = await crawler.launch_browser(
                        chromium, None, crawler.user_agent, headless=config.HEADLESS
                    )
                    crawler.context_page = await crawler.browser_context.new_page()
                    await crawler.context_page.goto("https://www.xiaohongshu.com")
            
            # 获取cookies并创建客户端
            cookie_str, cookie_dict = utils.convert_cookies(
                await crawler.browser_context.cookies()
            )
            
            xhs_client = XiaoHongShuClient(
                proxies=None,  # 暂时不使用代理
                headers={
                    "User-Agent": crawler.user_agent,
                    "Cookie": cookie_str,
                    "Origin": "https://www.xiaohongshu.com",
                    "Referer": "https://www.xiaohongshu.com",
                    "Content-Type": "application/json;charset=UTF-8",
                },
                playwright_page=crawler.context_page,
                cookie_dict=cookie_dict,
            )
            
            self.logger.info("MediaCrawler-style XHS client created successfully")
            return xhs_client
            
        except Exception as e:
            self.logger.error("Failed to create MediaCrawler-style XHS client", error=str(e))
            raise PlatformError("xhs", f"Failed to create XHS client: {str(e)}")
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def _perform_mediacrawler_login(self, crawler):
        """按照MediaCrawler方式执行登录"""
        try:
            # 确保导入正确的MediaCrawler配置
            mediacrawler_config_path = os.path.join(self.mediacrawler_path, 'config')
            if mediacrawler_config_path not in sys.path:
                sys.path.insert(0, mediacrawler_config_path)
            import base_config as config
            
            from media_platform.xhs.login import XiaoHongShuLogin
            
            self.logger.info("Starting MediaCrawler-style login process", login_type=config.LOGIN_TYPE)
            
            # 创建登录实例
            login_instance = XiaoHongShuLogin(
                login_type=config.LOGIN_TYPE,
                login_phone="",  # input your phone number if needed
                browser_context=crawler.browser_context,
                context_page=crawler.context_page,
                cookie_str=config.COOKIES if config.LOGIN_TYPE == "cookie" else ""
            )
            
            # 执行登录
            await login_instance.begin()
            
            self.logger.info("MediaCrawler-style login process completed successfully")
            
        except Exception as e:
            self.logger.error("MediaCrawler-style login process failed", error=str(e))
            raise
    
    async def _ensure_login_status(self, crawler):
        """确保登录状态有效"""
        try:
            # 确保导入正确的MediaCrawler配置
            mediacrawler_config_path = os.path.join(self.mediacrawler_path, 'config')
            if mediacrawler_config_path not in sys.path:
                sys.path.insert(0, mediacrawler_config_path)
            import base_config as config
            
            self.logger.info("Checking login configuration", login_type=config.LOGIN_TYPE)
            
            if config.LOGIN_TYPE == "qrcode":
                # 如果配置为扫码登录，总是执行登录流程
                self.logger.info("QR code login configured, initiating login process")
                await self._perform_login(crawler)
            elif config.LOGIN_TYPE == "cookie":
                # Cookie登录模式，检查cookie是否有效
                self.logger.info("Cookie login configured, validating cookie")
                cookie_valid = await self._validate_xhs_cookie()
                
                if not cookie_valid:
                    self.logger.warning("XHS Cookie validation failed, attempting refresh")
                    # 尝试刷新cookie或提供指导
                    await self._handle_invalid_cookie()
                else:
                    self.logger.info("XHS Cookie validation passed")
            
        except Exception as e:
            self.logger.warning("Login status check failed", error=str(e))
    
    async def _validate_xhs_cookie(self) -> bool:
        """验证XHS Cookie有效性"""
        try:
            # 从设置或配置获取cookie
            cookie_str = self.config.get('xhs_cookie', '') if hasattr(self, 'config') and self.config else ''
            
            if not cookie_str:
                # 尝试从MediaCrawler配置获取
                try:
                    import config
                    cookie_str = getattr(config, 'COOKIES', '')
                except (ImportError, AttributeError):
                    pass
            
            if not cookie_str:
                self.logger.warning("No XHS cookie found for validation")
                return False
            
            # 基本格式检查
            if len(cookie_str) < 50:  # Cookie应该比较长
                self.logger.warning("XHS cookie appears too short", length=len(cookie_str))
                return False
            
            # 检查必要的cookie字段
            required_cookie_parts = ['a1', 'webId', 'web_session']
            found_parts = []
            
            for part in required_cookie_parts:
                if part in cookie_str:
                    found_parts.append(part)
            
            if len(found_parts) < 2:
                self.logger.warning("XHS cookie missing required parts", 
                                  found=found_parts, 
                                  required=required_cookie_parts)
                return False
            
            self.logger.info("XHS cookie format validation passed", 
                           found_parts=found_parts, 
                           cookie_length=len(cookie_str))
            
            # TODO: 可以添加实际API调用验证cookie有效性
            # 这里暂时返回True，因为格式检查通过
            return True
            
        except Exception as e:
            self.logger.error("XHS cookie validation failed", error=str(e))
            return False
    
    async def _handle_invalid_cookie(self):
        """处理无效的Cookie"""
        self.logger.error("XHS Cookie无效或已过期")
        
        # 提供用户指导
        cookie_guidance = """
        🔄 XHS Cookie已过期，请按以下步骤更新：
        
        1. 浏览器打开 https://www.xiaohongshu.com 并登录
        2. 按F12打开开发者工具 -> Network标签
        3. 刷新页面，点击任意请求查看Request Headers
        4. 复制Cookie完整值
        5. 更新环境变量 XHS_COOKIE 或配置文件
        6. 重启应用
        
        注意：Cookie通常包含 a1、webId、web_session 等字段
        """
        
        self.logger.info("Cookie refresh guidance", guidance=cookie_guidance)
        
        # 可以选择抛出异常让上层处理，或者尝试其他登录方式
        raise PlatformError("xhs", "XHS Cookie无效，需要手动更新。请查看日志获取更新指导。")
    
    async def _refresh_xhs_cookie(self):
        """尝试刷新XHS Cookie（如果可能的话）"""
        try:
            self.logger.info("Attempting to refresh XHS cookie")
            
            # 对于XHS，通常需要用户手动更新cookie
            # 这里可以实现自动化的cookie刷新逻辑，但需要小心不要违反服务条款
            
            # 暂时返回False，表示需要手动刷新
            self.logger.warning("Automatic cookie refresh not implemented for XHS")
            self.logger.info("Please manually update XHS_COOKIE environment variable")
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to refresh XHS cookie", error=str(e))
            return False
    
    async def _perform_login(self, crawler):
        """执行登录流程"""
        try:
            # 确保导入正确的MediaCrawler配置
            mediacrawler_config_path = os.path.join(self.mediacrawler_path, 'config')
            if mediacrawler_config_path not in sys.path:
                sys.path.insert(0, mediacrawler_config_path)
            import base_config as config
            
            from media_platform.xhs.login import XiaoHongShuLogin
            from playwright.async_api import async_playwright
            
            self.logger.info("Starting login process", login_type=config.LOGIN_TYPE)
            
            async with async_playwright() as playwright:
                # 根据配置选择启动模式
                if config.ENABLE_CDP_MODE:
                    browser_context = await crawler.launch_browser_with_cdp(
                        playwright, None, crawler.user_agent,
                        headless=config.CDP_HEADLESS
                    )
                else:
                    chromium = playwright.chromium
                    browser_context = await crawler.launch_browser(
                        chromium, None, crawler.user_agent, headless=config.HEADLESS
                    )
                
                # 创建页面并导航到小红书
                context_page = await browser_context.new_page()
                await context_page.goto("https://www.xiaohongshu.com")
                
                # 创建登录实例
                login_instance = XiaoHongShuLogin(
                    login_type=config.LOGIN_TYPE,
                    browser_context=browser_context,
                    context_page=context_page,
                    cookie_str=config.COOKIES if config.LOGIN_TYPE == "cookie" else ""
                )
                
                # 执行登录
                await login_instance.begin()
                
                self.logger.info("Login process completed successfully")
                
        except Exception as e:
            self.logger.error("Login process failed", error=str(e))
            raise
    
    async def transform_to_raw_content(self, xhs_data: Dict[str, Any]) -> RawContent:
        """
        将XHS数据转换为统一格式
        
        Args:
            xhs_data: XHS原始数据
            
        Returns:
            标准化的RawContent
        """
        try:
            # 提取基础信息
            note_id = xhs_data.get('note_id', '')
            title = xhs_data.get('title', '')
            desc = xhs_data.get('desc', '')
            content_type = xhs_data.get('type', 'text')
            
            # 组合内容
            full_content = f"{title}\n{desc}".strip()
            
            # 处理时间戳
            publish_time = self._parse_timestamp(xhs_data.get('time'))
            last_update_time = self._parse_timestamp(xhs_data.get('last_update_time'))
            
            # 处理媒体URL
            image_urls = []
            video_urls = []
            
            if content_type == "video" and xhs_data.get('video_url'):
                video_urls.append(xhs_data['video_url'])
            
            # 处理图片URL - MediaCrawler格式
            if xhs_data.get('image_list'):
                img_list = xhs_data['image_list']
                if isinstance(img_list, str):
                    image_urls.append(img_list)
                elif isinstance(img_list, list):
                    for img in img_list:
                        if isinstance(img, dict):
                            # MediaCrawler返回的是复杂对象，提取URL
                            img_url = img.get('url') or img.get('url_default') or ''
                            if img_url:
                                image_urls.append(img_url)
                        elif isinstance(img, str):
                            image_urls.append(img)
            
            # 处理标签 - MediaCrawler格式
            tags = []
            if xhs_data.get('tag_list'):
                tag_list = xhs_data['tag_list']
                if isinstance(tag_list, str):
                    tags = [tag.strip() for tag in tag_list.split(',') if tag.strip()]
                elif isinstance(tag_list, list):
                    for tag in tag_list:
                        if isinstance(tag, dict):
                            # MediaCrawler返回的是对象，提取name
                            tag_name = tag.get('name', '')
                            if tag_name:
                                tags.append(tag_name)
                        elif isinstance(tag, str):
                            tags.append(tag)
            
            # 创建RawContent对象
            raw_content = RawContent(
                platform=Platform.XHS,
                content_id=note_id,
                content_type=ContentType.VIDEO if content_type == "video" else ContentType.TEXT,
                title=title,
                content=desc,
                raw_content=json.dumps(xhs_data, ensure_ascii=False),
                author_id=xhs_data.get('user_id', ''),
                author_name=xhs_data.get('nickname', ''),
                author_avatar=xhs_data.get('avatar', ''),
                publish_time=publish_time,
                crawl_time=datetime.utcnow(),
                last_update_time=last_update_time,
                like_count=self._parse_count(xhs_data.get('liked_count')),
                comment_count=self._parse_count(xhs_data.get('comment_count')),
                share_count=self._parse_count(xhs_data.get('share_count')),
                collect_count=self._parse_count(xhs_data.get('collected_count')),
                image_urls=image_urls,
                video_urls=video_urls,
                tags=tags,
                source_url=xhs_data.get('note_url', ''),
                ip_location=xhs_data.get('ip_location', ''),
                platform_metadata={
                    'xsec_token': xhs_data.get('xsec_token', ''),
                    'last_modify_ts': xhs_data.get('last_modify_ts'),
                    'source_keyword': xhs_data.get('source_keyword', '')
                },
                source_keywords=[xhs_data.get('source_keyword', '')] if xhs_data.get('source_keyword') else []
            )
            
            return raw_content
            
        except Exception as e:
            raise PlatformError("xhs", f"Failed to transform XHS data: {str(e)}")
    
    def _parse_timestamp(self, timestamp_value: Any) -> Optional[datetime]:
        """解析时间戳"""
        if not timestamp_value:
            return None
        
        try:
            if isinstance(timestamp_value, (int, float)):
                # 毫秒时间戳
                if timestamp_value > 10**12:
                    return datetime.fromtimestamp(timestamp_value / 1000)
                # 秒时间戳
                else:
                    return datetime.fromtimestamp(timestamp_value)
            return None
        except Exception:
            return None
    
    def _parse_count(self, count_value: Any) -> int:
        """解析数量字段"""
        if not count_value:
            return 0
        
        try:
            if isinstance(count_value, int):
                return count_value
            
            if isinstance(count_value, str):
                # 处理中文数字：1.2万 -> 12000
                if '万' in count_value:
                    return int(float(count_value.replace('万', '')) * 10000)
                elif '千' in count_value:
                    return int(float(count_value.replace('千', '')) * 1000)
                elif count_value.isdigit():
                    return int(count_value)
            
            return 0
        except Exception:
            return 0