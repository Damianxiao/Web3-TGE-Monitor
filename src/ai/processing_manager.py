"""
AI处理流程管理器
统一管理AI分析流程
"""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from .ai_client import get_ai_client
from .content_analyzer import ContentAnalyzer
from .investment_advisor import InvestmentAdvisor
from .sentiment_analyzer import SentimentAnalyzer
from ..crawler.data_service import crawl_data_service
from ..database.database import get_db_session
from ..database.crud import TGEProjectCRUD

logger = structlog.get_logger()


class AIProcessingManager:
    """
AI处理流程管理器
    统一管理内容分析、投资建议和情感分析的整个流程
    """
    
    def __init__(self, ai_config: Dict[str, Any] = None):
        """
        初始化AI处理管理器
        
        Args:
            ai_config: AI配置
        """
        self.ai_client = get_ai_client(ai_config)
        self.content_analyzer = ContentAnalyzer(self.ai_client)
        self.investment_advisor = InvestmentAdvisor(self.ai_client)
        self.sentiment_analyzer = SentimentAnalyzer(self.ai_client)
        
        logger.info("AI processing manager initialized")
    
    async def process_unprocessed_contents(self, batch_size: int = 10, max_concurrent: int = 3) -> Dict[str, Any]:
        """
        处理所有未处理的内容
        
        Args:
            batch_size: 批次处理数量
            max_concurrent: 最大并发数
            
        Returns:
            处理结果统计
        """
        logger.info("Starting batch processing of unprocessed contents", 
                   batch_size=batch_size,
                   max_concurrent=max_concurrent)
        
        stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'processing_time': 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            while True:
                # 获取未处理的内容
                unprocessed_contents = await crawl_data_service.get_unprocessed_contents(batch_size)
                
                if not unprocessed_contents:
                    logger.info("No more unprocessed contents found")
                    break
                
                logger.info(f"Processing batch of {len(unprocessed_contents)} contents")
                
                # 批量处理
                batch_results = await self._process_content_batch(
                    unprocessed_contents, 
                    max_concurrent
                )
                
                # 更新统计
                stats['total_processed'] += len(unprocessed_contents)
                stats['successful'] += sum(1 for r in batch_results if r.get('success', False))
                stats['failed'] += sum(1 for r in batch_results if not r.get('success', False))
                
                # 如果批次小于batch_size，说明已经处理完成
                if len(unprocessed_contents) < batch_size:
                    break
            
            # 计算处理时间
            stats['processing_time'] = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info("Batch processing completed", stats=stats)
            return stats
            
        except Exception as e:
            logger.error("Batch processing failed", error=str(e))
            stats['processing_time'] = (datetime.utcnow() - start_time).total_seconds()
            return stats
    
    async def process_single_content(
        self, 
        project_id: int, 
        include_sentiment: bool = True
    ) -> Dict[str, Any]:
        """
        处理单个内容
        
        Args:
            project_id: 项目ID
            include_sentiment: 是否包含情感分析
            
        Returns:
            处理结果
        """
        try:
            logger.info("Processing single content", project_id=project_id)
            
            # 获取项目数据
            async with get_db_session() as session:
                project = await TGEProjectCRUD.get_by_id(session, project_id)
                if not project:
                    return {'success': False, 'error': 'Project not found'}
                
                if project.is_processed:
                    return {'success': True, 'message': 'Already processed', 'skipped': True}
            
            # 执行AI分析流程
            analysis_result = await self._execute_full_analysis(
                project_id=project_id,
                content=project.raw_content,
                project_name=project.project_name,
                include_sentiment=include_sentiment
            )
            
            if analysis_result['success']:
                # 更新数据库
                success = await crawl_data_service.mark_content_processed(
                    project_id, 
                    analysis_result['ai_analysis']
                )
                
                if success:
                    logger.info("Content processing completed", project_id=project_id)
                    return {'success': True, 'analysis': analysis_result['ai_analysis']}
                else:
                    logger.error("Failed to save analysis results", project_id=project_id)
                    return {'success': False, 'error': 'Failed to save results'}
            else:
                logger.error("AI analysis failed", 
                           project_id=project_id,
                           error=analysis_result.get('error'))
                return analysis_result
                
        except Exception as e:
            logger.error("Single content processing failed", 
                        project_id=project_id,
                        error=str(e))
            return {'success': False, 'error': str(e)}
    
    async def _process_content_batch(
        self, 
        contents: List[Dict[str, Any]], 
        max_concurrent: int
    ) -> List[Dict[str, Any]]:
        """批量处理内容"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(content_data):
            async with semaphore:
                return await self.process_single_content(content_data['id'])
        
        # 并发执行
        tasks = [process_single(content) for content in contents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Batch item processing failed", 
                           content_id=contents[i]['id'],
                           error=str(result))
                processed_results.append({
                    'success': False, 
                    'error': str(result),
                    'content_id': contents[i]['id']
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _execute_full_analysis(
        self, 
        project_id: int, 
        content: str, 
        project_name: str, 
        include_sentiment: bool = True
    ) -> Dict[str, Any]:
        """执行完整的AI分析流程"""
        try:
            analysis_results = {}
            
            # 步骤1：TGE内容分析
            logger.debug("Starting TGE analysis", project_id=project_id)
            tge_analysis = await self.content_analyzer.analyze_tge_content(
                project_id=project_id,
                content=content,
                project_name=project_name
            )
            analysis_results['tge_analysis'] = tge_analysis
            
            # 步骤2：投资建议生成
            logger.debug("Starting investment advice generation", project_id=project_id)
            investment_advice = await self.investment_advisor.generate_investment_advice(
                project_id=project_id,
                tge_analysis=tge_analysis
            )
            analysis_results['investment_advice'] = investment_advice
            
            # 步骤3：情感分析（可选）
            if include_sentiment:
                logger.debug("Starting sentiment analysis", project_id=project_id)
                sentiment_analysis = await self.sentiment_analyzer.analyze_sentiment(
                    content=content,
                    project_name=project_name
                )
                analysis_results['sentiment_analysis'] = sentiment_analysis
            
            # 整合结果
            integrated_analysis = self._integrate_analysis_results(analysis_results)
            
            return {
                'success': True,
                'ai_analysis': integrated_analysis,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Full analysis execution failed", 
                        project_id=project_id,
                        error=str(e))
            return {
                'success': False,
                'error': str(e),
                'processing_timestamp': datetime.utcnow().isoformat()
            }
    
    def _integrate_analysis_results(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """整合分析结果"""
        tge = analysis_results.get('tge_analysis', {})
        investment = analysis_results.get('investment_advice', {})
        sentiment = analysis_results.get('sentiment_analysis', {})
        
        # 整合后的统一结构
        integrated = {
            # 项目基本信息
            'project_name': tge.get('project_name'),
            'token_symbol': tge.get('token_symbol'),
            'project_category': tge.get('project_category'),
            'tge_date': tge.get('tge_date'),
            
            # TGE分析结果
            'tge_summary': tge.get('summary'),
            'key_features': tge.get('key_features', []),
            'funding_info': tge.get('funding_info'),
            'risk_level': tge.get('risk_level'),
            
            # 投资建议
            'investment_rating': investment.get('investment_rating'),
            'investment_recommendation': investment.get('recommendation'),
            'investment_reason': investment.get('reason'),
            'key_advantages': investment.get('key_advantages', []),
            'key_risks': investment.get('key_risks', []),
            'potential_score': investment.get('potential_score'),
            'overall_score': investment.get('overall_score'),
            
            # 情感分析
            'sentiment_score': sentiment.get('sentiment_score'),
            'sentiment_label': sentiment.get('sentiment_label'),
            'market_sentiment': sentiment.get('market_sentiment'),
            
            # 元数据
            'analysis_confidence': self._calculate_overall_confidence(analysis_results),
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'analysis_version': '1.0'
        }
        
        # 添加原始结果用于调试
        integrated['raw_results'] = {
            'tge_analysis': tge,
            'investment_advice': investment,
            'sentiment_analysis': sentiment
        }
        
        return integrated
    
    def _calculate_overall_confidence(self, analysis_results: Dict[str, Any]) -> float:
        """计算综合置信度"""
        confidences = []
        
        # TGE分析置信度
        tge_conf = analysis_results.get('tge_analysis', {}).get('analysis_confidence', 0.5)
        confidences.append(tge_conf)
        
        # 投资建议置信度
        invest_conf = analysis_results.get('investment_advice', {}).get('confidence_level', 0.5)
        confidences.append(invest_conf)
        
        # 情感分析置信度
        if 'sentiment_analysis' in analysis_results:
            sentiment_conf = analysis_results['sentiment_analysis'].get('confidence', 0.5)
            confidences.append(sentiment_conf)
        
        # 计算加权平均置信度
        if confidences:
            overall_confidence = sum(confidences) / len(confidences)
            return round(overall_confidence, 3)
        else:
            return 0.5
    
    async def get_processing_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        try:
            async with get_db_session() as session:
                # 统计已处理和未处理的内容
                total_projects = await TGEProjectCRUD.count_all(session)
                processed_projects = await TGEProjectCRUD.count_processed(session)
                unprocessed_projects = total_projects - processed_projects
                
                return {
                    'total_projects': total_projects,
                    'processed_projects': processed_projects,
                    'unprocessed_projects': unprocessed_projects,
                    'processing_rate': round(processed_projects / max(total_projects, 1) * 100, 2),
                    'last_updated': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error("Failed to get processing statistics", error=str(e))
            return {
                'total_projects': 0,
                'processed_projects': 0,
                'unprocessed_projects': 0,
                'processing_rate': 0.0,
                'error': str(e)
            }


# 全局AI处理管理器实例
ai_processing_manager = AIProcessingManager()