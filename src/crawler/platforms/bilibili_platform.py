"""
Bilibili平台适配器 - 完整MediaCrawler集成版
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


class BilibiliPlatform(AbstractPlatform):
    """Bilibili平台实现 - 完整MediaCrawler集成版"""
    
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
            
        self._bilibili_client = None
        
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
                setattr(config, 'PLATFORM', 'bilibili')
            if not hasattr(config, 'LOGIN_TYPE'):
                setattr(config, 'LOGIN_TYPE', 'cookie')
            if not hasattr(config, 'COOKIES'):
                cookie_str = os.getenv('BILIBILI_COOKIE', '')
                setattr(config, 'COOKIES', cookie_str)
                
            self.logger.info("MediaCrawler environment setup completed")
            
        except Exception as e:
            self.logger.warning("Failed to setup MediaCrawler environment", error=str(e))
        finally:
            os.chdir(original_cwd)
        
    def get_platform_name(self) -> Platform:
        """获取平台名称"""
        return Platform.BILIBILI
    
    async def is_available(self) -> bool:
        """检查平台是否可用"""
        original_cwd = os.getcwd()
        try:
            # 验证mediacrawler目录结构
            mediacrawler_path = Path(self.mediacrawler_path)
            required_files = [
                mediacrawler_path / "media_platform" / "bilibili" / "core.py",
                mediacrawler_path / "media_platform" / "bilibili" / "client.py",
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
            
            # 尝试导入mediacrawler的bilibili模块
            from media_platform.bilibili import client as bilibili_client
            from media_platform.bilibili import core as bilibili_core
            
            self.logger.info("Bilibili platform modules imported successfully")
            return True
            
        except Exception as e:
            self.logger.error("Bilibili platform not available", error=str(e))
            return False
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def _get_bilibili_client(self):
        """获取Bilibili爬虫实例（延迟初始化）"""
        if self._bilibili_client is None:
            original_cwd = os.getcwd()
            try:
                # 切换到mediacrawler目录以确保相对路径正确
                os.chdir(self.mediacrawler_path)
                
                # 再次确保mediacrawler在Python路径中
                self._ensure_mediacrawler_in_path()
                
                # 设置MediaCrawler环境
                self._setup_mediacrawler_environment()
                
                # 导入MediaCrawler的bilibili核心爬虫
                from media_platform.bilibili.core import BilibiliCrawler
                
                # 创建爬虫实例
                self._bilibili_client = BilibiliCrawler()
                
                self.logger.info("Bilibili crawler initialized")
                
            except Exception as e:
                self.logger.error("Failed to initialize Bilibili crawler", error=str(e))
                raise PlatformError("bilibili", f"Failed to initialize Bilibili crawler: {str(e)}")
            finally:
                # 恢复原工作目录
                os.chdir(original_cwd)
        
        return self._bilibili_client
    
    async def crawl(
        self, 
        keywords: List[str], 
        max_count: int = 50,
        **kwargs
    ) -> List[RawContent]:
        """
        爬取Bilibili内容 - 完整MediaCrawler方式
        
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
            
            self.logger.info("Starting Bilibili crawl with complete MediaCrawler",
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
                                      content_id=item.get('aid', 'unknown'),
                                      error=str(e))
            
            # 过滤内容
            filtered_contents = await self.filter_content(raw_contents)
            
            self.logger.info("Bilibili crawl completed",
                            keywords=validated_keywords,
                            raw_count=len(raw_data),
                            transformed_count=len(raw_contents),
                            filtered_count=len(filtered_contents))
            
            return filtered_contents
            
        except Exception as e:
            self.logger.error("Bilibili crawl failed", error=str(e))
            
            # 如果原始异常包含详细错误信息，保留它们
            if hasattr(e, 'detailed_errors'):
                platform_error = PlatformError("bilibili", f"Crawl failed: {str(e)}")
                platform_error.detailed_errors = e.detailed_errors
                raise platform_error
            else:
                raise PlatformError("bilibili", f"Crawl failed: {str(e)}")
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
            from media_platform.bilibili.core import BilibiliCrawler
            from media_platform.bilibili.field import SearchOrderType
            from playwright.async_api import async_playwright
            import config
            
            self.logger.info("Starting complete MediaCrawler search", keywords=keywords, max_count=max_count)
            
            # 创建完整的MediaCrawler爬虫实例
            bilibili_crawler = BilibiliCrawler()
            all_videos = []
            
            async with async_playwright() as playwright:
                # 启动浏览器，按照MediaCrawler的标准方式
                chromium = playwright.chromium
                bilibili_crawler.browser_context = await bilibili_crawler.launch_browser(
                    chromium, None, None, headless=config.HEADLESS
                )
                
                # 添加初始化脚本
                await bilibili_crawler.browser_context.add_init_script(path="libs/stealth.min.js")
                
                # 创建页面
                bilibili_crawler.context_page = await bilibili_crawler.browser_context.new_page()
                await bilibili_crawler.context_page.goto(bilibili_crawler.index_url)
                
                # 创建客户端
                bilibili_crawler.bili_client = await bilibili_crawler.create_bilibili_client(None)
                
                # 检查登录状态
                if not await bilibili_crawler.bili_client.pong():
                    self.logger.info("MediaCrawler: connection test failed, performing login")
                    from media_platform.bilibili.login import BilibiliLogin
                    
                    login_obj = BilibiliLogin(
                        login_type=config.LOGIN_TYPE,
                        login_phone="",
                        browser_context=bilibili_crawler.browser_context,
                        context_page=bilibili_crawler.context_page,
                        cookie_str=config.COOKIES,
                    )
                    await login_obj.begin()
                    
                    # 登录成功后更新cookie
                    await bilibili_crawler.bili_client.update_cookies(browser_context=bilibili_crawler.browser_context)
                else:
                    self.logger.info("MediaCrawler: connection test passed")
                
                # 执行搜索，使用MediaCrawler的search_video_by_keyword方法
                for keyword in keywords:
                    self.logger.info("MediaCrawler search for keyword", keyword=keyword)
                    
                    page = 1
                    page_size = 20
                    
                    try:
                        search_res = await bilibili_crawler.bili_client.search_video_by_keyword(
                            keyword=keyword,
                            page=page,
                            page_size=page_size,
                            order=SearchOrderType.DEFAULT,
                            pubtime_begin_s=0,
                            pubtime_end_s=0
                        )
                        
                        self.logger.info("MediaCrawler search result", 
                                       keyword=keyword,
                                       has_data=bool(search_res and search_res.get("result")),
                                       data_count=len(search_res.get("result", [])) if search_res else 0)
                        
                        if not search_res or not search_res.get("result"):
                            self.logger.warning("No videos found for keyword", keyword=keyword)
                            continue
                        
                        # 处理搜索结果
                        for video_info in search_res.get("result", []):
                            if video_info:
                                # 添加来源关键词
                                video_info['source_keyword'] = keyword
                                all_videos.append(video_info)
                                
                                self.logger.debug("Found video with complete MediaCrawler", 
                                                aid=video_info.get("aid"),
                                                keyword=keyword)
                                
                                # 控制总数
                                if len(all_videos) >= max_count:
                                    break
                        
                        self.logger.info("Found videos for keyword", 
                                       keyword=keyword, 
                                       count=len([v for v in all_videos if v.get('source_keyword') == keyword]))
                    
                    except Exception as e:
                        self.logger.error("Failed to search keyword with complete MediaCrawler", 
                                        keyword=keyword, 
                                        error=str(e))
                        continue
                    
                    # 控制总数
                    if len(all_videos) >= max_count:
                        break
                
                # 关闭浏览器
                await bilibili_crawler.close()
            
            # 截取到指定数量
            result = all_videos[:max_count]
            
            self.logger.info("Complete MediaCrawler search completed", 
                           total_found=len(all_videos), 
                           returned=len(result))
            
            return result
            
        except Exception as e:
            self.logger.error("Complete MediaCrawler search failed", error=str(e))
            raise PlatformError("bilibili", f"Complete MediaCrawler search failed: {str(e)}")
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def transform_to_raw_content(self, bilibili_data: Dict[str, Any]) -> RawContent:
        """
        将Bilibili数据转换为统一的RawContent格式
        适配MediaCrawler的数据结构
        """
        
        # Bilibili数据结构解析
        aid = str(bilibili_data.get('aid', ''))
        bvid = bilibili_data.get('bvid', '')
        title = bilibili_data.get('title', '')
        description = bilibili_data.get('description', '')
        
        # 作者信息
        author = bilibili_data.get('author', '')
        mid = bilibili_data.get('mid', '')
        
        # 视频统计信息
        view = bilibili_data.get('view', 0)
        danmaku = bilibili_data.get('danmaku', 0)
        reply = bilibili_data.get('reply', 0)
        favorite = bilibili_data.get('favorite', 0)
        coin = bilibili_data.get('coin', 0)
        share = bilibili_data.get('share', 0)
        like = bilibili_data.get('like', 0)
        
        # 视频信息
        duration = bilibili_data.get('duration', '')
        
        # 构建URL
        source_url = f"https://www.bilibili.com/video/{bvid}" if bvid else f"https://www.bilibili.com/video/av{aid}"
        
        # 提取视频封面
        images = []
        pic = bilibili_data.get('pic', '')
        if pic:
            images = [pic]
        
        # 发布时间处理
        publish_time = None
        pubdate = bilibili_data.get('pubdate')
        if pubdate:
            try:
                publish_time = datetime.fromtimestamp(int(pubdate))
            except (ValueError, TypeError):
                pass
        
        # 来源关键词
        source_keywords = []
        if 'source_keyword' in bilibili_data:
            source_keywords = [bilibili_data['source_keyword']]
        
        # 时长处理
        video_duration = 0
        if duration:
            try:
                # 时长格式通常是 "MM:SS" 或者秒数
                if isinstance(duration, str) and ':' in duration:
                    parts = duration.split(':')
                    if len(parts) == 2:
                        video_duration = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        video_duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    video_duration = int(duration)
            except (ValueError, TypeError):
                pass
        
        # 创建RawContent实例
        raw_content = RawContent(
            platform=Platform.BILIBILI,
            content_id=aid,
            content_type=ContentType.VIDEO,
            title=title,
            content=description,
            raw_content=description,  # 添加必需的字段
            author_name=author,
            author_id=str(mid),
            publish_time=publish_time,
            crawl_time=datetime.now(),  # 添加必需的字段
            source_url=source_url,
            images=images,
            videos=[],  # Bilibili视频链接需要额外API获取
            source_keywords=source_keywords,
            
            # 基础互动数据
            like_count=like,
            comment_count=reply,
            share_count=share,
            collect_count=favorite,
            
            # Bilibili特有的统计数据
            engagement_stats={
                'views': view,
                'danmaku': danmaku,
                'replies': reply,
                'favorites': favorite,
                'coins': coin,
                'shares': share,
                'likes': like
            },
            
            # 视频相关信息
            video_duration=video_duration,
            
            # 平台特定数据
            platform_specific={
                'aid': aid,
                'bvid': bvid,
                'mid': mid,
                'duration': duration,
                'view': view,
                'danmaku': danmaku,
                'reply': reply,
                'favorite': favorite,
                'coin': coin,
                'share': share,
                'like': like,
                'pubdate': pubdate
            }
        )
        
        return raw_content