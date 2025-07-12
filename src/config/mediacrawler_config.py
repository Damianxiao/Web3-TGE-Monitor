"""
MediaCrawler配置管理工具
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class MediaCrawlerConfig:
    """MediaCrawler配置管理器"""
    
    def __init__(self, settings=None):
        self.settings = settings
        self._mediacrawler_path = None
        
    @property
    def mediacrawler_path(self) -> str:
        """获取MediaCrawler路径"""
        if self._mediacrawler_path is None:
            self._mediacrawler_path = self._resolve_mediacrawler_path()
        return self._mediacrawler_path
    
    def _resolve_mediacrawler_path(self) -> str:
        """
        智能解析MediaCrawler路径
        
        优先级:
        1. 环境变量 MEDIACRAWLER_PATH
        2. settings配置
        3. 相对路径查找
        4. 默认路径
        """
        # 环境变量优先
        env_path = os.environ.get('MEDIACRAWLER_PATH')
        if env_path:
            path = Path(env_path).resolve()
            if self._validate_mediacrawler_path(path):
                logger.info("Using MediaCrawler from environment variable", path=str(path))
                return str(path)
            else:
                logger.warning("Environment MEDIACRAWLER_PATH invalid", path=str(path))
        
        # Settings配置
        if self.settings and hasattr(self.settings, 'mediacrawler_path'):
            settings_path = Path(self.settings.mediacrawler_path).resolve()
            if self._validate_mediacrawler_path(settings_path):
                logger.info("Using MediaCrawler from settings", path=str(settings_path))
                return str(settings_path)
            else:
                logger.warning("Settings mediacrawler_path invalid", path=str(settings_path))
        
        # 相对路径查找
        project_root = Path(__file__).parent.parent.parent  # 回到项目根目录
        relative_paths = [
            project_root.parent / "MediaCrawler",  # 平行目录 (最常见)
            project_root / "MediaCrawler",         # 子目录
            project_root / "external" / "MediaCrawler",  # external目录
            project_root / "third_party" / "MediaCrawler",  # third_party目录
        ]
        
        for path in relative_paths:
            if self._validate_mediacrawler_path(path):
                logger.info("Found MediaCrawler at relative path", path=str(path))
                return str(path.resolve())
        
        # 默认路径作为最后的fallback
        default_paths = [
            "/home/damian/MediaCrawler",
            str(Path.home() / "MediaCrawler"),
            "/opt/MediaCrawler"
        ]
        
        for default_path in default_paths:
            if self._validate_mediacrawler_path(default_path):
                logger.info("Using default MediaCrawler path", path=default_path)
                return default_path
        
        raise RuntimeError(
            "MediaCrawler not found. Please:\n"
            "1. Set MEDIACRAWLER_PATH environment variable, or\n"
            "2. Update mediacrawler_path in settings, or\n"
            "3. Place MediaCrawler in a relative path from project root"
        )
    
    def _validate_mediacrawler_path(self, path) -> bool:
        """验证MediaCrawler路径是否有效"""
        try:
            path = Path(path)
            if not (path.exists() and path.is_dir()):
                return False
            
            # 检查必需的核心文件
            required_files = [
                path / "media_platform" / "xhs" / "core.py",
                path / "media_platform" / "xhs" / "client.py", 
                path / "base" / "base_crawler.py"
            ]
            
            return all(f.exists() and f.is_file() for f in required_files)
        except Exception:
            return False
    
    def get_platform_config(self, platform: str = "xhs") -> Dict[str, Any]:
        """获取平台特定配置"""
        config = {
            'mediacrawler_path': self.mediacrawler_path,
            'headless': getattr(self.settings, 'mediacrawler_headless', True),
            'enable_proxy': getattr(self.settings, 'mediacrawler_enable_proxy', False),
            'save_data': getattr(self.settings, 'mediacrawler_save_data', True),
        }
        
        return config
    
    def validate_installation(self) -> bool:
        """验证MediaCrawler安装是否完整"""
        try:
            # 验证路径
            if not self._validate_mediacrawler_path(self.mediacrawler_path):
                logger.error("MediaCrawler path validation failed", path=self.mediacrawler_path)
                return False
            
            # 验证Python模块导入
            import sys
            if self.mediacrawler_path not in sys.path:
                sys.path.insert(0, self.mediacrawler_path)
            
            # 尝试导入关键模块
            try:
                from media_platform.xhs import client, core
                from base.base_crawler import AbstractCrawler
                logger.info("MediaCrawler modules imported successfully")
                return True
            except ImportError as e:
                logger.error("Failed to import MediaCrawler modules", error=str(e))
                return False
                
        except Exception as e:
            logger.error("MediaCrawler validation failed", error=str(e))
            return False