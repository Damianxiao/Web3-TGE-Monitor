"""
百度贴吧平台适配器 - 完整MediaCrawler集成版
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


class TiebaPlatform(AbstractPlatform):
    """百度贴吧平台实现 - 完整MediaCrawler集成版"""
    
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
            
        self._tieba_client = None
        
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
                setattr(config, 'PLATFORM', 'tieba')
            if not hasattr(config, 'LOGIN_TYPE'):
                setattr(config, 'LOGIN_TYPE', 'cookie')
            if not hasattr(config, 'COOKIES'):
                cookie_str = os.getenv('TIEBA_COOKIE', '')
                setattr(config, 'COOKIES', cookie_str)
            if not hasattr(config, 'ENABLE_CDP_MODE'):
                setattr(config, 'ENABLE_CDP_MODE', False)
            if not hasattr(config, 'CDP_HEADLESS'):
                setattr(config, 'CDP_HEADLESS', True)
            if not hasattr(config, 'ENABLE_GET_COMMENTS'):
                setattr(config, 'ENABLE_GET_COMMENTS', False)
            if not hasattr(config, 'ENABLE_GET_SUB_COMMENTS'):
                setattr(config, 'ENABLE_GET_SUB_COMMENTS', False)
            if not hasattr(config, 'CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES'):
                setattr(config, 'CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES', 10)
            if not hasattr(config, 'MAX_CONCURRENCY_NUM'):
                setattr(config, 'MAX_CONCURRENCY_NUM', 4)
            if not hasattr(config, 'TIEBA_SPECIFIED_ID_LIST'):
                setattr(config, 'TIEBA_SPECIFIED_ID_LIST', [])
            if not hasattr(config, 'TIEBA_NAME_LIST'):
                setattr(config, 'TIEBA_NAME_LIST', [])
            if not hasattr(config, 'TIEBA_CREATOR_URL_LIST'):
                setattr(config, 'TIEBA_CREATOR_URL_LIST', [])
            if not hasattr(config, 'CRAWLER_TYPE'):
                setattr(config, 'CRAWLER_TYPE', 'search')
            if not hasattr(config, 'KEYWORDS'):
                setattr(config, 'KEYWORDS', 'TGE')
            if not hasattr(config, 'CRAWLER_MAX_NOTES_COUNT'):
                setattr(config, 'CRAWLER_MAX_NOTES_COUNT', 10)
            if not hasattr(config, 'START_PAGE'):
                setattr(config, 'START_PAGE', 1)
                
            self.logger.info("MediaCrawler environment setup completed")
            
        except Exception as e:
            self.logger.warning("Failed to setup MediaCrawler environment", error=str(e))
        finally:
            os.chdir(original_cwd)
        
    def get_platform_name(self) -> Platform:
        """获取平台名称"""
        return Platform.TIEBA
    
    async def is_available(self) -> bool:
        """检查平台是否可用"""
        original_cwd = os.getcwd()
        try:
            # 验证mediacrawler目录结构
            mediacrawler_path = Path(self.mediacrawler_path)
            required_files = [
                mediacrawler_path / "media_platform" / "tieba" / "core.py",
                mediacrawler_path / "media_platform" / "tieba" / "client.py",
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
            
            # 尝试导入mediacrawler的贴吧模块
            from media_platform.tieba import client as tieba_client
            from media_platform.tieba import core as tieba_core
            
            self.logger.info("Tieba platform modules imported successfully")
            return True
            
        except Exception as e:
            self.logger.error("Tieba platform not available", error=str(e))
            return False
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def _get_tieba_client(self):
        """获取贴吧爬虫实例（延迟初始化）"""
        if self._tieba_client is None:
            original_cwd = os.getcwd()
            try:
                # 切换到mediacrawler目录以确保相对路径正确
                os.chdir(self.mediacrawler_path)
                
                # 再次确保mediacrawler在Python路径中
                self._ensure_mediacrawler_in_path()
                
                # 设置MediaCrawler环境
                self._setup_mediacrawler_environment()
                
                # 导入MediaCrawler的贴吧核心爬虫
                from media_platform.tieba.core import TieBaCrawler
                
                # 创建爬虫实例
                self._tieba_client = TieBaCrawler()
                
                self.logger.info("Tieba crawler initialized")
                
            except Exception as e:
                self.logger.error("Failed to initialize Tieba crawler", error=str(e))
                raise PlatformError("tieba", f"Failed to initialize Tieba crawler: {str(e)}")
            finally:
                # 恢复原工作目录
                os.chdir(original_cwd)
        
        return self._tieba_client
    
    async def crawl(
        self, 
        keywords: List[str], 
        max_count: int = 50,
        **kwargs
    ) -> List[RawContent]:
        """
        爬取贴吧内容 - 完整MediaCrawler方式
        
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
            
            self.logger.info("Starting Tieba crawl with complete MediaCrawler",
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
                                      content_id=item.get('note_id', 'unknown'),
                                      error=str(e))
            
            # 过滤内容
            filtered_contents = await self.filter_content(raw_contents)
            
            self.logger.info("Tieba crawl completed",
                            keywords=validated_keywords,
                            raw_count=len(raw_data),
                            transformed_count=len(raw_contents),
                            filtered_count=len(filtered_contents))
            
            return filtered_contents
            
        except Exception as e:
            self.logger.error("Tieba crawl failed", error=str(e))
            
            # 如果原始异常包含详细错误信息，保留它们
            if hasattr(e, 'detailed_errors'):
                platform_error = PlatformError("tieba", f"Crawl failed: {str(e)}")
                platform_error.detailed_errors = e.detailed_errors
                raise platform_error
            else:
                raise PlatformError("tieba", f"Crawl failed: {str(e)}")
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
            from media_platform.tieba.client import BaiduTieBaClient
            from media_platform.tieba.field import SearchSortType, SearchNoteType
            import config
            
            self.logger.info("Starting complete MediaCrawler search", keywords=keywords, max_count=max_count)
            
            # 创建完整的MediaCrawler客户端实例
            tieba_client = BaiduTieBaClient()
            
            # 设置Headers中的Cookie
            cookie_str = config.COOKIES
            if cookie_str:
                tieba_client.headers["Cookie"] = cookie_str
                self.logger.info("MediaCrawler: Cookie set for Tieba client")
            
            all_notes = []
            
            # 对每个关键词进行搜索
            for keyword in keywords:
                self.logger.info("MediaCrawler search for keyword", keyword=keyword)
                
                try:
                    # 使用MediaCrawler的get_notes_by_keyword方法
                    notes_list = await tieba_client.get_notes_by_keyword(
                        keyword=keyword,
                        page=1,
                        page_size=min(max_count, 50),  # 贴吧每页最多50条
                        sort=SearchSortType.TIME_DESC,
                        note_type=SearchNoteType.FIXED_THREAD
                    )
                    
                    self.logger.info("MediaCrawler search result", 
                                   keyword=keyword,
                                   notes_count=len(notes_list) if notes_list else 0)
                    
                    if not notes_list:
                        self.logger.warning("No notes found for keyword", keyword=keyword)
                        continue
                    
                    # 处理搜索结果
                    for note in notes_list:
                        if note:
                            # 转换为字典格式并添加来源关键词
                            note_dict = {
                                'note_id': note.note_id,
                                'title': note.title,
                                'content': note.content,
                                'author_name': note.author_name,
                                'author_id': note.author_id,
                                'publish_time': note.publish_time,
                                'note_url': note.note_url,
                                'total_replay_count': note.total_replay_count,
                                'avatar': note.avatar,
                                'tieba_name': note.tieba_name,
                                'tieba_link': note.tieba_link,
                                'image_list': note.image_list,
                                'source_keyword': keyword  # 添加来源关键词
                            }
                            all_notes.append(note_dict)
                            
                            self.logger.debug("Found note with complete MediaCrawler", 
                                            note_id=note.note_id,
                                            keyword=keyword)
                            
                            # 控制总数
                            if len(all_notes) >= max_count:
                                break
                    
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
            
            # 截取到指定数量
            result = all_notes[:max_count]
            
            self.logger.info("Complete MediaCrawler search completed", 
                           total_found=len(all_notes), 
                           returned=len(result))
            
            return result
            
        except Exception as e:
            self.logger.error("Complete MediaCrawler search failed", error=str(e))
            raise PlatformError("tieba", f"Complete MediaCrawler search failed: {str(e)}")
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
    
    async def transform_to_raw_content(self, tieba_data: Dict[str, Any]) -> RawContent:
        """
        将贴吧数据转换为统一的RawContent格式
        适配MediaCrawler的数据结构
        """
        
        # 贴吧数据结构解析
        note_id = str(tieba_data.get('note_id', ''))
        title = tieba_data.get('title', '')
        content = tieba_data.get('content', '')
        
        # 作者信息
        author_name = tieba_data.get('author_name', '')
        author_id = tieba_data.get('author_id', '')
        
        # 贴吧信息
        tieba_name = tieba_data.get('tieba_name', '')
        tieba_link = tieba_data.get('tieba_link', '')
        
        # 互动数据
        total_replay_count = tieba_data.get('total_replay_count', 0)
        
        # 构建URL
        source_url = tieba_data.get('note_url', f"https://tieba.baidu.com/p/{note_id}")
        
        # 提取图片
        images = []
        image_list = tieba_data.get('image_list', [])
        if image_list:
            images = image_list
        
        # 头像
        avatar = tieba_data.get('avatar', '')
        if avatar:
            images.append(avatar)
        
        # 发布时间处理
        publish_time = tieba_data.get('publish_time')
        if isinstance(publish_time, str):
            try:
                # 尝试解析时间字符串
                from datetime import datetime
                publish_time = datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                publish_time = None
        
        # 来源关键词
        source_keywords = []
        if 'source_keyword' in tieba_data:
            source_keywords = [tieba_data['source_keyword']]
        
        # 创建RawContent实例
        raw_content = RawContent(
            platform=Platform.TIEBA,
            content_id=note_id,
            content_type=ContentType.POST,
            title=title[:100] if title else "贴吧帖子",
            content=content,
            raw_content=content,  # 添加必需的字段
            author_name=author_name,
            author_id=author_id,
            publish_time=publish_time,
            crawl_time=datetime.now(),  # 添加必需的字段
            source_url=source_url,
            images=images,
            videos=[],  # 贴吧主要是文本和图片内容
            source_keywords=source_keywords,
            
            # 基础互动数据
            like_count=0,  # 贴吧MediaCrawler数据中没有点赞数，使用0
            comment_count=total_replay_count,
            share_count=0,  # 贴吧MediaCrawler数据中没有分享数，使用0
            collect_count=0,  # 贴吧MediaCrawler数据中没有收藏数，使用0
            
            # 贴吧特有的统计数据
            engagement_stats={
                'replies': total_replay_count,
                'comments': total_replay_count,
            },
            
            # 平台特定数据
            platform_specific={
                'note_id': note_id,
                'author_id': author_id,
                'tieba_name': tieba_name,
                'tieba_link': tieba_link,
                'total_replay_count': total_replay_count,
                'avatar': avatar,
                'image_list': image_list
            }
        )
        
        return raw_content