"""
数据库CRUD操作
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import structlog

from .models import TGEProject, CrawlerLog, AIProcessLog

logger = structlog.get_logger()


class TGEProjectCRUD:
    """TGE项目数据操作"""
    
    @staticmethod
    async def create(session: AsyncSession, project_data: Dict[str, Any]) -> Optional[TGEProject]:
        """创建新的TGE项目记录"""
        try:
            project = TGEProject(**project_data)
            session.add(project)
            await session.commit()
            await session.refresh(project)
            logger.info("TGE project created", project_id=project.id, project_name=project.project_name)
            return project
        except IntegrityError:
            await session.rollback()
            logger.warning("Duplicate content hash detected", content_hash=project_data.get('content_hash'))
            return None
        except Exception as e:
            await session.rollback()
            logger.error("Failed to create TGE project", error=str(e))
            raise
    
    @staticmethod
    async def get_by_id(session: AsyncSession, project_id: int) -> Optional[TGEProject]:
        """根据ID获取TGE项目"""
        result = await session.execute(select(TGEProject).where(TGEProject.id == project_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_content_hash(session: AsyncSession, content_hash: str) -> Optional[TGEProject]:
        """根据内容hash获取TGE项目（用于去重）"""
        result = await session.execute(select(TGEProject).where(TGEProject.content_hash == content_hash))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_latest(session: AsyncSession, limit: int = 10, sentiment: Optional[str] = None) -> List[TGEProject]:
        """获取最新的TGE项目"""
        query = select(TGEProject).where(TGEProject.is_valid == True)
        
        if sentiment:
            query = query.where(TGEProject.sentiment == sentiment)
        
        query = query.order_by(TGEProject.created_at.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def search_by_keywords(session: AsyncSession, keywords: List[str], limit: int = 20) -> List[TGEProject]:
        """根据关键词搜索TGE项目"""
        conditions = []
        for keyword in keywords:
            conditions.append(TGEProject.raw_content.contains(keyword))
            conditions.append(TGEProject.ai_summary.contains(keyword))
            conditions.append(TGEProject.project_name.contains(keyword))
        
        query = select(TGEProject).where(
            and_(
                TGEProject.is_valid == True,
                or_(*conditions)
            )
        ).order_by(TGEProject.created_at.desc()).limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def update_ai_analysis(session: AsyncSession, project_id: int, analysis_data: Dict[str, Any]) -> bool:
        """更新AI分析结果"""
        try:
            await session.execute(
                update(TGEProject)
                .where(TGEProject.id == project_id)
                .values(**analysis_data, is_processed=True)
            )
            await session.commit()
            logger.info("AI analysis updated", project_id=project_id)
            return True
        except Exception as e:
            await session.rollback()
            logger.error("Failed to update AI analysis", project_id=project_id, error=str(e))
            return False
    
    @staticmethod
    async def get_unprocessed(session: AsyncSession, limit: int = 50) -> List[TGEProject]:
        """获取未处理的TGE项目"""
        query = select(TGEProject).where(
            and_(
                TGEProject.is_processed == False,
                TGEProject.is_valid == True
            )
        ).order_by(TGEProject.created_at.asc()).limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def cleanup_old_records(session: AsyncSession, days: int = 30) -> int:
        """清理过期记录"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await session.execute(
            delete(TGEProject).where(TGEProject.created_at < cutoff_date)
        )
        await session.commit()
        
        deleted_count = result.rowcount
        logger.info("Old records cleaned up", deleted_count=deleted_count, days=days)
        return deleted_count
    
    @staticmethod
    async def get_statistics(session: AsyncSession) -> Dict[str, Any]:
        """获取统计信息"""
        total_query = select(func.count(TGEProject.id))
        total_result = await session.execute(total_query)
        total_count = total_result.scalar()
        
        processed_query = select(func.count(TGEProject.id)).where(TGEProject.is_processed == True)
        processed_result = await session.execute(processed_query)
        processed_count = processed_result.scalar()
        
        sentiment_query = select(TGEProject.sentiment, func.count(TGEProject.id)).group_by(TGEProject.sentiment)
        sentiment_result = await session.execute(sentiment_query)
        sentiment_stats = dict(sentiment_result.all())
        
        return {
            "total_projects": total_count,
            "processed_projects": processed_count,
            "sentiment_distribution": sentiment_stats,
            "processing_rate": round(processed_count / total_count * 100, 2) if total_count > 0 else 0
        }
    
    @staticmethod
    async def count_all(session: AsyncSession) -> int:
        """统计所有项目数量"""
        result = await session.execute(select(func.count(TGEProject.id)))
        return result.scalar()
    
    @staticmethod
    async def count_processed(session: AsyncSession) -> int:
        """统计已处理项目数量"""
        result = await session.execute(
            select(func.count(TGEProject.id)).where(TGEProject.is_processed == True)
        )
        return result.scalar()
    
    @staticmethod
    async def count_unprocessed(session: AsyncSession) -> int:
        """统计未处理项目数量"""
        result = await session.execute(
            select(func.count(TGEProject.id)).where(TGEProject.is_processed == False)
        )
        return result.scalar()
    
    @staticmethod
    async def count_recent(session: AsyncSession, since: datetime) -> int:
        """统计指定时间以来的项目数量"""
        result = await session.execute(
            select(func.count(TGEProject.id)).where(TGEProject.created_at >= since)
        )
        return result.scalar()
    
    @staticmethod
    async def get_paginated(
        session: AsyncSession, 
        page: int = 1, 
        size: int = 20,
        filters: Dict[str, Any] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> tuple[List[TGEProject], int]:
        """分页获取项目列表"""
        # 构建基础查询
        query = select(TGEProject).where(TGEProject.is_valid == True)
        count_query = select(func.count(TGEProject.id)).where(TGEProject.is_valid == True)
        
        # 应用过滤条件
        if filters:
            conditions = []
            for key, value in filters.items():
                if key == 'project_category' and value:
                    conditions.append(TGEProject.project_category == value)
                elif key == 'risk_level' and value:
                    conditions.append(TGEProject.risk_level == value)
                elif key == 'source_platform' and value:
                    conditions.append(TGEProject.source_platform == value)
                elif key == 'has_tge_date' and value is not None:
                    if value:
                        conditions.append(TGEProject.tge_date.isnot(None))
                    else:
                        conditions.append(TGEProject.tge_date.is_(None))
                elif key == 'is_processed' and value is not None:
                    conditions.append(TGEProject.is_processed == value)
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
        
        # 应用排序
        sort_column = getattr(TGEProject, sort_by, TGEProject.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # 应用分页
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        # 执行查询
        items_result = await session.execute(query)
        total_result = await session.execute(count_query)
        
        items = list(items_result.scalars().all())
        total = total_result.scalar()
        
        return items, total
    
    @staticmethod
    async def search(
        session: AsyncSession, 
        query: str,
        page: int = 1, 
        size: int = 20,
        filters: Dict[str, Any] = None
    ) -> tuple[List[TGEProject], int]:
        """搜索项目"""
        # 构建搜索条件
        search_conditions = [
            TGEProject.project_name.contains(query),
            TGEProject.token_symbol.contains(query),
            TGEProject.raw_content.contains(query),
            TGEProject.tge_summary.contains(query),
            TGEProject.key_features.contains(query)
        ]
        
        base_query = select(TGEProject).where(
            and_(
                TGEProject.is_valid == True,
                or_(*search_conditions)
            )
        )
        
        count_query = select(func.count(TGEProject.id)).where(
            and_(
                TGEProject.is_valid == True,
                or_(*search_conditions)
            )
        )
        
        # 应用过滤条件
        if filters:
            conditions = []
            for key, value in filters.items():
                if key == 'project_category' and value:
                    conditions.append(TGEProject.project_category == value)
                elif key == 'risk_level' and value:
                    conditions.append(TGEProject.risk_level == value)
                elif key == 'source_platform' and value:
                    conditions.append(TGEProject.source_platform == value)
            
            if conditions:
                base_query = base_query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
        
        # 排序和分页
        base_query = base_query.order_by(TGEProject.created_at.desc())
        offset = (page - 1) * size
        base_query = base_query.offset(offset).limit(size)
        
        # 执行查询
        items_result = await session.execute(base_query)
        total_result = await session.execute(count_query)
        
        items = list(items_result.scalars().all())
        total = total_result.scalar()
        
        return items, total
    
    @staticmethod
    async def get_platform_stats(session: AsyncSession) -> Dict[str, int]:
        """获取各平台项目数量统计"""
        result = await session.execute(
            select(TGEProject.source_platform, func.count(TGEProject.id))
            .group_by(TGEProject.source_platform)
        )
        return dict(result.all())
    
    @staticmethod
    async def get_category_stats(session: AsyncSession) -> Dict[str, int]:
        """获取各分类项目数量统计"""
        result = await session.execute(
            select(TGEProject.project_category, func.count(TGEProject.id))
            .where(TGEProject.project_category.isnot(None))
            .group_by(TGEProject.project_category)
        )
        return dict(result.all())
    
    @staticmethod
    async def count_all(session: AsyncSession) -> int:
        """统计所有项目数量"""
        result = await session.execute(
            select(func.count(TGEProject.id))
        )
        return result.scalar()
    
    @staticmethod
    async def count_processed(session: AsyncSession) -> int:
        """统计已处理项目数量"""
        result = await session.execute(
            select(func.count(TGEProject.id))
            .where(TGEProject.is_processed == True)
        )
        return result.scalar()
    
    @staticmethod
    async def count_unprocessed(session: AsyncSession) -> int:
        """统计未处理项目数量"""
        result = await session.execute(
            select(func.count(TGEProject.id))
            .where(TGEProject.is_processed == False)
        )
        return result.scalar()
    
    @staticmethod
    async def count_recent(session: AsyncSession, since: datetime) -> int:
        """统计指定时间以来的项目数量"""
        result = await session.execute(
            select(func.count(TGEProject.id))
            .where(TGEProject.created_at >= since)
        )
        return result.scalar()


class CrawlerLogCRUD:
    """爬虫日志操作"""
    
    @staticmethod
    async def create_log(session: AsyncSession, log_data: Dict[str, Any]) -> CrawlerLog:
        """创建爬虫日志"""
        log = CrawlerLog(**log_data)
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log
    
    @staticmethod
    async def get_recent_logs(session: AsyncSession, platform: Optional[str] = None, limit: int = 50, since: Optional[datetime] = None) -> List[CrawlerLog]:
        """获取最近的爬虫日志"""
        query = select(CrawlerLog)
        
        if platform:
            query = query.where(CrawlerLog.platform == platform)
        
        if since:
            query = query.where(CrawlerLog.created_at >= since)
        
        query = query.order_by(CrawlerLog.created_at.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())


class AIProcessLogCRUD:
    """AI处理日志操作"""
    
    @staticmethod
    async def create_log(session: AsyncSession, log_data: Dict[str, Any]) -> AIProcessLog:
        """创建AI处理日志"""
        log = AIProcessLog(**log_data)
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log
    
    @staticmethod
    async def get_recent_logs(session: AsyncSession, limit: int = 50) -> List[AIProcessLog]:
        """获取最近的AI处理日志"""
        query = select(AIProcessLog).order_by(AIProcessLog.created_at.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def update_log_status(session: AsyncSession, project_id: int, analysis_type: str, update_data: Dict[str, Any]) -> bool:
        """更新日志状态"""
        try:
            await session.execute(
                update(AIProcessLog)
                .where(
                    and_(
                        AIProcessLog.project_id == project_id,
                        AIProcessLog.analysis_type == analysis_type
                    )
                )
                .values(**update_data)
            )
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            logger.error("Failed to update AI log status", error=str(e))
            return False