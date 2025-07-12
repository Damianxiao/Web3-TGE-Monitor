"""
内容分析器
负责AI内容分析的业务逻辑
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from .ai_client import get_ai_client
from ..database.database import get_db_session
from ..database.crud import TGEProjectCRUD, AIProcessLogCRUD

logger = structlog.get_logger()


class ContentAnalyzer:
    """内容分析器"""
    
    def __init__(self, ai_client=None):
        self.ai_client = ai_client or get_ai_client()
        
    async def analyze_tge_content(
        self, 
        project_id: int, 
        content: str, 
        project_name: str = None
    ) -> Dict[str, Any]:
        """
        分析TGE项目内容
        
        Args:
            project_id: 项目ID
            content: 要分析的内容
            project_name: 项目名称（可选）
            
        Returns:
            分析结果字典
        """
        try:
            logger.info("Starting TGE content analysis", 
                       project_id=project_id,
                       content_length=len(content))
            
            # 记录处理开始
            await self._log_analysis_start(project_id, "tge_analysis", content)
            
            # 调用AI分析
            analysis_result = await self.ai_client.analyze_content(
                content=content,
                analysis_type="tge_analysis"
            )
            
            if not analysis_result:
                logger.error("AI analysis failed", project_id=project_id)
                await self._log_analysis_error(project_id, "AI analysis returned None")
                return self._create_default_analysis(project_name or "Unknown")
            
            # 验证和标准化结果
            standardized_result = self._standardize_tge_analysis(analysis_result, project_name)
            
            # 记录处理成功
            await self._log_analysis_success(project_id, "tge_analysis", standardized_result)
            
            logger.info("TGE content analysis completed", 
                       project_id=project_id,
                       project_name=standardized_result.get('project_name'))
            
            return standardized_result
            
        except Exception as e:
            logger.error("TGE content analysis failed", 
                        project_id=project_id,
                        error=str(e))
            await self._log_analysis_error(project_id, str(e))
            return self._create_default_analysis(project_name or "Unknown")
    
    async def batch_analyze_contents(
        self, 
        contents: List[Dict[str, Any]], 
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        批量分析内容
        
        Args:
            contents: 内容列表，每项包含id, content, project_name
            max_concurrent: 最大并发数
            
        Returns:
            分析结果列表
        """
        import asyncio
        
        logger.info("Starting batch content analysis", 
                   batch_size=len(contents),
                   max_concurrent=max_concurrent)
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_single(item):
            async with semaphore:
                return await self.analyze_tge_content(
                    project_id=item['id'],
                    content=item['raw_content'],
                    project_name=item.get('project_name')
                )
        
        # 并发执行分析
        tasks = [analyze_single(item) for item in contents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Batch analysis item failed", 
                           item_id=contents[i]['id'],
                           error=str(result))
                processed_results.append(
                    self._create_default_analysis(contents[i].get('project_name', 'Unknown'))
                )
            else:
                processed_results.append(result)
        
        logger.info("Batch content analysis completed", 
                   successful=len([r for r in results if not isinstance(r, Exception)]),
                   failed=len([r for r in results if isinstance(r, Exception)]))
        
        return processed_results
    
    def _standardize_tge_analysis(self, raw_result: Dict[str, Any], fallback_name: str = None) -> Dict[str, Any]:
        """标准化TGE分析结果"""
        # 默认结构
        standard_result = {
            "project_name": fallback_name or "Unknown",
            "token_symbol": None,
            "tge_date": None,
            "project_category": "Other",
            "key_features": [],
            "funding_info": None,
            "risk_level": "Medium",
            "summary": "项目信息需要进一步分析",
            "analysis_confidence": 0.5,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        # 如果是文本格式的结果
        if isinstance(raw_result, dict) and "analysis" in raw_result:
            standard_result["summary"] = raw_result["analysis"][:100]
            return standard_result
        
        # 如果是结构化结果，逐字段验证和填充
        if isinstance(raw_result, dict):
            if raw_result.get('project_name'):
                standard_result['project_name'] = str(raw_result['project_name'])[:100]
            
            if raw_result.get('token_symbol'):
                standard_result['token_symbol'] = str(raw_result['token_symbol'])[:20]
            
            if raw_result.get('tge_date'):
                standard_result['tge_date'] = self._validate_date(raw_result['tge_date'])
            
            if raw_result.get('project_category') in ['DeFi', 'GameFi', 'NFT', 'Layer2', 'DAO', 'Other']:
                standard_result['project_category'] = raw_result['project_category']
            
            if raw_result.get('key_features') and isinstance(raw_result['key_features'], list):
                standard_result['key_features'] = [str(f)[:50] for f in raw_result['key_features'][:5]]
            
            if raw_result.get('funding_info'):
                standard_result['funding_info'] = str(raw_result['funding_info'])[:200]
            
            if raw_result.get('risk_level') in ['Low', 'Medium', 'High']:
                standard_result['risk_level'] = raw_result['risk_level']
            
            if raw_result.get('summary'):
                standard_result['summary'] = str(raw_result['summary'])[:200]
        
        return standard_result
    
    def _validate_date(self, date_str: str) -> Optional[str]:
        """验证日期格式"""
        if not date_str:
            return None
        
        try:
            # 尝试解析常见的日期格式
            import re
            from datetime import datetime
            
            # YYYY-MM-DD格式
            if re.match(r'\d{4}-\d{2}-\d{2}', str(date_str)):
                datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
                return str(date_str)[:10]
            
            return None
        except Exception:
            return None
    
    def _create_default_analysis(self, project_name: str) -> Dict[str, Any]:
        """创建默认分析结果"""
        return {
            "project_name": project_name,
            "token_symbol": None,
            "tge_date": None,
            "project_category": "Other",
            "key_features": [],
            "funding_info": None,
            "risk_level": "Medium",
            "summary": "AI分析暂时不可用，需要人工审核",
            "analysis_confidence": 0.0,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "analysis_status": "failed"
        }
    
    async def _log_analysis_start(self, project_id: int, analysis_type: str, content: str):
        """记录分析开始"""
        try:
            log_data = {
                'project_id': project_id,
                'analysis_type': analysis_type,
                'input_length': len(content),
                'status': 'started',
                'prompt_tokens': self._estimate_tokens(content)
            }
            
            async with get_db_session() as session:
                await AIProcessLogCRUD.create_log(session, log_data)
                
        except Exception as e:
            logger.warning("Failed to log analysis start", error=str(e))
    
    async def _log_analysis_success(self, project_id: int, analysis_type: str, result: Dict[str, Any]):
        """记录分析成功"""
        try:
            log_data = {
                'project_id': project_id,
                'analysis_type': analysis_type,
                'status': 'success',
                'output_length': len(str(result)),
                'confidence_score': result.get('analysis_confidence', 0.5)
            }
            
            async with get_db_session() as session:
                await AIProcessLogCRUD.update_log_status(session, project_id, analysis_type, log_data)
                
        except Exception as e:
            logger.warning("Failed to log analysis success", error=str(e))
    
    async def _log_analysis_error(self, project_id: int, error_message: str):
        """记录分析错误"""
        try:
            log_data = {
                'project_id': project_id,
                'analysis_type': 'tge_analysis',
                'status': 'error',
                'error_message': error_message[:500]
            }
            
            async with get_db_session() as session:
                await AIProcessLogCRUD.update_log_status(session, project_id, 'tge_analysis', log_data)
                
        except Exception as e:
            logger.warning("Failed to log analysis error", error=str(e))
    
    def _estimate_tokens(self, text: str) -> int:
        """估算文本token数量"""
        # 简单估算：中文约1.5字符/token，英文约4字符/token
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        
        estimated_tokens = int(chinese_chars / 1.5 + other_chars / 4)
        return max(1, estimated_tokens)