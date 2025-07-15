"""
微博平台适配器 - 完整MediaCrawler集成版
直接使用项目内部的mediacrawler模块，完全按照MediaCrawler的成功模式实现
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


class WeiboPlatform(AbstractPlatform):
    """微博平台实现 - 完整MediaCrawler集成版"""
    
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
            
        self._weibo_client = None
        
        # 确保mediacrawler在Python路径中
        self._ensure_mediacrawler_in_path()
        
    def _ensure_mediacrawler_in_path(self):
        """确保mediacrawler路径在Python路径中"""
        if self.mediacrawler_path not in sys.path:
            sys.path.insert(0, self.mediacrawler_path)
            self.logger.info("Added mediacrawler to Python path", path=self.mediacrawler_path)
        
    def _setup_mediacrawler_environment(self):
        """设置MediaCrawler环境变量和配置"""
        import os
        
        # 设置必要的环境变量
        os.environ['MEDIACRAWLER_PATH'] = self.mediacrawler_path
        
        # 在导入前手动添加缺失的配置常量到config模块
        try:
            original_cwd = os.getcwd()
            os.chdir(self.mediacrawler_path)
            
            import config
            
            # 添加缺失的缓存配置常量
            if not hasattr(config, 'CACHE_TYPE_MEMORY'):
                setattr(config, 'CACHE_TYPE_MEMORY', 'memory')
            if not hasattr(config, 'CACHE_TYPE_REDIS'):
                setattr(config, 'CACHE_TYPE_REDIS', 'redis')
            
            # 添加其他缺失的配置常量    
            if not hasattr(config, 'STOP_WORDS_FILE'):
                setattr(config, 'STOP_WORDS_FILE', './docs/hit_stopwords.txt')
            if not hasattr(config, 'FONT_PATH'):
                setattr(config, 'FONT_PATH', './docs/STZHONGS.TTF')
            if not hasattr(config, 'START_DAY'):
                setattr(config, 'START_DAY', '2024-01-01')
            if not hasattr(config, 'END_DAY'):
                setattr(config, 'END_DAY', '2024-01-01')
            if not hasattr(config, 'ALL_DAY'):
                setattr(config, 'ALL_DAY', False)
            if not hasattr(config, 'CUSTOM_WORDS'):
                setattr(config, 'CUSTOM_WORDS', {})
            if not hasattr(config, 'HEADLESS'):
                setattr(config, 'HEADLESS', True)
            if not hasattr(config, 'SAVE_LOGIN_STATE'):
                setattr(config, 'SAVE_LOGIN_STATE', True)
            if not hasattr(config, 'USER_DATA_DIR'):
                setattr(config, 'USER_DATA_DIR', '%s_user_data_dir')
            if not hasattr(config, 'ENABLE_IP_PROXY'):
                setattr(config, 'ENABLE_IP_PROXY', False)
                
            self.logger.info("MediaCrawler environment setup completed")
            
        except Exception as e:
            self.logger.warning("Failed to setup MediaCrawler environment", error=str(e))
        finally:
            os.chdir(original_cwd)
        
    def get_platform_name(self) -> Platform:
        """获取平台名称"""
        return Platform.WEIBO
    
    async def is_available(self) -> bool:
        """检查平台是否可用"""
        original_cwd = os.getcwd()
        try:
            # 验证mediacrawler目录结构
            mediacrawler_path = Path(self.mediacrawler_path)
            required_files = [
                mediacrawler_path / "media_platform" / "weibo" / "core.py",
                mediacrawler_path / "media_platform" / "weibo" / "client.py",
                mediacrawler_path / "base" / "base_crawler.py"
            ]
            
            for required_file in required_files:
                if not required_file.exists():
                    self.logger.error("Required file not found", file=str(required_file))
                    return False
            
            # 切换到mediacrawler目录以确保相对路径正确
            os.chdir(self.mediacrawler_path)
            
            # 再次确保mediacrawler在Python路径中
            self._ensure_mediacrawler_in_path()
            
            # 设置MediaCrawler环境
            self._setup_mediacrawler_environment()
            
            # 尝试导入mediacrawler的微博模块
            from media_platform.weibo import client as weibo_client
            from media_platform.weibo import core as weibo_core
            
            self.logger.info("Weibo platform modules imported successfully")
            return True
            
        except Exception as e:
            self.logger.error("Weibo platform not available", error=str(e))
            return False
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def _get_weibo_client(self):
        """获取微博爬虫实例（延迟初始化）"""
        if self._weibo_client is None:
            original_cwd = os.getcwd()
            try:
                # 切换到mediacrawler目录以确保相对路径正确
                os.chdir(self.mediacrawler_path)
                
                # 再次确保mediacrawler在Python路径中
                self._ensure_mediacrawler_in_path()
                
                # 设置MediaCrawler环境
                self._setup_mediacrawler_environment()
                
                # 导入MediaCrawler的微博核心爬虫
                from media_platform.weibo.core import WeiboCrawler
                
                # 创建爬虫实例
                self._weibo_client = WeiboCrawler()
                
                self.logger.info("Weibo crawler initialized")
                
            except Exception as e:
                self.logger.error("Failed to initialize Weibo crawler", error=str(e))
                raise PlatformError("weibo", f"Failed to initialize Weibo crawler: {str(e)}")
            finally:
                # 恢复原工作目录
                os.chdir(original_cwd)
        
        return self._weibo_client
    
    async def crawl(
        self, 
        keywords: List[str], 
        max_count: int = 50,
        **kwargs
    ) -> List[RawContent]:
        """
        爬取微博内容 - 完整MediaCrawler方式
        
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
            
            # 再次确保mediacrawler在Python路径中
            self._ensure_mediacrawler_in_path()
            
            # 设置MediaCrawler环境
            self._setup_mediacrawler_environment()
            
            # 首先修改配置文件（在任何MediaCrawler导入之前）
            try:
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
            
            self.logger.info("Starting Weibo crawl with complete MediaCrawler",
                           keywords=validated_keywords,
                           max_count=max_count)
            
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
                                      content_id=item.get('id', 'unknown'),
                                      error=str(e))
            
            # 过滤内容
            filtered_contents = await self.filter_content(raw_contents)
            
            self.logger.info("Weibo crawl completed",
                            keywords=validated_keywords,
                            raw_count=len(raw_data),
                            transformed_count=len(raw_contents),
                            filtered_count=len(filtered_contents))
            
            return filtered_contents
            
        except Exception as e:
            self.logger.error("Weibo crawl failed", error=str(e))
            
            # 如果原始异常包含详细错误信息，保留它们
            if hasattr(e, 'detailed_errors'):
                platform_error = PlatformError("weibo", f"Crawl failed: {str(e)}")
                platform_error.detailed_errors = e.detailed_errors
                raise platform_error
            else:
                raise PlatformError("weibo", f"Crawl failed: {str(e)}")
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
            from media_platform.weibo.core import WeiboCrawler
            from playwright.async_api import async_playwright
            import config
            
            self.logger.info("Starting complete MediaCrawler search", keywords=keywords, max_count=max_count)
            
            # 创建完整的MediaCrawler爬虫实例
            weibo_crawler = WeiboCrawler()
            all_notes = []
            
            async with async_playwright() as playwright:
                # 启动浏览器，按照MediaCrawler的标准方式
                chromium = playwright.chromium
                weibo_crawler.browser_context = await weibo_crawler.launch_browser(
                    chromium, None, weibo_crawler.mobile_user_agent, headless=config.HEADLESS
                )
                
                # 添加初始化脚本
                await weibo_crawler.browser_context.add_init_script(path="libs/stealth.min.js")
                
                # 创建页面
                weibo_crawler.context_page = await weibo_crawler.browser_context.new_page()
                await weibo_crawler.context_page.goto(weibo_crawler.mobile_index_url)
                
                # 创建客户端
                weibo_crawler.wb_client = await weibo_crawler.create_weibo_client(None)
                
                # 检查登录状态
                if not await weibo_crawler.wb_client.pong():
                    self.logger.info("MediaCrawler: connection test failed, performing login")
                    from media_platform.weibo.login import WeiboLogin
                    
                    login_obj = WeiboLogin(
                        login_type=config.LOGIN_TYPE,
                        login_phone="",
                        browser_context=weibo_crawler.browser_context,
                        context_page=weibo_crawler.context_page,
                        cookie_str=config.COOKIES,
                    )
                    await login_obj.begin()
                    
                    # 登录成功后重定向到手机端的网站，再更新手机端登录成功的cookie
                    await weibo_crawler.context_page.goto(weibo_crawler.mobile_index_url)
                    await asyncio.sleep(2)
                    await weibo_crawler.wb_client.update_cookies(browser_context=weibo_crawler.browser_context)
                else:
                    self.logger.info("MediaCrawler: connection test passed")
                
                # 执行搜索，按照MediaCrawler的搜索逻辑
                from media_platform.weibo.field import SearchType
                from media_platform.weibo.help import filter_search_result_card
                
                weibo_limit_count = 10  # 微博每页固定限制
                search_type = SearchType.DEFAULT  # 使用默认搜索类型
                
                for keyword in keywords:
                    self.logger.info("MediaCrawler search for keyword", keyword=keyword)
                    
                    page = 1
                    
                    try:
                        search_res = await weibo_crawler.wb_client.get_note_by_keyword(
                            keyword=keyword,
                            page=page,
                            search_type=search_type
                        )
                        
                        self.logger.info("MediaCrawler search result", 
                                       keyword=keyword,
                                       has_cards=bool(search_res and search_res.get("cards")),
                                       card_count=len(search_res.get("cards", [])) if search_res else 0)
                        
                        if not search_res or not search_res.get("cards"):
                            self.logger.warning("No notes found for keyword", keyword=keyword)
                            continue
                        
                        # 过滤搜索结果卡片
                        note_list = filter_search_result_card(search_res.get("cards"))
                        
                        for note_item in note_list:
                            if note_item:
                                mblog: Dict = note_item.get("mblog")
                                if mblog:
                                    # 添加来源关键词
                                    mblog['source_keyword'] = keyword
                                    all_notes.append(note_item)
                                    
                                    self.logger.debug("Found note with complete MediaCrawler", 
                                                    note_id=mblog.get("id"),
                                                    keyword=keyword)
                                    
                                    # 控制总数
                                    if len(all_notes) >= max_count:
                                        break
                        
                        self.logger.info("Found notes for keyword", 
                                       keyword=keyword, 
                                       count=len([n for n in all_notes if n.get('mblog', {}).get('source_keyword') == keyword]))
                    
                    except Exception as e:
                        self.logger.error("Failed to search keyword with complete MediaCrawler", 
                                        keyword=keyword, 
                                        error=str(e))
                        continue
                    
                    # 控制总数
                    if len(all_notes) >= max_count:
                        break
                
                # 关闭浏览器
                await weibo_crawler.close()
            
            # 截取到指定数量
            result = all_notes[:max_count]
            
            self.logger.info("Complete MediaCrawler search completed", 
                           total_found=len(all_notes), 
                           returned=len(result))
            
            return result
            
        except Exception as e:
            self.logger.error("Complete MediaCrawler search failed", error=str(e))
            raise PlatformError("weibo", f"Complete MediaCrawler search failed: {str(e)}")
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def transform_to_raw_content(self, weibo_data: Dict[str, Any]) -> RawContent:
        """
        将微博数据转换为统一的RawContent格式
        适配MediaCrawler的数据结构
        """
        try:
            # MediaCrawler返回的数据结构：note_item中包含mblog
            mblog = weibo_data.get('mblog', {})
            if not mblog:
                # 如果没有mblog字段，直接使用weibo_data
                mblog = weibo_data
            
            # 提取基础信息
            content_id = str(mblog.get('id', ''))
            text_content = mblog.get('text', '')
            user_info = mblog.get('user', {})
            
            # 构建URL
            user_id = user_info.get('id', '')
            source_url = f"https://weibo.com/{user_id}/{content_id}" if user_id and content_id else ""
            
            # 解析互动数据
            like_count = self._parse_count(mblog.get('attitudes_count', 0))
            comment_count = self._parse_count(mblog.get('comments_count', 0))
            share_count = self._parse_count(mblog.get('reposts_count', 0))
            
            # 处理图片URLs - MediaCrawler格式
            image_urls = []
            pics = mblog.get('pics', [])
            if pics and isinstance(pics, list):
                for pic in pics:
                    if isinstance(pic, dict):
                        # MediaCrawler返回的pic结构
                        pic_url = pic.get('url') or pic.get('large', {}).get('url', '')
                        if pic_url:
                            image_urls.append(pic_url)
                    elif isinstance(pic, str):
                        image_urls.append(pic)
            
            # 如果pics为空，尝试从pic_infos获取
            if not image_urls:
                pic_infos = mblog.get('pic_infos', {})
                if pic_infos:
                    for pic_info in pic_infos.values():
                        if isinstance(pic_info, dict) and 'url' in pic_info:
                            image_urls.append(pic_info['url'])
            
            # 解析发布时间
            publish_time = self._parse_timestamp(mblog.get('created_at'))
            
            # 提取标签 - 从文本中提取话题
            hashtags = self._extract_hashtags(text_content)
            
            # 确定内容类型
            content_type = ContentType.VIDEO if mblog.get('page_info', {}).get('type') == 'video' else (
                ContentType.MIXED if image_urls else ContentType.TEXT
            )
            
            return RawContent(
                platform=Platform.WEIBO,
                content_id=content_id,
                content_type=content_type,
                title=text_content[:100] if text_content else "",  # 微博无标题，使用内容前100字符
                content=text_content,
                raw_content=json.dumps(weibo_data, ensure_ascii=False),
                author_id=str(user_info.get('id', '')),
                author_name=user_info.get('screen_name', ''),
                author_avatar=user_info.get('profile_image_url', ''),
                publish_time=publish_time,
                crawl_time=datetime.utcnow(),
                last_update_time=publish_time,
                like_count=like_count,
                comment_count=comment_count,
                share_count=share_count,
                collect_count=0,  # 微博没有收藏数
                image_urls=image_urls,
                video_urls=[],  # 视频URL需要特殊处理，暂时留空
                tags=hashtags,
                source_url=source_url,
                ip_location=mblog.get('location', ''),
                platform_metadata={
                    'weibo_type': mblog.get('type', ''),
                    'is_verified': user_info.get('verified', False),
                    'followers_count': user_info.get('followers_count', 0),
                    'source_keyword': mblog.get('source_keyword', ''),
                    'original_data': weibo_data
                },
                source_keywords=[mblog.get('source_keyword', '')] if mblog.get('source_keyword') else []
            )
            
        except Exception as e:
            raise PlatformError("weibo", f"Failed to transform Weibo data: {str(e)}")
    
    def _parse_timestamp(self, time_value: Any) -> Optional[datetime]:
        """解析微博时间戳"""
        if not time_value:
            return None
            
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
        
        return None
    
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
        import re
        hashtag_pattern = r'#([^#]+)#'
        hashtags = re.findall(hashtag_pattern, text)
        
        # 清理和去重
        cleaned_hashtags = []
        for tag in hashtags:
            tag = tag.strip()
            if tag and tag not in cleaned_hashtags:
                cleaned_hashtags.append(tag)
        
        return cleaned_hashtags