"""
抖音平台适配器 - 完整MediaCrawler集成版
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


class DouyinPlatform(AbstractPlatform):
    """抖音平台实现 - 完整MediaCrawler集成版"""
    
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
            
        self._douyin_client = None
        
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
            if not hasattr(config, 'PUBLISH_TIME_TYPE'):
                setattr(config, 'PUBLISH_TIME_TYPE', 0)
            if not hasattr(config, 'PLATFORM'):
                setattr(config, 'PLATFORM', 'douyin')
            if not hasattr(config, 'LOGIN_TYPE'):
                setattr(config, 'LOGIN_TYPE', 'cookie')
            if not hasattr(config, 'COOKIES'):
                setattr(config, 'COOKIES', '')
                
            self.logger.info("MediaCrawler environment setup completed")
            
        except Exception as e:
            self.logger.warning("Failed to setup MediaCrawler environment", error=str(e))
        finally:
            os.chdir(original_cwd)
        
    def get_platform_name(self) -> Platform:
        """获取平台名称"""
        return Platform.DOUYIN
    
    async def is_available(self) -> bool:
        """检查平台是否可用"""
        original_cwd = os.getcwd()
        try:
            # 验证mediacrawler目录结构
            mediacrawler_path = Path(self.mediacrawler_path)
            required_files = [
                mediacrawler_path / "media_platform" / "douyin" / "core.py",
                mediacrawler_path / "media_platform" / "douyin" / "client.py",
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
            
            # 尝试导入mediacrawler的抖音模块
            from media_platform.douyin import client as douyin_client
            from media_platform.douyin import core as douyin_core
            
            self.logger.info("Douyin platform modules imported successfully")
            return True
            
        except Exception as e:
            self.logger.error("Douyin platform not available", error=str(e))
            return False
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def _get_douyin_client(self):
        """获取抖音爬虫实例（延迟初始化）"""
        if self._douyin_client is None:
            original_cwd = os.getcwd()
            try:
                # 切换到mediacrawler目录以确保相对路径正确
                os.chdir(self.mediacrawler_path)
                
                # 再次确保mediacrawler在Python路径中
                self._ensure_mediacrawler_in_path()
                
                # 设置MediaCrawler环境
                self._setup_mediacrawler_environment()
                
                # 导入MediaCrawler的抖音核心爬虫
                from media_platform.douyin.core import DouYinCrawler
                
                # 创建爬虫实例
                self._douyin_client = DouYinCrawler()
                
                self.logger.info("Douyin crawler initialized")
                
            except Exception as e:
                self.logger.error("Failed to initialize Douyin crawler", error=str(e))
                raise PlatformError("douyin", f"Failed to initialize Douyin crawler: {str(e)}")
            finally:
                # 恢复原工作目录
                os.chdir(original_cwd)
        
        return self._douyin_client
    
    async def crawl(
        self, 
        keywords: List[str], 
        max_count: int = 50,
        **kwargs
    ) -> List[RawContent]:
        """
        爬取抖音内容 - 完整MediaCrawler方式
        
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
            
            self.logger.info("Starting Douyin crawl with complete MediaCrawler",
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
                                      content_id=item.get('aweme_id', 'unknown'),
                                      error=str(e))
            
            # 过滤内容
            filtered_contents = await self.filter_content(raw_contents)
            
            self.logger.info("Douyin crawl completed",
                            keywords=validated_keywords,
                            raw_count=len(raw_data),
                            transformed_count=len(raw_contents),
                            filtered_count=len(filtered_contents))
            
            return filtered_contents
            
        except Exception as e:
            self.logger.error("Douyin crawl failed", error=str(e))
            
            # 如果原始异常包含详细错误信息，保留它们
            if hasattr(e, 'detailed_errors'):
                platform_error = PlatformError("douyin", f"Crawl failed: {str(e)}")
                platform_error.detailed_errors = e.detailed_errors
                raise platform_error
            else:
                raise PlatformError("douyin", f"Crawl failed: {str(e)}")
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
            from media_platform.douyin.core import DouYinCrawler
            from playwright.async_api import async_playwright
            import config
            
            self.logger.info("Starting complete MediaCrawler search", keywords=keywords, max_count=max_count)
            
            # 创建完整的MediaCrawler爬虫实例
            douyin_crawler = DouYinCrawler()
            all_notes = []
            
            async with async_playwright() as playwright:
                # 启动浏览器，按照MediaCrawler的标准方式
                chromium = playwright.chromium
                douyin_crawler.browser_context = await douyin_crawler.launch_browser(
                    chromium, None, None, headless=config.HEADLESS
                )
                
                # 添加初始化脚本
                await douyin_crawler.browser_context.add_init_script(path="libs/stealth.min.js")
                
                # 创建页面
                douyin_crawler.context_page = await douyin_crawler.browser_context.new_page()
                await douyin_crawler.context_page.goto(douyin_crawler.index_url)
                
                # 创建客户端
                douyin_crawler.dy_client = await douyin_crawler.create_douyin_client(None)
                
                # 检查登录状态
                if not await douyin_crawler.dy_client.pong(douyin_crawler.browser_context):
                    self.logger.info("MediaCrawler: connection test failed, performing login")
                    from media_platform.douyin.login import DouYinLogin
                    
                    login_obj = DouYinLogin(
                        login_type=config.LOGIN_TYPE,
                        login_phone="",
                        browser_context=douyin_crawler.browser_context,
                        context_page=douyin_crawler.context_page,
                        cookie_str=config.COOKIES,
                    )
                    await login_obj.begin()
                    
                    # 登录成功后更新cookie
                    await douyin_crawler.dy_client.update_cookies(browser_context=douyin_crawler.browser_context)
                else:
                    self.logger.info("MediaCrawler: connection test passed")
                
                # 执行搜索，使用MediaCrawler的search_info_by_keyword方法
                from media_platform.douyin.field import PublishTimeType, SearchChannelType, SearchSortType
                
                for keyword in keywords:
                    self.logger.info("MediaCrawler search for keyword", keyword=keyword)
                    
                    try:
                        search_res = await douyin_crawler.dy_client.search_info_by_keyword(
                            keyword=keyword,
                            offset=0,
                            search_channel=SearchChannelType.GENERAL,
                            sort_type=SearchSortType.GENERAL,
                            publish_time=PublishTimeType.UNLIMITED,
                            search_id=""
                        )
                        
                        self.logger.info("MediaCrawler search result", 
                                       keyword=keyword,
                                       has_data=bool(search_res and search_res.get("data")),
                                       data_count=len(search_res.get("data", [])) if search_res else 0)
                        
                        if not search_res or not search_res.get("data"):
                            self.logger.warning("No videos found for keyword", keyword=keyword)
                            continue
                        
                        # 处理搜索结果
                        for aweme_info in search_res.get("data", []):
                            if aweme_info:
                                # 获取aweme_info或者直接使用（根据实际结构）
                                aweme_detail = aweme_info.get("aweme_info", aweme_info)
                                if aweme_detail:
                                    # 添加来源关键词
                                    aweme_detail['source_keyword'] = keyword
                                    all_notes.append(aweme_detail)
                                    
                                    self.logger.debug("Found video with complete MediaCrawler", 
                                                    aweme_id=aweme_detail.get("aweme_id"),
                                                    keyword=keyword)
                                    
                                    # 控制总数
                                    if len(all_notes) >= max_count:
                                        break
                        
                        self.logger.info("Found videos for keyword", 
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
                await douyin_crawler.close()
            
            # 截取到指定数量
            result = all_notes[:max_count]
            
            self.logger.info("Complete MediaCrawler search completed", 
                           total_found=len(all_notes), 
                           returned=len(result))
            
            return result
            
        except Exception as e:
            self.logger.error("Complete MediaCrawler search failed", error=str(e))
            raise PlatformError("douyin", f"Complete MediaCrawler search failed: {str(e)}")
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def transform_to_raw_content(self, douyin_data: Dict[str, Any]) -> RawContent:
        """
        将抖音数据转换为统一的RawContent格式
        适配MediaCrawler的数据结构
        """
        
        # 抖音数据结构解析
        aweme_id = str(douyin_data.get('aweme_id', ''))
        desc = douyin_data.get('desc', '')
        
        # 作者信息
        author_info = douyin_data.get('author', {})
        author_name = author_info.get('nickname', '')
        author_id = author_info.get('unique_id', '')
        
        # 视频统计信息
        statistics = douyin_data.get('statistics', {})
        digg_count = statistics.get('digg_count', 0)
        comment_count = statistics.get('comment_count', 0)
        share_count = statistics.get('share_count', 0)
        play_count = statistics.get('play_count', 0)
        
        # 视频信息
        video_info = douyin_data.get('video', {})
        video_duration = video_info.get('duration', 0)
        
        # 构建URL
        source_url = f"https://www.douyin.com/video/{aweme_id}"
        
        # 提取视频封面
        images = []
        cover_url = video_info.get('cover', {}).get('url_list', [])
        if cover_url:
            images = [cover_url[0]]
        
        # 提取视频链接
        videos = []
        play_addr = video_info.get('play_addr', {}).get('url_list', [])
        if play_addr:
            videos = [play_addr[0]]
        
        # 发布时间处理
        publish_time = None
        create_time = douyin_data.get('create_time')
        if create_time:
            try:
                publish_time = datetime.fromtimestamp(int(create_time))
            except (ValueError, TypeError):
                pass
        
        # 来源关键词
        source_keywords = []
        if 'source_keyword' in douyin_data:
            source_keywords = [douyin_data['source_keyword']]
        
        # 创建RawContent实例
        raw_content = RawContent(
            platform=Platform.DOUYIN,
            content_id=aweme_id,
            content_type=ContentType.VIDEO,
            title=desc[:100] if desc else "抖音视频",  # 抖音用描述作为标题
            content=desc,
            author_name=author_name,
            author_id=author_id,
            publish_time=publish_time,
            source_url=source_url,
            images=images,
            videos=videos,
            source_keywords=source_keywords,
            
            # 抖音特有的统计数据
            engagement_stats={
                'likes': digg_count,
                'comments': comment_count,
                'shares': share_count,
                'plays': play_count
            },
            
            # 视频相关信息
            video_duration=video_duration,
            
            # 平台特定数据
            platform_specific={
                'aweme_id': aweme_id,
                'author_unique_id': author_id,
                'video_duration': video_duration,
                'digg_count': digg_count,
                'comment_count': comment_count,
                'share_count': share_count,
                'play_count': play_count,
                'create_time': create_time
            }
        )
        
        return raw_content