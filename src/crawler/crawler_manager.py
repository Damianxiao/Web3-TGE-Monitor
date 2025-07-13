"""
爬虫管理器
统一管理多平台爬虫任务的调度和执行
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import structlog

from crawler.models import Platform, CrawlTask, CrawlResult, RawContent
from crawler.platform_factory import PlatformFactory
from utils.deduplication import deduplication_service
from config.keywords import get_all_keywords

logger = structlog.get_logger()


class CrawlerManager:
    """爬虫管理器"""
    
    def __init__(self):
        self.active_tasks: Dict[str, CrawlTask] = {}
        self.task_results: Dict[str, CrawlResult] = {}
        self._task_lock = asyncio.Lock()
    
    async def submit_crawl_task(
        self,
        platform: Platform,
        keywords: List[str] = None,
        max_count: int = 50,
        **kwargs
    ) -> str:
        """
        提交爬取任务
        
        Args:
            platform: 目标平台
            keywords: 关键词列表，如果为空则使用默认Web3关键词
            max_count: 最大爬取数量
            **kwargs: 其他参数
            
        Returns:
            任务ID
        """
        # 使用默认关键词如果未提供
        if not keywords:
            keywords = get_all_keywords()[:5]  # 使用前5个核心关键词
        
        task_id = str(uuid.uuid4())
        task = CrawlTask(
            task_id=task_id,
            platform=platform,
            keywords=keywords,
            max_count=max_count,
            created_at=datetime.utcnow()
        )
        
        async with self._task_lock:
            self.active_tasks[task_id] = task
        
        logger.info("Crawl task submitted", 
                   task_id=task_id, 
                   platform=platform.value,
                   keywords=keywords[:3])  # 只记录前3个关键词
        
        return task_id
    
    async def execute_task(self, task_id: str) -> CrawlResult:
        """
        执行爬取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            爬取结果
        """
        if task_id not in self.active_tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.active_tasks[task_id]
        start_time = datetime.utcnow()
        
        try:
            # 更新任务状态
            task.status = "running"
            
            # 创建平台实例
            platform_instance = await PlatformFactory.create_platform(task.platform)
            
            # 执行爬取
            raw_contents = await platform_instance.crawl(
                keywords=task.keywords,
                max_count=task.max_count
            )
            
            # 数据处理和去重
            processed_contents = await self._process_contents(raw_contents, task)
            
            # 计算执行时间
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 创建结果
            result = CrawlResult(
                task_id=task_id,
                platform=task.platform,
                contents=processed_contents,
                total_count=len(raw_contents),
                success_count=len(processed_contents),
                duplicate_count=len(raw_contents) - len(processed_contents),
                execution_time=execution_time,
                keywords_used=task.keywords
            )
            
            # 更新任务状态
            task.status = "completed"
            task.result_count = len(processed_contents)
            
            # 保存结果
            self.task_results[task_id] = result
            
            logger.info("Crawl task completed",
                       task_id=task_id,
                       platform=task.platform.value,
                       total_found=result.total_count,
                       success_saved=result.success_count,
                       execution_time=result.execution_time)
            
            return result
            
        except Exception as e:
            # 处理错误
            task.status = "failed"
            task.error_message = str(e)
            
            logger.error("Crawl task failed",
                        task_id=task_id,
                        platform=task.platform.value,
                        error=str(e))
            
            # 创建失败结果
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            result = CrawlResult(
                task_id=task_id,
                platform=task.platform,
                contents=[],
                total_count=0,
                success_count=0,
                error_count=1,
                execution_time=execution_time,
                keywords_used=task.keywords
            )
            
            self.task_results[task_id] = result
            raise
    
    async def _process_contents(self, contents: List[RawContent], task: CrawlTask) -> List[RawContent]:
        """
        处理爬取内容（去重、过滤等）
        
        Args:
            contents: 原始内容列表
            task: 爬取任务
            
        Returns:
            处理后的内容列表
        """
        processed = []
        
        for content in contents:
            # 去重检查
            content_text = f"{content.title} {content.content}"
            content_hash = deduplication_service.generate_content_hash(content_text)
            
            if deduplication_service.is_duplicate_by_hash(content_hash):
                logger.debug("Duplicate content skipped", content_id=content.content_id)
                continue
            
            # Web3关键词匹配检查
            if self._contains_web3_keywords(content_text):
                # 添加爬取元信息
                content.source_keywords = task.keywords
                content.crawl_batch_id = task.task_id
                content.crawl_time = datetime.utcnow()
                
                processed.append(content)
            else:
                logger.debug("Content filtered - no Web3 keywords", content_id=content.content_id)
        
        return processed
    
    def _contains_web3_keywords(self, text: str) -> bool:
        """检查文本是否包含Web3关键词"""
        web3_keywords = get_all_keywords()
        text_lower = text.lower()
        
        # 检查是否包含任何Web3关键词
        for keyword in web3_keywords:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    async def get_task_status(self, task_id: str) -> Optional[CrawlTask]:
        """获取任务状态"""
        return self.active_tasks.get(task_id)
    
    async def get_task_result(self, task_id: str) -> Optional[CrawlResult]:
        """获取任务结果"""
        return self.task_results.get(task_id)
    
    async def list_active_tasks(self) -> List[CrawlTask]:
        """列出活跃任务"""
        return list(self.active_tasks.values())

    async def get_tasks(self, status: str = None, platform: Platform = None, limit: int = 50) -> List[CrawlTask]:
        """
        获取任务列表，支持过滤

        Args:
            status: 任务状态过滤
            platform: 平台过滤
            limit: 返回数量限制

        Returns:
            任务列表
        """
        tasks = list(self.active_tasks.values())

        # 按状态过滤
        if status:
            tasks = [task for task in tasks if task.status == status]

        # 按平台过滤
        if platform:
            tasks = [task for task in tasks if task.platform == platform]

        # 按创建时间倒序排序
        tasks.sort(key=lambda x: x.created_at, reverse=True)

        # 限制返回数量
        return tasks[:limit]
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            if task.status not in ["completed", "failed", "cancelled"]:
                task.status = "cancelled"
                logger.info("Task cancelled", task_id=task_id)
                return True
        return False
    
    async def cleanup_old_tasks(self, hours: int = 24):
        """清理旧任务"""
        cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
        
        tasks_to_remove = []
        for task_id, task in self.active_tasks.items():
            if task.created_at.timestamp() < cutoff_time:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.active_tasks[task_id]
            if task_id in self.task_results:
                del self.task_results[task_id]
        
        logger.info("Old tasks cleaned up", removed_count=len(tasks_to_remove))


# 全局爬虫管理器实例
crawler_manager = CrawlerManager()