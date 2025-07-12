"""
应用配置管理模块
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """应用设置"""
    
    # 数据库配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "123456"
    mysql_db: str = "web3_tge_monitor"
    
    # AI API配置
    ai_api_base_url: str = "api.gpt.ge"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o"
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
    mediacrawler_path: str = "../MediaCrawler"
    mediacrawler_enable_proxy: bool = False
    mediacrawler_headless: bool = True
    mediacrawler_save_data: bool = True
    
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
    def database_url(self) -> str:
        """构建数据库连接URL"""
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
    
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