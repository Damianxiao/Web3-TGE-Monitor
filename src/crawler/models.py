"""
爬虫数据模型
统一的数据格式，支持多平台扩展
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, validator
from enum import Enum


class ContentType(str, Enum):
    """内容类型枚举"""
    TEXT = "text"
    VIDEO = "video"
    IMAGE = "image"
    MIXED = "mixed"


class Platform(str, Enum):
    """支持的平台枚举"""
    XHS = "xhs"          # 小红书
    DOUYIN = "douyin"    # 抖音
    WEIBO = "weibo"      # 微博
    BILIBILI = "bilibili" # B站
    ZHIHU = "zhihu"      # 知乎
    

class RawContent(BaseModel):
    """
    统一的原始内容数据模型
    所有平台的爬取数据都转换为此格式
    """
    # 基础标识
    platform: Platform
    content_id: str
    content_type: ContentType
    
    # 内容信息
    title: str
    content: str                    # 主要文本内容
    raw_content: str               # 原始完整内容（包含格式）
    
    # 作者信息
    author_id: str
    author_name: str
    author_avatar: Optional[str] = None
    
    # 时间信息
    publish_time: datetime
    crawl_time: datetime
    last_update_time: Optional[datetime] = None
    
    # 互动数据
    like_count: Optional[int] = 0
    comment_count: Optional[int] = 0
    share_count: Optional[int] = 0
    collect_count: Optional[int] = 0
    
    # 媒体资源
    image_urls: List[str] = []
    video_urls: List[str] = []
    
    # 标签和分类
    tags: List[str] = []
    hashtags: List[str] = []
    
    # 链接信息
    source_url: str
    
    # 位置信息
    ip_location: Optional[str] = None
    
    # 平台特有数据
    platform_metadata: Dict[str, Any] = {}
    
    # 爬取元信息
    source_keywords: List[str] = []
    crawl_batch_id: Optional[str] = None
    
    @validator('publish_time', 'crawl_time', pre=True)
    def parse_timestamp(cls, v):
        """解析时间戳"""
        if isinstance(v, int):
            # 毫秒时间戳
            if v > 10**12:
                return datetime.fromtimestamp(v / 1000)
            # 秒时间戳
            else:
                return datetime.fromtimestamp(v)
        return v
    
    @validator('like_count', 'comment_count', 'share_count', 'collect_count', pre=True)
    def parse_count(cls, v):
        """解析数量字段（处理中文数字如'1.2万'）"""
        if isinstance(v, str):
            if '万' in v:
                return int(float(v.replace('万', '')) * 10000)
            elif '千' in v:
                return int(float(v.replace('千', '')) * 1000)
            elif v.isdigit():
                return int(v)
            else:
                return 0
        return v or 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.dict()
    
    def get_display_content(self, max_length: int = 200) -> str:
        """获取用于显示的内容摘要"""
        display_text = self.content or self.title
        if len(display_text) > max_length:
            return display_text[:max_length] + "..."
        return display_text


class CrawlTask(BaseModel):
    """爬取任务模型"""
    task_id: str
    platform: Platform
    keywords: List[str]
    max_count: int = 50
    created_at: datetime
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None
    result_count: int = 0


class CrawlResult(BaseModel):
    """爬取结果模型"""
    task_id: str
    platform: Platform
    contents: List[RawContent]
    total_count: int
    success_count: int
    duplicate_count: int = 0
    error_count: int = 0
    execution_time: float
    keywords_used: List[str]
    
    def get_summary(self) -> Dict[str, Any]:
        """获取结果摘要"""
        return {
            "task_id": self.task_id,
            "platform": self.platform,
            "total_found": self.total_count,
            "success_saved": self.success_count,
            "duplicates_skipped": self.duplicate_count,
            "errors": self.error_count,
            "execution_time": f"{self.execution_time:.2f}s",
            "keywords": self.keywords_used
        }