"""
平台工厂类
负责管理和创建不同平台的爬虫实例
"""
from typing import Dict, Type, List, Optional
import structlog

from crawler.base_platform import AbstractPlatform
from crawler.models import Platform
from config.settings import settings

logger = structlog.get_logger()


class PlatformFactory:
    """平台工厂类"""
    
    _platforms: Dict[Platform, Type[AbstractPlatform]] = {}
    _instances: Dict[Platform, AbstractPlatform] = {}
    
    @classmethod
    def register(cls, platform: Platform, platform_class: Type[AbstractPlatform]):
        """
        注册平台类
        
        Args:
            platform: 平台枚举
            platform_class: 平台实现类
        """
        cls._platforms[platform] = platform_class
        logger.info("Platform registered", platform=platform.value)
    
    @classmethod
    def unregister(cls, platform: Platform):
        """注销平台"""
        if platform in cls._platforms:
            del cls._platforms[platform]
            if platform in cls._instances:
                del cls._instances[platform]
            logger.info("Platform unregistered", platform=platform.value)
    
    @classmethod
    async def create_platform(cls, platform: Platform, config: Dict = None) -> AbstractPlatform:
        """
        创建平台实例
        
        Args:
            platform: 平台枚举
            config: 平台配置
            
        Returns:
            平台实例
        """
        if platform not in cls._platforms:
            raise ValueError(f"Platform {platform} not registered")
        
        # 使用单例模式，避免重复创建
        if platform in cls._instances:
            return cls._instances[platform]
        
        platform_class = cls._platforms[platform]
        platform_config = config or cls._get_platform_config(platform)
        
        instance = platform_class(platform_config)
        
        # 检查平台是否可用
        if not await instance.is_available():
            raise RuntimeError(f"Platform {platform} is not available")
        
        cls._instances[platform] = instance
        logger.info("Platform instance created", platform=platform.value)
        
        return instance
    
    @classmethod
    def get_registered_platforms(cls) -> List[Platform]:
        """获取已注册的平台列表"""
        return list(cls._platforms.keys())
    
    @classmethod
    def is_platform_registered(cls, platform: Platform) -> bool:
        """检查平台是否已注册"""
        return platform in cls._platforms
    
    @classmethod
    async def get_available_platforms(cls) -> List[Platform]:
        """获取可用的平台列表"""
        available = []
        
        for platform in cls._platforms.keys():
            try:
                instance = await cls.create_platform(platform)
                if await instance.is_available():
                    available.append(platform)
            except Exception as e:
                logger.warning("Platform not available", 
                              platform=platform.value, 
                              error=str(e))
        
        return available
    
    @classmethod
    def _get_platform_config(cls, platform: Platform) -> Dict:
        """获取平台配置"""
        # 从全局设置中获取平台特定配置
        platform_configs = {
            Platform.XHS: {
                'mediacrawler_path': settings.mediacrawler_path,
                'xhs_cookie': settings.xhs_cookie,
                'xhs_search_type': settings.xhs_search_type,
                'xhs_max_pages': settings.xhs_max_pages,
                'xhs_rate_limit': settings.xhs_rate_limit,
                'xhs_enabled': settings.xhs_enabled,
                'xhs_login_method': settings.xhs_login_method,
                'xhs_headless': settings.xhs_headless,
                'rate_limit': {
                    'requests_per_minute': 20,
                    'delay_between_requests': 3.0
                },
                'retry': {
                    'max_retries': 3,
                    'backoff_factor': 2.0
                }
            },
            Platform.DOUYIN: {
                'rate_limit': {
                    'requests_per_minute': 15,
                    'delay_between_requests': 4.0
                }
            },
            Platform.WEIBO: {
                'mediacrawler_path': settings.mediacrawler_path,
                'weibo_cookie': getattr(settings, 'weibo_cookie', ''),
                'weibo_search_type': getattr(settings, 'weibo_search_type', '综合'),
                'weibo_max_pages': getattr(settings, 'weibo_max_pages', 10),
                'weibo_rate_limit': getattr(settings, 'weibo_rate_limit', 60),
                'weibo_enabled': getattr(settings, 'weibo_enabled', True),
                'weibo_login_method': getattr(settings, 'weibo_login_method', 'cookie'),
                'weibo_headless': getattr(settings, 'weibo_headless', True),
                'rate_limit': {
                    'requests_per_minute': 25,
                    'delay_between_requests': 2.5
                },
                'retry': {
                    'max_retries': 3,
                    'backoff_factor': 2.0
                }
            },
            Platform.DOUYIN: {
                'mediacrawler_path': settings.mediacrawler_path,
                'douyin_cookie': getattr(settings, 'douyin_cookie', ''),
                'douyin_max_pages': getattr(settings, 'douyin_max_pages', 10),
                'douyin_rate_limit': getattr(settings, 'douyin_rate_limit', 60),
                'douyin_enabled': getattr(settings, 'douyin_enabled', True),
                'douyin_login_method': getattr(settings, 'douyin_login_method', 'cookie'),
                'douyin_headless': getattr(settings, 'douyin_headless', True),
                'rate_limit': {
                    'requests_per_minute': 20,
                    'delay_between_requests': 3.0
                },
                'retry': {
                    'max_retries': 3,
                    'backoff_factor': 2.0
                }
            },
            Platform.BILIBILI: {
                'mediacrawler_path': settings.mediacrawler_path,
                'bilibili_cookie': getattr(settings, 'bilibili_cookie', ''),
                'bilibili_max_pages': getattr(settings, 'bilibili_max_pages', 10),
                'bilibili_rate_limit': getattr(settings, 'bilibili_rate_limit', 60),
                'bilibili_enabled': getattr(settings, 'bilibili_enabled', True),
                'bilibili_login_method': getattr(settings, 'bilibili_login_method', 'cookie'),
                'bilibili_headless': getattr(settings, 'bilibili_headless', True),
                'rate_limit': {
                    'requests_per_minute': 25,
                    'delay_between_requests': 2.5
                },
                'retry': {
                    'max_retries': 3,
                    'backoff_factor': 2.0
                }
            },
            Platform.KUAISHOU: {
                'mediacrawler_path': settings.mediacrawler_path,
                'kuaishou_cookie': getattr(settings, 'kuaishou_cookie', ''),
                'kuaishou_max_pages': getattr(settings, 'kuaishou_max_pages', 10),
                'kuaishou_rate_limit': getattr(settings, 'kuaishou_rate_limit', 60),
                'kuaishou_enabled': getattr(settings, 'kuaishou_enabled', True),
                'kuaishou_login_method': getattr(settings, 'kuaishou_login_method', 'cookie'),
                'kuaishou_headless': getattr(settings, 'kuaishou_headless', True),
                'rate_limit': {
                    'requests_per_minute': 20,
                    'delay_between_requests': 3.0
                },
                'retry': {
                    'max_retries': 3,
                    'backoff_factor': 2.0
                }
            },
            Platform.TIEBA: {
                'mediacrawler_path': settings.mediacrawler_path,
                'tieba_cookie': getattr(settings, 'tieba_cookie', ''),
                'tieba_max_pages': getattr(settings, 'tieba_max_pages', 10),
                'tieba_rate_limit': getattr(settings, 'tieba_rate_limit', 60),
                'tieba_enabled': getattr(settings, 'tieba_enabled', True),
                'tieba_login_method': getattr(settings, 'tieba_login_method', 'cookie'),
                'tieba_headless': getattr(settings, 'tieba_headless', True),
                'rate_limit': {
                    'requests_per_minute': 25,
                    'delay_between_requests': 2.5
                },
                'retry': {
                    'max_retries': 3,
                    'backoff_factor': 2.0
                }
            }
        }
        
        return platform_configs.get(platform, {})
    
    @classmethod
    def clear_instances(cls):
        """清理所有实例（用于测试和重置）"""
        cls._instances.clear()
        logger.info("All platform instances cleared")


# 自动发现和注册平台
def auto_register_platforms():
    """自动发现并注册可用的平台"""
    try:
        # 尝试导入和注册XHS平台
        from .platforms.xhs_platform import XHSPlatform
        PlatformFactory.register(Platform.XHS, XHSPlatform)
    except ImportError as e:
        logger.warning("Failed to register XHS platform", error=str(e))
    
    # 注册微博平台
    try:
        from .platforms.weibo_platform import WeiboPlatform
        PlatformFactory.register(Platform.WEIBO, WeiboPlatform)
    except ImportError as e:
        logger.warning("Failed to register Weibo platform", error=str(e))
    
    # 注册知乎平台
    try:
        from .platforms.zhihu_platform import ZhihuPlatform
        PlatformFactory.register(Platform.ZHIHU, ZhihuPlatform)
        logger.info("Platform registered", platform="zhihu")
    except ImportError as e:
        logger.warning("Failed to register Zhihu platform", error=str(e))
    
    # 注册抖音平台
    try:
        from .platforms.douyin_platform import DouyinPlatform
        PlatformFactory.register(Platform.DOUYIN, DouyinPlatform)
        logger.info("Platform registered", platform="douyin")
    except ImportError as e:
        logger.warning("Failed to register Douyin platform", error=str(e))
    
    # 注册B站平台
    try:
        from .platforms.bilibili_platform import BilibiliPlatform
        PlatformFactory.register(Platform.BILIBILI, BilibiliPlatform)
        logger.info("Platform registered", platform="bilibili")
    except ImportError as e:
        logger.warning("Failed to register Bilibili platform", error=str(e))
    
    # 注册快手平台
    try:
        from .platforms.kuaishou_platform import KuaishouPlatform
        PlatformFactory.register(Platform.KUAISHOU, KuaishouPlatform)
        logger.info("Platform registered", platform="kuaishou")
    except ImportError as e:
        logger.warning("Failed to register Kuaishou platform", error=str(e))
    
    # 注册贴吧平台
    try:
        from .platforms.tieba_platform import TiebaPlatform
        PlatformFactory.register(Platform.TIEBA, TiebaPlatform)
        logger.info("Platform registered", platform="tieba")
    except ImportError as e:
        logger.warning("Failed to register Tieba platform", error=str(e))
    
    # 可以继续添加其他平台的自动注册
    # try:
    #     from .platforms.douyin_platform import DouyinPlatform
    #     PlatformFactory.register(Platform.DOUYIN, DouyinPlatform)
    # except ImportError:
    #     pass
    
    logger.info("Auto registration completed", 
               registered_count=len(PlatformFactory.get_registered_platforms()))