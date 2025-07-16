"""
批次爬虫管理器
管理多平台爬虫任务的批次执行
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import structlog

from .models import Platform
from .crawler_manager import crawler_manager
from ..ai import ai_processing_manager

logger = structlog.get_logger()


class BatchCrawlManager:
    """批次爬虫管理器"""
    
    def __init__(self):
        self.active_batches: Dict[str, Dict] = {}
        self._batch_lock = asyncio.Lock()
    
    async def create_batch_crawl(
        self,
        platforms: Optional[List[Platform]] = None,
        keywords: List[str] = None,
        max_count_per_platform: int = 20,
        enable_ai_analysis: bool = True,
        **kwargs
    ) -> str:
        """
        创建批次爬虫任务
        
        Args:
            platforms: 目标平台列表，空则使用所有可用平台
            keywords: 关键词列表
            max_count_per_platform: 每个平台最大爬取数量
            enable_ai_analysis: 是否启用AI分析
            **kwargs: 其他参数
            
        Returns:
            批次ID
        """
        # 如果未指定平台，获取所有可用平台
        if not platforms:
            from .platform_factory import PlatformFactory
            platforms = PlatformFactory.get_registered_platforms()
            logger.info("Using all available platforms", platforms=[p.value for p in platforms])
        
        batch_id = str(uuid.uuid4())
        
        # 创建批次记录
        batch_info = {
            'batch_id': batch_id,
            'platforms': platforms,
            'keywords': keywords,
            'max_count_per_platform': max_count_per_platform,
            'enable_ai_analysis': enable_ai_analysis,
            'created_at': datetime.utcnow(),
            'task_ids': [],
            'platform_status': {},
            'overall_status': 'pending',
            'total_tasks': len(platforms),
            'completed_tasks': 0,
            'failed_tasks': 0,
            'total_content_found': 0,
            'ai_analysis_status': 'pending' if enable_ai_analysis else 'disabled'
        }
        
        async with self._batch_lock:
            self.active_batches[batch_id] = batch_info
        
        logger.info("Batch crawl created", 
                   batch_id=batch_id,
                   platforms=[p.value for p in platforms],
                   keywords=keywords[:3] if keywords else None,
                   enable_ai_analysis=enable_ai_analysis)
        
        return batch_id
    
    async def execute_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        执行批次爬虫任务
        
        Args:
            batch_id: 批次ID
            
        Returns:
            批次执行结果
        """
        if batch_id not in self.active_batches:
            raise ValueError(f"Batch {batch_id} not found")
        
        batch_info = self.active_batches[batch_id]
        batch_info['overall_status'] = 'running'
        batch_info['started_at'] = datetime.utcnow()
        
        try:
            # 为每个平台创建爬虫任务
            task_ids = []
            for platform in batch_info['platforms']:
                try:
                    task_id = await crawler_manager.submit_crawl_task(
                        platform=platform,
                        keywords=batch_info['keywords'],
                        max_count=batch_info['max_count_per_platform']
                    )
                    task_ids.append(task_id)
                    batch_info['platform_status'][platform.value] = {
                        'task_id': task_id,
                        'status': 'pending',
                        'content_count': 0,
                        'error_message': None
                    }
                    logger.info("Platform task created", 
                               batch_id=batch_id,
                               platform=platform.value,
                               task_id=task_id)
                except Exception as e:
                    logger.error("Failed to create platform task",
                                batch_id=batch_id,
                                platform=platform.value,
                                error=str(e))
                    batch_info['platform_status'][platform.value] = {
                        'task_id': None,
                        'status': 'failed',
                        'content_count': 0,
                        'error_message': str(e)
                    }
                    batch_info['failed_tasks'] += 1
            
            batch_info['task_ids'] = task_ids
            
            # 并行执行所有任务
            await self._execute_tasks_parallel(batch_id, task_ids)
            
            # 如果启用AI分析，等待所有任务完成后进行分析
            if batch_info['enable_ai_analysis'] and batch_info['total_content_found'] > 0:
                await self._execute_ai_analysis(batch_id)
            
            # 更新最终状态
            batch_info['completed_at'] = datetime.utcnow()
            if batch_info['failed_tasks'] == 0:
                batch_info['overall_status'] = 'completed'
            elif batch_info['completed_tasks'] > 0:
                batch_info['overall_status'] = 'partial_success'
            else:
                batch_info['overall_status'] = 'failed'
            
            logger.info("Batch crawl completed",
                       batch_id=batch_id,
                       overall_status=batch_info['overall_status'],
                       completed_tasks=batch_info['completed_tasks'],
                       failed_tasks=batch_info['failed_tasks'],
                       total_content=batch_info['total_content_found'])
            
            return batch_info
            
        except Exception as e:
            batch_info['overall_status'] = 'failed'
            batch_info['error_message'] = str(e)
            logger.error("Batch execution failed", batch_id=batch_id, error=str(e))
            raise
    
    async def _execute_tasks_parallel(self, batch_id: str, task_ids: List[str]):
        """并行执行爬虫任务"""
        batch_info = self.active_batches[batch_id]
        
        async def execute_single_task(task_id: str):
            try:
                result = await crawler_manager.execute_task(task_id)
                
                # 找到对应的平台
                platform_name = None
                for platform, status in batch_info['platform_status'].items():
                    if status.get('task_id') == task_id:
                        platform_name = platform
                        break
                
                if platform_name:
                    batch_info['platform_status'][platform_name].update({
                        'status': 'completed',
                        'content_count': result.success_count if result else 0
                    })
                    if result:
                        batch_info['total_content_found'] += result.success_count
                    batch_info['completed_tasks'] += 1
                    
                    logger.info("Platform task completed",
                               batch_id=batch_id,
                               platform=platform_name,
                               task_id=task_id,
                               content_count=result.success_count if result else 0)
                
            except Exception as e:
                # 找到对应的平台并标记为失败
                platform_name = None
                for platform, status in batch_info['platform_status'].items():
                    if status.get('task_id') == task_id:
                        platform_name = platform
                        break
                
                if platform_name:
                    batch_info['platform_status'][platform_name].update({
                        'status': 'failed',
                        'error_message': str(e)
                    })
                    batch_info['failed_tasks'] += 1
                    
                    logger.error("Platform task failed",
                                batch_id=batch_id,
                                platform=platform_name,
                                task_id=task_id,
                                error=str(e))
        
        # 并行执行所有任务
        await asyncio.gather(*[execute_single_task(task_id) for task_id in task_ids], 
                            return_exceptions=True)
    
    async def _execute_ai_analysis(self, batch_id: str):
        """执行AI分析"""
        batch_info = self.active_batches[batch_id]
        
        try:
            batch_info['ai_analysis_status'] = 'running'
            logger.info("Starting AI analysis for batch", batch_id=batch_id)
            
            # 触发AI分析
            await ai_processing_manager.process_unprocessed_contents(
                batch_size=min(batch_info['total_content_found'], 20),
                max_concurrent=3
            )
            
            # 生成批次总结
            ai_summary = await self._generate_batch_summary(batch_id)
            batch_info['ai_summary'] = ai_summary
            batch_info['ai_analysis_status'] = 'completed'
            
            logger.info("AI analysis completed for batch", batch_id=batch_id)
            
        except Exception as e:
            batch_info['ai_analysis_status'] = 'failed'
            batch_info['ai_error_message'] = str(e)
            logger.error("AI analysis failed for batch", 
                        batch_id=batch_id, error=str(e))
    
    async def _generate_batch_summary(self, batch_id: str) -> str:
        """生成批次总结"""
        batch_info = self.active_batches[batch_id]
        
        # 这里可以调用AI服务生成更智能的总结
        # 目前先生成基础总结
        platforms_summary = []
        for platform, status in batch_info['platform_status'].items():
            if status['status'] == 'completed':
                platforms_summary.append(f"{platform}: {status['content_count']}条内容")
            else:
                platforms_summary.append(f"{platform}: 失败")
        
        summary = f"""
批次爬虫总结 (ID: {batch_id}):
- 爬取平台: {len(batch_info['platforms'])}个
- 成功平台: {batch_info['completed_tasks']}个
- 失败平台: {batch_info['failed_tasks']}个
- 总内容数: {batch_info['total_content_found']}条
- 平台详情: {', '.join(platforms_summary)}
- 关键词: {', '.join(batch_info['keywords']) if batch_info['keywords'] else '默认关键词'}
"""
        return summary.strip()
    
    async def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """获取批次状态"""
        batch_info = self.active_batches.get(batch_id)
        if not batch_info:
            return None
        
        # 计算整体进度
        total_tasks = batch_info['total_tasks']
        if total_tasks > 0:
            completed_progress = (batch_info['completed_tasks'] / total_tasks) * 80  # 爬虫占80%
            if batch_info['enable_ai_analysis'] and batch_info['ai_analysis_status'] == 'completed':
                ai_progress = 20  # AI分析占20%
            elif batch_info['enable_ai_analysis'] and batch_info['ai_analysis_status'] == 'running':
                ai_progress = 10
            else:
                ai_progress = 0
            overall_progress = int(completed_progress + ai_progress)
        else:
            overall_progress = 0
        
        return {
            **batch_info,
            'overall_progress': min(overall_progress, 100)
        }
    
    async def list_batches(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出批次任务"""
        batches = list(self.active_batches.values())
        # 按创建时间倒序排序
        batches.sort(key=lambda x: x['created_at'], reverse=True)
        return batches[:limit]
    
    async def cleanup_old_batches(self, hours: int = 24):
        """清理旧批次"""
        cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
        
        batches_to_remove = []
        for batch_id, batch_info in self.active_batches.items():
            if batch_info['created_at'].timestamp() < cutoff_time:
                batches_to_remove.append(batch_id)
        
        for batch_id in batches_to_remove:
            del self.active_batches[batch_id]
        
        logger.info("Old batches cleaned up", removed_count=len(batches_to_remove))


# 全局批次管理器实例
batch_crawl_manager = BatchCrawlManager()