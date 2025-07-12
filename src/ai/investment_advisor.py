"""
投资建议生成器
基于AI分析生成投资建议
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from .ai_client import get_ai_client
from ..database.database import get_db_session
from ..database.crud import TGEProjectCRUD

logger = structlog.get_logger()


class InvestmentAdvisor:
    """投资建议生成器"""
    
    def __init__(self, ai_client=None):
        self.ai_client = ai_client or get_ai_client()
    
    async def generate_investment_advice(
        self, 
        project_id: int, 
        tge_analysis: Dict[str, Any], 
        market_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        生成投资建议
        
        Args:
            project_id: 项目ID
            tge_analysis: TGE分析结果
            market_context: 市场背景信息（可选）
            
        Returns:
            投资建议结果
        """
        try:
            logger.info("Generating investment advice", project_id=project_id)
            
            # 构建分析内容
            analysis_content = self._build_analysis_content(tge_analysis, market_context)
            
            # 调用AI生成建议
            advice_result = await self.ai_client.analyze_content(
                content=analysis_content,
                analysis_type="investment_advice"
            )
            
            if not advice_result:
                logger.error("Investment advice generation failed", project_id=project_id)
                return self._create_default_advice(tge_analysis)
            
            # 标准化结果
            standardized_advice = self._standardize_investment_advice(advice_result, tge_analysis)
            
            # 添加额外的分析维度
            enhanced_advice = await self._enhance_advice_with_metrics(standardized_advice, tge_analysis)
            
            logger.info("Investment advice generated", 
                       project_id=project_id,
                       rating=enhanced_advice.get('investment_rating'),
                       recommendation=enhanced_advice.get('recommendation'))
            
            return enhanced_advice
            
        except Exception as e:
            logger.error("Investment advice generation failed", 
                        project_id=project_id,
                        error=str(e))
            return self._create_default_advice(tge_analysis)
    
    async def batch_generate_advice(
        self, 
        projects_data: List[Dict[str, Any]], 
        max_concurrent: int = 2
    ) -> List[Dict[str, Any]]:
        """
        批量生成投资建议
        
        Args:
            projects_data: 项目数据列表，包含id和tge_analysis
            max_concurrent: 最大并发数
            
        Returns:
            投资建议列表
        """
        import asyncio
        
        logger.info("Starting batch investment advice generation", 
                   batch_size=len(projects_data))
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_single(project_data):
            async with semaphore:
                return await self.generate_investment_advice(
                    project_id=project_data['id'],
                    tge_analysis=project_data.get('tge_analysis', {})
                )
        
        # 并发执行
        tasks = [generate_single(data) for data in projects_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Batch advice generation failed", 
                           project_id=projects_data[i]['id'],
                           error=str(result))
                processed_results.append(
                    self._create_default_advice(projects_data[i].get('tge_analysis', {}))
                )
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _build_analysis_content(self, tge_analysis: Dict[str, Any], market_context: Dict[str, Any] = None) -> str:
        """构建分析内容文本"""
        content_parts = []
        
        # 基本项目信息
        content_parts.append(f"项目名称：{tge_analysis.get('project_name', 'Unknown')}")
        
        if tge_analysis.get('token_symbol'):
            content_parts.append(f"代币符号：{tge_analysis['token_symbol']}")
        
        if tge_analysis.get('project_category'):
            content_parts.append(f"项目类别：{tge_analysis['project_category']}")
        
        if tge_analysis.get('tge_date'):
            content_parts.append(f"TGE日期：{tge_analysis['tge_date']}")
        
        # 项目特性
        if tge_analysis.get('key_features'):
            features = ', '.join(tge_analysis['key_features'])
            content_parts.append(f"关键特性：{features}")
        
        # 融资信息
        if tge_analysis.get('funding_info'):
            content_parts.append(f"融资信息：{tge_analysis['funding_info']}")
        
        # 项目简介
        if tge_analysis.get('summary'):
            content_parts.append(f"项目简介：{tge_analysis['summary']}")
        
        # 市场背景（如果有）
        if market_context:
            if market_context.get('market_trend'):
                content_parts.append(f"市场趋势：{market_context['market_trend']}")
        
        return '\n'.join(content_parts)
    
    def _standardize_investment_advice(self, raw_advice: Dict[str, Any], tge_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """标准化投资建议结果"""
        # 默认结构
        standard_advice = {
            "investment_rating": 3,  # 1-5分
            "risk_assessment": "Medium",
            "potential_score": 3,  # 1-5分
            "key_advantages": [],
            "key_risks": [],
            "short_term_outlook": "中性观望，需要持续关注",
            "recommendation": "谨慎",
            "reason": "基于当前信息的初步判断",
            "confidence_level": 0.5,
            "advice_timestamp": datetime.utcnow().isoformat()
        }
        
        # 如果是文本格式的结果
        if isinstance(raw_advice, dict) and "analysis" in raw_advice:
            standard_advice["reason"] = raw_advice["analysis"][:100]
            return standard_advice
        
        # 如果是结构化结果
        if isinstance(raw_advice, dict):
            # 投资评级
            if raw_advice.get('investment_rating'):
                try:
                    rating = int(float(str(raw_advice['investment_rating'])))
                    standard_advice['investment_rating'] = max(1, min(5, rating))
                except (ValueError, TypeError):
                    pass
            
            # 风险评估
            if raw_advice.get('risk_assessment') in ['Low', 'Medium', 'High']:
                standard_advice['risk_assessment'] = raw_advice['risk_assessment']
            
            # 潜力评分
            if raw_advice.get('potential_score'):
                try:
                    score = int(float(str(raw_advice['potential_score'])))
                    standard_advice['potential_score'] = max(1, min(5, score))
                except (ValueError, TypeError):
                    pass
            
            # 优势和风险
            if raw_advice.get('key_advantages') and isinstance(raw_advice['key_advantages'], list):
                standard_advice['key_advantages'] = [str(adv)[:100] for adv in raw_advice['key_advantages'][:5]]
            
            if raw_advice.get('key_risks') and isinstance(raw_advice['key_risks'], list):
                standard_advice['key_risks'] = [str(risk)[:100] for risk in raw_advice['key_risks'][:5]]
            
            # 短期前景
            if raw_advice.get('short_term_outlook'):
                standard_advice['short_term_outlook'] = str(raw_advice['short_term_outlook'])[:200]
            
            # 建议
            if raw_advice.get('recommendation') in ['关注', '谨慎', '避免', 'Watch', 'Caution', 'Avoid']:
                rec = raw_advice['recommendation']
                if rec in ['Watch', '关注']:
                    standard_advice['recommendation'] = '关注'
                elif rec in ['Caution', '谨慎']:
                    standard_advice['recommendation'] = '谨慎'
                elif rec in ['Avoid', '避免']:
                    standard_advice['recommendation'] = '避免'
            
            # 建议理由
            if raw_advice.get('reason'):
                standard_advice['reason'] = str(raw_advice['reason'])[:200]
        
        return standard_advice
    
    async def _enhance_advice_with_metrics(self, advice: Dict[str, Any], tge_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """基于额外指标增强建议"""
        enhanced = advice.copy()
        
        # 根据项目类别调整风险评估
        category = tge_analysis.get('project_category', 'Other')
        if category == 'DeFi':
            enhanced['category_risk_note'] = 'DeFi项目通常具有较高的智能合约风险'
        elif category == 'GameFi':
            enhanced['category_risk_note'] = 'GameFi项目依赖游戏采用率和玩家留存'
        elif category == 'Layer2':
            enhanced['category_risk_note'] = 'Layer2项目需要关注技术成熟度和生态发展'
        
        # 根据TGE日期调整时机建议
        if tge_analysis.get('tge_date'):
            try:
                from datetime import datetime
                tge_date = datetime.fromisoformat(tge_analysis['tge_date'])
                days_until_tge = (tge_date - datetime.now()).days
                
                if days_until_tge > 30:
                    enhanced['timing_note'] = 'TGE还有较长时间，可以持续关注项目进展'
                elif 0 < days_until_tge <= 30:
                    enhanced['timing_note'] = 'TGE即将到来，需要特别关注市场反应'
                elif days_until_tge <= 0:
                    enhanced['timing_note'] = 'TGE已经进行，需要关注代币表现和项目执行'
                    
            except Exception:
                pass
        
        # 计算综合评分
        overall_score = self._calculate_overall_score(
            investment_rating=enhanced['investment_rating'],
            potential_score=enhanced['potential_score'],
            risk_assessment=enhanced['risk_assessment']
        )
        enhanced['overall_score'] = overall_score
        
        return enhanced
    
    def _calculate_overall_score(self, investment_rating: int, potential_score: int, risk_assessment: str) -> float:
        """计算综合评分"""
        # 基础评分（投资评级 + 潜力评分）/ 2
        base_score = (investment_rating + potential_score) / 2
        
        # 风险调整
        risk_multiplier = {
            'Low': 1.1,
            'Medium': 1.0,
            'High': 0.8
        }.get(risk_assessment, 1.0)
        
        final_score = base_score * risk_multiplier
        return round(min(5.0, max(1.0, final_score)), 2)
    
    def _create_default_advice(self, tge_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """创建默认投资建议"""
        return {
            "investment_rating": 3,
            "risk_assessment": "Medium",
            "potential_score": 3,
            "key_advantages": [],
            "key_risks": ["信息不足，需要进一步研究"],
            "short_term_outlook": "由于AI分析不可用，无法提供明确建议",
            "recommendation": "谨慎",
            "reason": "AI分析系统暂时不可用，建议人工审核",
            "confidence_level": 0.0,
            "advice_timestamp": datetime.utcnow().isoformat(),
            "advice_status": "failed",
            "overall_score": 3.0
        }