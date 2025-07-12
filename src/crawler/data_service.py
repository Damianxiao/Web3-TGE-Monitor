"""
数据服务层
负责爬虫数据的存储、处理和管理
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from ..database.database import get_db_session
from ..database.crud import TGEProjectCRUD, CrawlerLogCRUD
from ..utils.deduplication import deduplication_service
from ..utils.text_processing import process_raw_content
from .models import RawContent, CrawlResult, Platform

logger = structlog.get_logger()


class CrawlDataService:
    """爬虫数据服务"""
    
    async def process_and_store_crawl_result(self, result: CrawlResult) -> Dict[str, Any]:
        """
        处理并存储爬取结果
        
        Args:
            result: 爬取结果
            
        Returns:
            处理统计信息
        """
        stats = {
            'total_processed': 0,
            'successfully_saved': 0,
            'duplicates_skipped': 0,
            'errors': 0,
            'processing_time': 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            # 处理每个内容项
            for content in result.contents:
                stats['total_processed'] += 1
                
                try:
                    # 处理单个内容项
                    success = await self._process_single_content(content)
                    if success:
                        stats['successfully_saved'] += 1
                    else:
                        stats['duplicates_skipped'] += 1
                        
                except Exception as e:
                    stats['errors'] += 1
                    logger.error("Failed to process content",
                               content_id=content.content_id,
                               platform=content.platform.value,
                               error=str(e))
            
            # 记录爬虫运行日志
            await self._log_crawl_execution(result, stats)
            
            # 计算处理时间
            stats['processing_time'] = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info("Crawl result processed",
                       task_id=result.task_id,
                       platform=result.platform.value,
                       stats=stats)
            
            return stats
            
        except Exception as e:
            logger.error("Failed to process crawl result",
                        task_id=result.task_id,
                        error=str(e))
            raise
    
    async def _process_single_content(self, content: RawContent) -> bool:
        """
        处理单个内容项
        
        Args:
            content: 原始内容
            
        Returns:
            是否成功保存（False表示重复跳过）
        """
        try:
            # 1. 文本处理和信息提取
            full_text = f"{content.title} {content.content}"
            processed_data = process_raw_content(full_text, extract_info=True)
            
            # 2. 生成内容hash用于去重
            content_hash = deduplication_service.generate_content_hash(full_text)
            
            # 3. 检查是否重复
            async with get_db_session() as session:
                existing = await TGEProjectCRUD.get_by_content_hash(session, content_hash)
                if existing:
                    logger.debug("Duplicate content skipped",
                               content_id=content.content_id,
                               existing_id=existing.id)
                    return False
            
            # 4. 提取项目信息
            tge_info = processed_data.get('tge_info', {})
            project_name = (
                tge_info.get('project_name') or 
                self._extract_project_name_from_title(content.title) or
                f"{content.platform.value}_{content.content_id}"
            )
            
            # 5. 构建数据库记录
            project_data = {
                'project_name': project_name,
                'content_hash': content_hash,
                'raw_content': full_text,
                'source_platform': content.platform.value,
                'source_url': content.source_url,
                'source_user_id': content.author_id,
                'source_username': content.author_name,
                
                # TGE相关信息
                'token_name': tge_info.get('project_name'),
                'token_symbol': tge_info.get('token_symbol'),
                'tge_date': tge_info.get('tge_date'),
                'project_category': self._classify_project_category(processed_data),
                
                # 统计信息
                'engagement_score': self._calculate_engagement_score(content),
                'keyword_matches': self._get_keyword_matches(full_text),
                
                'is_processed': False,  # 等待AI处理
                'is_valid': True
            }
            
            # 6. 保存到数据库
            async with get_db_session() as session:
                project = await TGEProjectCRUD.create(session, project_data)
                if project:
                    logger.info("Content saved to database",
                               content_id=content.content_id,
                               project_id=project.id,
                               project_name=project.project_name)
                    return True
                else:
                    logger.warning("Failed to save content - possible duplicate",
                                 content_id=content.content_id)
                    return False
                    
        except Exception as e:
            logger.error("Error processing single content",
                        content_id=content.content_id,
                        error=str(e))
            raise
    
    def _extract_project_name_from_title(self, title: str) -> Optional[str]:
        """从标题中提取项目名称"""
        if not title:
            return None
        
        # 简单的项目名称提取逻辑
        # 可以根据需要增强
        import re
        
        patterns = [
            r'([A-Za-z]+)(?:\s+Token|\s+Protocol|\s+Network)',
            r'([A-Za-z\u4e00-\u9fa5]+)(?:项目|代币|协议)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)
        
        return None
    
    def _classify_project_category(self, processed_data: Dict[str, Any]) -> Optional[str]:
        """分类项目类别"""
        content = processed_data.get('cleaned_text', '').lower()
        
        if any(keyword in content for keyword in ['defi', '去中心化金融', '借贷', '流动性']):
            return 'DeFi'
        elif any(keyword in content for keyword in ['gamefi', '链游', '游戏', 'game']):
            return 'GameFi'
        elif any(keyword in content for keyword in ['nft', '非同质化', '收藏品']):
            return 'NFT'
        elif any(keyword in content for keyword in ['layer2', 'l2', '二层', '扩容']):
            return 'Layer2'
        elif any(keyword in content for keyword in ['dao', '治理', 'governance']):
            return 'DAO'
        else:
            return 'Other'
    
    def _calculate_engagement_score(self, content: RawContent) -> float:
        """计算用户参与度评分"""
        # 简单的参与度计算公式
        likes = content.like_count or 0
        comments = content.comment_count or 0
        shares = content.share_count or 0
        collects = content.collect_count or 0
        
        # 加权计算
        score = (
            likes * 1.0 +
            comments * 3.0 +
            shares * 2.0 +
            collects * 2.5
        )
        
        # 归一化到0-1范围（对数缩放）
        import math
        if score > 0:
            normalized = math.log10(score + 1) / 6  # 假设最大为10^6
            return min(1.0, normalized)
        else:
            return 0.0
    
    def _get_keyword_matches(self, content: str) -> str:
        """获取匹配的关键词"""
        from ..config.keywords import get_all_keywords
        
        keywords = get_all_keywords()
        matches = []
        
        content_lower = content.lower()
        for keyword in keywords:
            if keyword.lower() in content_lower:
                matches.append(keyword)
        
        return ','.join(matches) if matches else ''
    
    async def _log_crawl_execution(self, result: CrawlResult, stats: Dict[str, Any]):
        """记录爬虫执行日志"""
        try:
            log_data = {
                'platform': result.platform.value,
                'keywords': ','.join(result.keywords_used),
                'pages_crawled': 1,  # 简化统计
                'items_found': result.total_count,
                'items_processed': stats['total_processed'],
                'items_saved': stats['successfully_saved'],
                'status': 'success' if stats['errors'] == 0 else 'partial',
                'error_message': f"Errors: {stats['errors']}" if stats['errors'] > 0 else None,
                'execution_time': result.execution_time
            }
            
            async with get_db_session() as session:
                await CrawlerLogCRUD.create_log(session, log_data)
                
        except Exception as e:
            logger.error("Failed to log crawl execution", error=str(e))
    
    async def get_unprocessed_contents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取未处理的内容（等待AI处理）"""
        try:
            async with get_db_session() as session:
                projects = await TGEProjectCRUD.get_unprocessed(session, limit)
                
                return [
                    {
                        'id': project.id,
                        'project_name': project.project_name,
                        'raw_content': project.raw_content,
                        'source_platform': project.source_platform,
                        'created_at': project.created_at
                    }
                    for project in projects
                ]
                
        except Exception as e:
            logger.error("Failed to get unprocessed contents", error=str(e))
            return []
    
    async def mark_content_processed(self, project_id: int, ai_analysis: Dict[str, Any]) -> bool:
        """标记内容已处理并保存AI分析结果"""
        try:
            async with get_db_session() as session:
                success = await TGEProjectCRUD.update_ai_analysis(
                    session, project_id, ai_analysis
                )
                return success
                
        except Exception as e:
            logger.error("Failed to mark content processed", 
                        project_id=project_id, 
                        error=str(e))
            return False


# 全局数据服务实例
crawl_data_service = CrawlDataService()