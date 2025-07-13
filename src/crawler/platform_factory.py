"""
平台工厂类
负责管理和创建不同平台的爬虫实例
"""
from typing import Dict, Type, List, Optional
import structlog

from .base_platform import AbstractPlatform
from .models import Platform
from ..config.settings import settings

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
                'rate_limit': {
                    'requests_per_minute': 25,
                    'delay_between_requests': 2.5
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
    
    # 可以继续添加其他平台的自动注册
    # try:
    #     from .platforms.douyin_platform import DouyinPlatform
    #     PlatformFactory.register(Platform.DOUYIN, DouyinPlatform)
    # except ImportError:
    #     pass
    
    logger.info("Auto registration completed", 
               registered_count=len(PlatformFactory.get_registered_platforms()))