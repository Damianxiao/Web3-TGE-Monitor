"""
去重工具模块
"""
import hashlib
from typing import List, Set, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class DeduplicationService:
    """去重服务"""
    
    def __init__(self):
        self._content_hashes: Set[str] = set()
        self._project_time_windows: dict = {}  # project_name -> last_seen_time
    
    @staticmethod
    def generate_content_hash(content: str) -> str:
        """
        生成内容hash用于去重
        
        Args:
            content: 原始内容文本
            
        Returns:
            MD5 hash字符串
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def extract_project_name(content: str, title: str = "") -> Optional[str]:
        """
        从内容中提取项目名称
        
        Args:
            content: 文本内容
            title: 标题（如果有）
            
        Returns:
            提取的项目名称，如果无法提取则返回None
        """
        # 简单的项目名称提取逻辑
        # 在实际应用中可能需要更复杂的NLP处理
        
        # 首先检查标题
        if title:
            # 查找常见的项目名称模式
            import re
            
            # 匹配 "XXX Token"、"XXX Protocol"、"XXX项目" 等模式
            patterns = [
                r'([A-Za-z]+)\s+(?:Token|Protocol|Network|Finance|Swap)',
                r'([A-Za-z\u4e00-\u9fa5]+)(?:代币|项目|协议|网络)',
                r'([A-Z][a-z]+[A-Z][a-z]+)',  # CamelCase
            ]
            
            for pattern in patterns:
                match = re.search(pattern, title)
                if match:
                    return match.group(1)
        
        # 如果标题没有找到，再检查内容
        # 这里可以添加更复杂的提取逻辑
        
        return None
    
    def is_duplicate_by_hash(self, content_hash: str) -> bool:
        """
        检查内容hash是否重复
        
        Args:
            content_hash: 内容hash
            
        Returns:
            是否重复
        """
        if content_hash in self._content_hashes:
            logger.info("Duplicate content detected by hash", content_hash=content_hash)
            return True
        
        self._content_hashes.add(content_hash)
        return False
    
    def is_duplicate_by_project_time(self, project_name: str, time_window_hours: int = 24) -> bool:
        """
        检查项目是否在时间窗口内重复
        
        Args:
            project_name: 项目名称
            time_window_hours: 时间窗口（小时）
            
        Returns:
            是否重复
        """
        if not project_name:
            return False
        
        now = datetime.utcnow()
        
        if project_name in self._project_time_windows:
            last_seen = self._project_time_windows[project_name]
            time_diff = now - last_seen
            
            if time_diff < timedelta(hours=time_window_hours):
                logger.info(
                    "Duplicate project detected within time window",
                    project_name=project_name,
                    last_seen=last_seen,
                    time_diff_hours=time_diff.total_seconds() / 3600
                )
                return True
        
        self._project_time_windows[project_name] = now
        return False
    
    def check_content_similarity(self, content1: str, content2: str, threshold: float = 0.8) -> bool:
        """
        检查内容相似度
        
        Args:
            content1: 内容1
            content2: 内容2
            threshold: 相似度阈值
            
        Returns:
            是否相似
        """
        # 简单的相似度计算（基于Jaccard相似度）
        def get_words(text: str) -> Set[str]:
            return set(text.lower().split())
        
        words1 = get_words(content1)
        words2 = get_words(content2)
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        
        if similarity >= threshold:
            logger.info(
                "Similar content detected",
                similarity=similarity,
                threshold=threshold
            )
            return True
        
        return False
    
    def cleanup_old_entries(self, days: int = 7) -> None:
        """
        清理过期的去重记录
        
        Args:
            days: 保留天数
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # 清理过期的项目时间窗口记录
        expired_projects = [
            project for project, last_seen in self._project_time_windows.items()
            if last_seen < cutoff_time
        ]
        
        for project in expired_projects:
            del self._project_time_windows[project]
        
        logger.info(
            "Cleaned up old deduplication entries",
            expired_count=len(expired_projects),
            cutoff_days=days
        )


# 全局去重服务实例
deduplication_service = DeduplicationService()


def is_duplicate_content(content: str, title: str = "", check_similarity: bool = False) -> bool:
    """
    综合去重检查
    
    Args:
        content: 内容文本
        title: 标题（可选）
        check_similarity: 是否检查相似度
        
    Returns:
        是否重复
    """
    # 1. 生成并检查内容hash
    content_hash = deduplication_service.generate_content_hash(content)
    if deduplication_service.is_duplicate_by_hash(content_hash):
        return True
    
    # 2. 检查项目时间窗口
    project_name = deduplication_service.extract_project_name(content, title)
    if project_name and deduplication_service.is_duplicate_by_project_time(project_name):
        return True
    
    # 3. 如果需要，检查内容相似度（暂时跳过，性能考虑）
    # if check_similarity:
    #     # 这里可以与最近的内容进行相似度比较
    #     pass
    
    return False