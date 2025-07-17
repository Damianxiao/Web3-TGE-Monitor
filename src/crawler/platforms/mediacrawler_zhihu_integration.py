"""
MediaCrawler知乎集成层
基于实际测试验证的成功方案，封装MediaCrawler的完整调用流程
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime

# 加载.env文件
from dotenv import load_dotenv
load_dotenv()

class MediaCrawlerZhihuIntegration:
    """MediaCrawler知乎集成层 - 基于验证的成功方案"""
    
    def __init__(self, mediacrawler_path: str, zhihu_cookie: str):
        self.mediacrawler_path = Path(mediacrawler_path)
        self.zhihu_cookie = zhihu_cookie
        self.logger = structlog.get_logger(__name__)
        self.original_cwd = None
        
        # 验证MediaCrawler路径
        if not self.mediacrawler_path.exists():
            raise ValueError(f"MediaCrawler path does not exist: {mediacrawler_path}")
        
        # 验证关键文件
        required_files = [
            "docs/hit_stopwords.txt",
            "media_platform/zhihu/__init__.py",
            "config/__init__.py"
        ]
        for file_path in required_files:
            if not (self.mediacrawler_path / file_path).exists():
                raise ValueError(f"Required MediaCrawler file missing: {file_path}")
    
    async def search_content(self, keywords: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        使用MediaCrawler搜索知乎内容
        
        Args:
            keywords: 搜索关键词，逗号分隔
            max_results: 最大结果数量
            
        Returns:
            List[Dict]: 标准化的内容数据列表
        """
        self.logger.info(f"Starting MediaCrawler zhihu search: keywords={keywords}, max_results={max_results}")
        
        # 切换到MediaCrawler目录
        self._switch_to_mediacrawler_dir()
        
        try:
            # 执行MediaCrawler爬取
            await self._execute_mediacrawler(keywords, max_results)
            
            # 读取并转换数据
            results = await self._load_and_convert_data()
            
            self.logger.info(f"MediaCrawler search completed: {len(results)} results")
            return results[:max_results]  # 确保不超过限制
            
        except Exception as e:
            self.logger.error(f"MediaCrawler search failed: {e}")
            raise
        finally:
            # 恢复原工作目录
            self._restore_original_dir()
    
    def _switch_to_mediacrawler_dir(self):
        """切换到MediaCrawler工作目录"""
        self.original_cwd = os.getcwd()
        
        # 确保使用绝对路径
        mediacrawler_abs_path = str(self.mediacrawler_path.resolve())
        self.logger.info(f"Switching from {self.original_cwd} to {mediacrawler_abs_path}")
        
        # 验证目录存在
        if not self.mediacrawler_path.exists():
            raise RuntimeError(f"MediaCrawler directory does not exist: {mediacrawler_abs_path}")
        
        os.chdir(mediacrawler_abs_path)
        
        # 添加MediaCrawler到Python路径
        if mediacrawler_abs_path not in sys.path:
            sys.path.insert(0, mediacrawler_abs_path)
            self.logger.debug(f"Added to Python path: {mediacrawler_abs_path}")
        
        # 验证切换成功
        current_dir = os.getcwd()
        if current_dir != mediacrawler_abs_path:
            raise RuntimeError(f"Failed to switch directory. Expected: {mediacrawler_abs_path}, Actual: {current_dir}")
        
        self.logger.info(f"Successfully switched to MediaCrawler directory: {current_dir}")
        
        # 验证关键文件存在
        required_files = [
            "docs/hit_stopwords.txt",
            "media_platform/zhihu/__init__.py",
            "constant/zhihu.py"
        ]
        for file_path in required_files:
            full_path = self.mediacrawler_path / file_path
            if not full_path.exists():
                self.logger.warning(f"Required file missing: {full_path}")
            else:
                self.logger.debug(f"Required file exists: {full_path}")
    
    def _restore_original_dir(self):
        """恢复原工作目录"""
        if self.original_cwd:
            os.chdir(self.original_cwd)
            self.logger.debug(f"Restored original directory: {self.original_cwd}")
    
    async def _execute_mediacrawler(self, keywords: str, max_results: int):
        """执行MediaCrawler爬取流程"""
        try:
            # 清除已有的config模块导入，避免冲突
            import sys
            if 'config' in sys.modules:
                del sys.modules['config']
            if 'config.db_config' in sys.modules:
                del sys.modules['config.db_config']
            
            # 导入MediaCrawler模块（必须在正确目录下）
            import config
            import config.db_config as db_config  # 直接导入MediaCrawler的db_config
            from media_platform.zhihu import ZhihuCrawler
            
            # 添加缺少的配置属性
            if not hasattr(config, 'CACHE_TYPE_MEMORY'):
                config.CACHE_TYPE_MEMORY = db_config.CACHE_TYPE_MEMORY
                self.logger.debug("Added CACHE_TYPE_MEMORY to config")
            
            # 配置MediaCrawler参数（基于测试验证的成功配置）
            config.PLATFORM = "zhihu"
            config.LOGIN_TYPE = "cookie"
            config.CRAWLER_TYPE = "search"
            config.KEYWORDS = keywords
            config.SAVE_DATA_OPTION = "json"
            # 从环境变量读取headless设置，默认为True（无头模式）
            headless_setting = os.getenv('ZHIHU_HEADLESS', 'true').lower() == 'true'
            config.HEADLESS = headless_setting
            config.CRAWLER_MAX_NOTES_COUNT = max_results
            config.ENABLE_GET_COMMENTS = False  # 禁用评论以提高速度
            config.COOKIES = self.zhihu_cookie
            
            self.logger.info("MediaCrawler configuration set successfully")
            
            # 创建并执行爬虫
            crawler = ZhihuCrawler()
            await crawler.start()
            
            self.logger.info("MediaCrawler execution completed")
            
        except ImportError as e:
            self.logger.error(f"Failed to import MediaCrawler modules: {e}")
            raise RuntimeError(f"MediaCrawler import failed: {e}")
        except Exception as e:
            self.logger.error(f"MediaCrawler execution failed: {e}")
            raise
    
    async def _load_and_convert_data(self) -> List[Dict[str, Any]]:
        """加载并转换MediaCrawler输出数据"""
        data_dir = self.mediacrawler_path / "data" / "zhihu" / "json"
        
        if not data_dir.exists():
            self.logger.warning("MediaCrawler data directory not found")
            return []
        
        # 查找最新的JSON文件
        json_files = list(data_dir.glob("search_contents_*.json"))
        if not json_files:
            self.logger.warning("No MediaCrawler output files found")
            return []
        
        # 获取最新文件
        latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
        self.logger.info(f"Loading data from: {latest_file}")
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            if not raw_data:
                self.logger.warning("MediaCrawler output file is empty")
                return []
            
            # 转换为标准格式
            converted_data = []
            for item in raw_data:
                converted_item = self._convert_mediacrawler_item(item)
                if converted_item:
                    converted_data.append(converted_item)
            
            self.logger.info(f"Converted {len(converted_data)} items from MediaCrawler data")
            return converted_data
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"Failed to load MediaCrawler data: {e}")
            return []
    
    def _convert_mediacrawler_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """将MediaCrawler数据项转换为标准格式"""
        try:
            # 基于实际MediaCrawler输出格式进行转换
            converted = {
                'id': item.get('content_id', ''),
                'title': item.get('title', ''),
                'content': item.get('content_text', ''),
                'url': item.get('content_url', ''),
                'platform': 'zhihu',
                'content_type': item.get('content_type', 'unknown'),
                'created_time': item.get('created_time'),
                'updated_time': item.get('updated_time'),
                'author': {
                    'id': item.get('user_id', ''),
                    'nickname': item.get('user_nickname', ''),
                    'avatar': item.get('user_avatar', ''),
                    'profile_url': item.get('user_link', '')
                },
                'stats': {
                    'voteup_count': item.get('voteup_count', 0),
                    'comment_count': item.get('comment_count', 0)
                },
                'metadata': {
                    'question_id': item.get('question_id', ''),
                    'source_keyword': item.get('source_keyword', ''),
                    'description': item.get('desc', ''),
                    'last_modify_ts': item.get('last_modify_ts')
                }
            }
            
            # 验证必需字段
            if not converted['id'] or not converted['title']:
                self.logger.warning(f"Skipping item with missing required fields: {item.get('content_id', 'unknown')}")
                return None
            
            return converted
            
        except Exception as e:
            self.logger.error(f"Failed to convert MediaCrawler item: {e}")
            return None
    
    async def get_content_details(self, content_id: str) -> Optional[Dict[str, Any]]:
        """
        获取具体内容详情
        注意：MediaCrawler主要用于搜索，详情获取需要额外实现
        """
        self.logger.info(f"Getting content details for: {content_id}")
        
        # 当前实现：从最近的搜索结果中查找
        try:
            data_dir = self.mediacrawler_path / "data" / "zhihu" / "json"
            json_files = list(data_dir.glob("search_contents_*.json"))
            
            for json_file in sorted(json_files, key=lambda f: f.stat().st_mtime, reverse=True):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for item in data:
                    if item.get('content_id') == content_id:
                        return self._convert_mediacrawler_item(item)
            
            self.logger.warning(f"Content not found in recent searches: {content_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get content details: {e}")
            return None
    
    def cleanup(self):
        """清理资源"""
        if self.original_cwd:
            os.chdir(self.original_cwd)
        
        # 移除添加的Python路径
        if str(self.mediacrawler_path) in sys.path:
            sys.path.remove(str(self.mediacrawler_path))
        
        self.logger.debug("MediaCrawler integration cleaned up")


class MediaCrawlerConfig:
    """MediaCrawler配置管理"""
    
    @staticmethod
    def get_mediacrawler_path() -> str:
        """获取MediaCrawler路径"""
        import structlog
        logger = structlog.get_logger(__name__)
        
        # 优先从环境变量获取
        path = os.getenv('MEDIACRAWLER_PATH')
        logger.debug(f"Environment MEDIACRAWLER_PATH: {path}")
        
        if path:
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(path):
                # 相对于项目根目录计算
                project_root = Path(__file__).parent.parent.parent.parent
                path = str(project_root / path)
                logger.debug(f"Converted relative path to: {path}")
            
            if Path(path).exists():
                logger.info(f"Using MediaCrawler path from environment: {path}")
                return path
            else:
                logger.warning(f"Environment path does not exist: {path}")
        
        # 默认绝对路径
        default_path = Path("/home/damian/MediaCrawler")
        if default_path.exists():
            logger.info(f"Using default MediaCrawler path: {default_path}")
            return str(default_path)
        
        # 备用相对路径
        backup_path = Path(__file__).parent.parent.parent.parent / "MediaCrawler"
        if backup_path.exists():
            logger.info(f"Using backup MediaCrawler path: {backup_path}")
            return str(backup_path)
        
        logger.error(f"MediaCrawler path not found. Tried: {path}, {default_path}, {backup_path}")
        raise ValueError(f"MediaCrawler path not found. Tried: {path}, {default_path}, {backup_path}")
    
    @staticmethod
    def get_zhihu_cookie() -> str:
        """获取知乎Cookie"""
        cookie = os.getenv('ZHIHU_COOKIE')
        if not cookie:
            raise ValueError("ZHIHU_COOKIE environment variable not set")
        return cookie


# 便捷函数
async def create_mediacrawler_integration() -> MediaCrawlerZhihuIntegration:
    """创建MediaCrawler集成实例"""
    mediacrawler_path = MediaCrawlerConfig.get_mediacrawler_path()
    zhihu_cookie = MediaCrawlerConfig.get_zhihu_cookie()
    
    return MediaCrawlerZhihuIntegration(mediacrawler_path, zhihu_cookie)