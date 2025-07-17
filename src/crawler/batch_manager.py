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
    
    async def _generate_batch_summary(self, batch_id: str) -> Dict[str, Any]:
        """生成批次AI分析总结"""
        batch_info = self.active_batches[batch_id]
        
        try:
            # 获取数据库会话
            from ..database.database import get_db_session
            from ..database.crud import TGEProjectCRUD
            
            session = await get_db_session()
            async with session:
                # 获取批次相关的已处理项目
                processed_projects = await TGEProjectCRUD.get_processed_projects_by_batch(
                    session, batch_id, limit=100
                )
                
                if not processed_projects:
                    return {
                        "batch_id": batch_id,
                        "message": "没有找到已处理的项目数据",
                        "basic_summary": self._generate_basic_summary(batch_id)
                    }
                
                # 生成AI分析汇总
                ai_analysis_summary = {
                    "batch_id": batch_id,
                    "total_projects": len(processed_projects),
                    "processed_projects": len(processed_projects),
                    "processing_rate": 100.0,
                    "investment_analysis": self._analyze_investment_recommendations(processed_projects),
                    "risk_analysis": self._analyze_risk_levels(processed_projects),
                    "sentiment_analysis": self._analyze_sentiment(processed_projects),
                    "top_projects": self._get_top_projects(processed_projects),
                    "category_distribution": self._analyze_categories(processed_projects),
                    "platform_breakdown": self._analyze_platforms(processed_projects),
                    "key_insights": self._generate_key_insights(processed_projects),
                    "basic_summary": self._generate_basic_summary(batch_id)
                }
                
                return ai_analysis_summary
                
        except Exception as e:
            logger.error("Failed to generate AI analysis summary", 
                        batch_id=batch_id, error=str(e))
            return {
                "batch_id": batch_id,
                "error": str(e),
                "basic_summary": self._generate_basic_summary(batch_id)
            }
    
    def _generate_basic_summary(self, batch_id: str) -> str:
        """生成基础批次总结"""
        batch_info = self.active_batches[batch_id]
        
        platforms_summary = []
        for platform, status in batch_info['platform_status'].items():
            if status['status'] == 'completed':
                platforms_summary.append(f"{platform}: {status['content_count']}条内容")
            else:
                platforms_summary.append(f"{platform}: 失败")
        
        summary = f"""批次爬虫总结 (ID: {batch_id}):
- 爬取平台: {len(batch_info['platforms'])}个
- 成功平台: {batch_info['completed_tasks']}个
- 失败平台: {batch_info['failed_tasks']}个
- 总内容数: {batch_info['total_content_found']}条
- 平台详情: {', '.join(platforms_summary)}
- 关键词: {', '.join(batch_info['keywords']) if batch_info['keywords'] else '默认关键词'}"""
        
        return summary.strip()
    
    def _analyze_investment_recommendations(self, projects) -> Dict[str, Any]:
        """分析投资建议分布"""
        recommendations = {}
        ratings = {}
        
        for project in projects:
            # 投资建议统计
            if project.investment_recommendation:
                rec = project.investment_recommendation
                recommendations[rec] = recommendations.get(rec, 0) + 1
            
            # 投资评级统计
            if project.investment_rating:
                rating = project.investment_rating
                ratings[rating] = ratings.get(rating, 0) + 1
        
        return {
            "recommendations": recommendations,
            "ratings": ratings,
            "total_analyzed": len(projects)
        }
    
    def _analyze_risk_levels(self, projects) -> Dict[str, Any]:
        """分析风险等级分布"""
        risk_levels = {}
        
        for project in projects:
            if project.risk_level:
                risk = project.risk_level
                risk_levels[risk] = risk_levels.get(risk, 0) + 1
        
        return {
            "distribution": risk_levels,
            "total_analyzed": len(projects)
        }
    
    def _analyze_sentiment(self, projects) -> Dict[str, Any]:
        """分析情感分布"""
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        sentiment_scores = []
        
        for project in projects:
            if project.sentiment_label:
                sentiment = project.sentiment_label.lower()
                if sentiment in ["positive", "bullish", "看涨", "乐观"]:
                    sentiments["positive"] += 1
                elif sentiment in ["negative", "bearish", "看跌", "悲观"]:
                    sentiments["negative"] += 1
                else:
                    sentiments["neutral"] += 1
            
            if project.sentiment_score:
                sentiment_scores.append(project.sentiment_score)
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        return {
            "distribution": sentiments,
            "average_sentiment_score": round(avg_sentiment, 2),
            "total_analyzed": len(projects)
        }
    
    def _get_top_projects(self, projects, limit: int = 5) -> List[Dict[str, Any]]:
        """获取评分最高的项目"""
        # 按综合评分排序
        sorted_projects = sorted(
            projects,
            key=lambda p: p.overall_score or 0,
            reverse=True
        )
        
        top_projects = []
        for project in sorted_projects[:limit]:
            top_projects.append({
                "id": project.id,
                "project_name": project.project_name,
                "token_symbol": project.token_symbol,
                "overall_score": project.overall_score,
                "potential_score": project.potential_score,
                "investment_recommendation": project.investment_recommendation,
                "investment_rating": project.investment_rating,
                "risk_level": project.risk_level,
                "source_platform": project.source_platform,
                "tge_summary": project.tge_summary[:100] + "..." if project.tge_summary and len(project.tge_summary) > 100 else project.tge_summary
            })
        
        return top_projects
    
    def _analyze_categories(self, projects) -> Dict[str, int]:
        """分析项目分类分布"""
        categories = {}
        
        for project in projects:
            if project.project_category:
                category = project.project_category
                categories[category] = categories.get(category, 0) + 1
        
        return categories
    
    def _analyze_platforms(self, projects) -> Dict[str, int]:
        """分析平台分布"""
        platforms = {}
        
        for project in projects:
            if project.source_platform:
                platform = project.source_platform
                platforms[platform] = platforms.get(platform, 0) + 1
        
        return platforms
    
    def _generate_key_insights(self, projects) -> List[str]:
        """生成关键洞察"""
        insights = []
        
        if not projects:
            return ["没有足够的数据生成洞察"]
        
        total_projects = len(projects)
        
        # 投资建议洞察
        positive_recommendations = sum(1 for p in projects 
                                     if p.investment_recommendation and 
                                     p.investment_recommendation in ["关注", "推荐", "买入"])
        
        if positive_recommendations > 0:
            positive_rate = (positive_recommendations / total_projects) * 100
            insights.append(f"有{positive_rate:.1f}%的项目获得正面投资建议")
        
        # 风险分析洞察
        high_risk_projects = sum(1 for p in projects 
                               if p.risk_level and p.risk_level == "高")
        
        if high_risk_projects > 0:
            high_risk_rate = (high_risk_projects / total_projects) * 100
            insights.append(f"有{high_risk_rate:.1f}%的项目被评为高风险")
        
        # 评分洞察
        scored_projects = [p for p in projects if p.overall_score]
        if scored_projects:
            avg_score = sum(p.overall_score for p in scored_projects) / len(scored_projects)
            insights.append(f"平均综合评分为{avg_score:.1f}分")
        
        # 平台洞察
        platform_stats = self._analyze_platforms(projects)
        if platform_stats:
            best_platform = max(platform_stats, key=platform_stats.get)
            insights.append(f"最多内容来自{best_platform}平台({platform_stats[best_platform]}条)")
        
        return insights[:5]  # 最多返回5条洞察
    
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