"""
微博客户端接口定义
定义统一的微博客户端接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class WeiboClientInterface(ABC):
    """微博客户端接口"""
    
    @abstractmethod
    async def initialize(self):
        """初始化客户端"""
        pass
    
    @abstractmethod
    async def login_with_qrcode(self):
        """使用二维码登录"""
        pass
    
    @abstractmethod
    async def get_note_by_keyword(self, keyword: str, page: int = 1, search_type=None) -> Dict[str, Any]:
        """
        根据关键词搜索微博内容
        
        Args:
            keyword: 搜索关键词
            page: 页数
            search_type: 搜索类型
            
        Returns:
            包含搜索结果的字典
        """
        pass
    
    @abstractmethod
    async def close(self):
        """关闭客户端"""
        pass