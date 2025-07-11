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
    async def get_recent_logs(session: AsyncSession, platform: Optional[str] = None, limit: int = 50) -> List[CrawlerLog]:
        """获取最近的爬虫日志"""
        query = select(CrawlerLog)
        
        if platform:
            query = query.where(CrawlerLog.platform == platform)
        
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