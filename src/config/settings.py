"""
应用配置管理模块
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator, validator
import re


class Settings(BaseSettings):
    """应用设置"""
    
    # 数据库配置
    database_url: str = "mysql+aiomysql://root:123456@localhost:3306/web3_tge_monitor"
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "123456"
    mysql_db: str = "web3_tge_monitor"
    
    # AI API配置
    ai_api_base_url: str = "api.gpt.ge"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_max_tokens: int = 1688
    ai_temperature: float = 0.5
    
    # 应用配置
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = True
    log_level: str = "INFO"
    
    # Redis配置
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    
    # MediaCrawler配置
    mediacrawler_path: str = "./external/MediaCrawler"
    mediacrawler_enable_proxy: bool = False
    mediacrawler_headless: bool = True
    mediacrawler_save_data: bool = True
    
    # XHS (小红书) 平台配置
    xhs_cookie: str = ""
    xhs_search_type: str = "综合"
    xhs_max_pages: int = 10
    xhs_rate_limit: int = 60
    xhs_enabled: bool = True
    xhs_login_method: str = "cookie"
    xhs_headless: bool = True
    
    # Douyin (抖音) 平台配置
    douyin_cookie: str = ""
    douyin_max_pages: int = 10
    douyin_rate_limit: int = 60
    douyin_enabled: bool = True
    douyin_login_method: str = "cookie"
    douyin_headless: bool = True
    
    # Bilibili (B站) 平台配置
    bilibili_cookie: str = ""
    bilibili_max_pages: int = 10
    bilibili_rate_limit: int = 60
    bilibili_enabled: bool = True
    bilibili_login_method: str = "cookie"
    bilibili_headless: bool = True
    
    # Weibo (微博) 平台配置
    weibo_cookie: str = ""
    weibo_search_type: str = "综合"
    weibo_max_pages: int = 10
    weibo_rate_limit: int = 60
    weibo_enabled: bool = True
    weibo_login_method: str = "cookie"
    weibo_headless: bool = True
    
    # Zhihu (知乎) 平台配置
    zhihu_cookie: str = ""
    zhihu_search_type: str = "综合"
    zhihu_max_pages: int = 10
    zhihu_rate_limit: int = 60
    zhihu_enabled: bool = True
    zhihu_login_method: str = "cookie"
    zhihu_headless: bool = True
    
    # Kuaishou (快手) 平台配置
    kuaishou_cookie: str = ""
    kuaishou_max_pages: int = 10
    kuaishou_rate_limit: int = 60
    kuaishou_enabled: bool = True
    kuaishou_login_method: str = "cookie"
    kuaishou_headless: bool = True
    
    # Tieba (百度贴吧) 平台配置
    tieba_cookie: str = ""
    tieba_max_pages: int = 10
    tieba_rate_limit: int = 60
    tieba_enabled: bool = True
    tieba_login_method: str = "cookie"
    tieba_headless: bool = True
    
    @field_validator('zhihu_headless', 'xhs_headless', 'douyin_headless', 'bilibili_headless', 'weibo_headless', 'kuaishou_headless', 'tieba_headless', mode='before')
    @classmethod
    def parse_boolean_with_comments(cls, v):
        """解析可能带有注释的布尔值"""
        if isinstance(v, str):
            # 移除注释部分（# 之后的内容）
            v = re.sub(r'\s*#.*$', '', v).strip()
            # 处理常见的字符串布尔值
            if v.lower() in ['true', '1', 'yes', 'on']:
                return True
            elif v.lower() in ['false', '0', 'no', 'off']:
                return False
        return v
    
    @field_validator('zhihu_enabled', 'xhs_enabled', 'douyin_enabled', 'bilibili_enabled', 'weibo_enabled', 'kuaishou_enabled', 'tieba_enabled', mode='before')
    @classmethod
    def parse_enabled_with_comments(cls, v):
        """解析可能带有注释的启用状态"""
        if isinstance(v, str):
            # 移除注释部分（# 之后的内容）
            v = re.sub(r'\s*#.*$', '', v).strip()
            # 处理常见的字符串布尔值
            if v.lower() in ['true', '1', 'yes', 'on']:
                return True
            elif v.lower() in ['false', '0', 'no', 'off']:
                return False
        return v
    
    @field_validator('zhihu_search_type', 'xhs_search_type', 'weibo_search_type', 'zhihu_login_method', 'xhs_login_method', 'douyin_login_method', 'bilibili_login_method', 'weibo_login_method', 'kuaishou_login_method', 'tieba_login_method', mode='before')
    @classmethod
    def parse_string_with_comments(cls, v):
        """解析可能带有注释的字符串值"""
        if isinstance(v, str):
            # 移除注释部分（# 之后的内容）
            v = re.sub(r'\s*#.*$', '', v).strip()
            # 移除引号
            v = v.strip('"\'')
        return v
    
    @field_validator('mediacrawler_path')
    @classmethod
    def validate_mediacrawler_path(cls, v):
        """验证MediaCrawler路径"""
        if not v:
            return v
        
        from pathlib import Path
        path = Path(v)
        
        # 如果是相对路径，转换为绝对路径
        if not path.is_absolute():
            # 相对于项目根目录
            project_root = Path(__file__).parent.parent.parent
            path = (project_root / v).resolve()
        
        return str(path)
    
    # 爬虫配置
    crawler_max_pages: int = 5
    crawler_delay_seconds: int = 3
    data_retention_days: int = 30
    
    # Web3关键词
    web3_keywords: str = "TGE,代币发行,空投,IDO,新币上线,DeFi,Web3项目,撸毛,开启测试网,速撸"
    
    @field_validator('web3_keywords')
    @classmethod
    def parse_keywords(cls, v):
        if isinstance(v, str):
            return [keyword.strip() for keyword in v.split(',') if keyword.strip()]
        return v
    
    @property
    def redis_url(self) -> str:
        """构建Redis连接URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow"
    }


# 全局设置实例
settings = Settings()

# AI配置字典（用于AI模块）
ai_config = {
    'api_url': f"https://{settings.ai_api_base_url}/v1/chat/completions",
    'api_key': settings.ai_api_key,
    'model': settings.ai_model,
    'max_tokens': settings.ai_max_tokens,
    'temperature': settings.ai_temperature,
    'timeout': 30
}