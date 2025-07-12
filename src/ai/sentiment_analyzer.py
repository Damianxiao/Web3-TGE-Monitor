"""
情感分析器
分析内容情感和市场情绪
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from .ai_client import get_ai_client

logger = structlog.get_logger()


class SentimentAnalyzer:
    """情感分析器"""
    
    def __init__(self, ai_client=None):
        self.ai_client = ai_client or get_ai_client()
    
    async def analyze_sentiment(
        self, 
        content: str, 
        project_name: str = None
    ) -> Dict[str, Any]:
        """
        分析内容情感
        
        Args:
            content: 要分析的内容
            project_name: 项目名称（可选）
            
        Returns:
            情感分析结果
        """
        try:
            logger.debug("Starting sentiment analysis", 
                        content_length=len(content),
                        project_name=project_name)
            
            # 调用AI情感分析
            sentiment_result = await self.ai_client.analyze_content(
                content=content,
                analysis_type="sentiment_analysis"
            )
            
            if not sentiment_result:
                logger.warning("AI sentiment analysis failed, using fallback")
                return self._create_fallback_sentiment(content)
            
            # 标准化结果
            standardized_result = self._standardize_sentiment_result(sentiment_result)
            
            # 添加额外的本地分析
            enhanced_result = self._enhance_with_local_analysis(standardized_result, content)
            
            logger.debug("Sentiment analysis completed", 
                        sentiment_label=enhanced_result.get('sentiment_label'),
                        sentiment_score=enhanced_result.get('sentiment_score'))
            
            return enhanced_result
            
        except Exception as e:
            logger.error("Sentiment analysis failed", error=str(e))
            return self._create_fallback_sentiment(content)
    
    async def batch_analyze_sentiment(
        self, 
        contents: List[Dict[str, str]], 
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        批量情感分析
        
        Args:
            contents: 内容列表，每项包含content和project_name
            max_concurrent: 最大并发数
            
        Returns:
            情感分析结果列表
        """
        import asyncio
        
        logger.info("Starting batch sentiment analysis", batch_size=len(contents))
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_single(item):
            async with semaphore:
                return await self.analyze_sentiment(
                    content=item['content'],
                    project_name=item.get('project_name')
                )
        
        # 并发执行
        tasks = [analyze_single(item) for item in contents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Batch sentiment analysis failed", 
                           item_index=i,
                           error=str(result))
                processed_results.append(
                    self._create_fallback_sentiment(contents[i]['content'])
                )
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _standardize_sentiment_result(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化情感分析结果"""
        # 默认结构
        standard_result = {
            "sentiment_score": 0.0,  # -1到1之间
            "sentiment_label": "Neutral",
            "confidence": 0.5,
            "key_emotions": [],
            "market_sentiment": "Neutral",
            "explanation": "情感分析结果",
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        # 如果是文本格式的结果
        if isinstance(raw_result, dict) and "analysis" in raw_result:
            standard_result["explanation"] = raw_result["analysis"][:100]
            return standard_result
        
        # 如果是结构化结果
        if isinstance(raw_result, dict):
            # 情感评分
            if raw_result.get('sentiment_score') is not None:
                try:
                    score = float(raw_result['sentiment_score'])
                    standard_result['sentiment_score'] = max(-1.0, min(1.0, score))
                except (ValueError, TypeError):
                    pass
            
            # 情感标签
            if raw_result.get('sentiment_label') in ['Positive', 'Neutral', 'Negative']:
                standard_result['sentiment_label'] = raw_result['sentiment_label']
            
            # 置信度
            if raw_result.get('confidence') is not None:
                try:
                    conf = float(raw_result['confidence'])
                    standard_result['confidence'] = max(0.0, min(1.0, conf))
                except (ValueError, TypeError):
                    pass
            
            # 关键情绪
            if raw_result.get('key_emotions') and isinstance(raw_result['key_emotions'], list):
                standard_result['key_emotions'] = [str(emotion)[:50] for emotion in raw_result['key_emotions'][:5]]
            
            # 市场情绪
            if raw_result.get('market_sentiment') in ['Bullish', 'Neutral', 'Bearish']:
                standard_result['market_sentiment'] = raw_result['market_sentiment']
            
            # 说明
            if raw_result.get('explanation'):
                standard_result['explanation'] = str(raw_result['explanation'])[:200]
        
        return standard_result
    
    def _enhance_with_local_analysis(self, sentiment_result: Dict[str, Any], content: str) -> Dict[str, Any]:
        """使用本地分析增强情感结果"""
        enhanced = sentiment_result.copy()
        
        # 关键词情感分析
        keyword_sentiment = self._analyze_keyword_sentiment(content)
        enhanced['keyword_sentiment'] = keyword_sentiment
        
        # 数值指标分析
        numeric_indicators = self._extract_numeric_indicators(content)
        enhanced['numeric_indicators'] = numeric_indicators
        
        # 综合评分调整
        if keyword_sentiment.get('adjustment_factor'):
            original_score = enhanced['sentiment_score']
            adjustment = keyword_sentiment['adjustment_factor']
            enhanced['sentiment_score'] = max(-1.0, min(1.0, original_score + adjustment))
            enhanced['local_adjustment'] = adjustment
        
        return enhanced
    
    def _analyze_keyword_sentiment(self, content: str) -> Dict[str, Any]:
        """分析关键词情感"""
        # 情感关键词字典
        positive_keywords = {
            '看好': 0.3, '看涨': 0.4, '乐观': 0.3, '看好': 0.3,
            '潜力': 0.2, '突破': 0.3, '上涨': 0.4, '爆发': 0.5,
            '优质': 0.2, '顶级': 0.3, '新高': 0.4, '爆炸': 0.5,
            'bullish': 0.4, 'moon': 0.5, 'pump': 0.4, 'gem': 0.3
        }
        
        negative_keywords = {
            '看跌': -0.4, '悲观': -0.3, '风险': -0.2, '警告': -0.3,
            '跌落': -0.4, '崩盘': -0.5, '退出': -0.3, '亚疾': -0.2,
            '骗局': -0.5, '跑路': -0.5, '失败': -0.4, '危险': -0.3,
            'bearish': -0.4, 'dump': -0.4, 'crash': -0.5, 'scam': -0.5
        }
        
        content_lower = content.lower()
        
        positive_score = 0
        negative_score = 0
        matched_keywords = []
        
        # 积极关键词匹配
        for keyword, weight in positive_keywords.items():
            if keyword in content_lower:
                positive_score += weight
                matched_keywords.append(f"+{keyword}")
        
        # 消极关键词匹配
        for keyword, weight in negative_keywords.items():
            if keyword in content_lower:
                negative_score += abs(weight)
                matched_keywords.append(f"-{keyword}")
        
        # 计算调整因子
        net_score = positive_score - negative_score
        adjustment_factor = max(-0.3, min(0.3, net_score * 0.5))
        
        return {
            'positive_score': positive_score,
            'negative_score': negative_score,
            'net_score': net_score,
            'adjustment_factor': adjustment_factor,
            'matched_keywords': matched_keywords
        }
    
    def _extract_numeric_indicators(self, content: str) -> Dict[str, Any]:
        """提取数值指标"""
        import re
        
        indicators = {
            'percentage_changes': [],
            'price_mentions': [],
            'volume_mentions': [],
            'time_references': []
        }
        
        # 百分比变化
        percentage_pattern = r'[+\-]?\d+(?:\.\d+)?%'
        percentages = re.findall(percentage_pattern, content)
        indicators['percentage_changes'] = percentages[:5]  # 限制数量
        
        # 价格提及
        price_patterns = [
            r'\$\d+(?:\.\d+)?',  # $1.23
            r'\d+(?:\.\d+)?\s*美元',  # 1.23美元
            r'\d+(?:\.\d+)?\s*USDT'  # 1.23 USDT
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            indicators['price_mentions'].extend(matches[:3])
        
        # 时间引用
        time_patterns = [
            r'\d+天',
            r'\d+小时',
            r'\d+分钟',
            r'明天|今天|昨天',
            r'下周|下月'
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, content)
            indicators['time_references'].extend(matches[:3])
        
        return indicators
    
    def _create_fallback_sentiment(self, content: str) -> Dict[str, Any]:
        """创建后备情感分析结果"""
        # 简单的本地情感分析
        keyword_analysis = self._analyze_keyword_sentiment(content)
        
        # 基于关键词分析确定情感
        net_score = keyword_analysis.get('net_score', 0)
        
        if net_score > 0.1:
            sentiment_label = "Positive"
            sentiment_score = min(0.7, net_score)
        elif net_score < -0.1:
            sentiment_label = "Negative"
            sentiment_score = max(-0.7, net_score)
        else:
            sentiment_label = "Neutral"
            sentiment_score = 0.0
        
        return {
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "confidence": 0.3,  # 较低的置信度
            "key_emotions": keyword_analysis.get('matched_keywords', [])[:3],
            "market_sentiment": "Neutral",
            "explanation": f"基于关键词的本地分析，净得分: {net_score:.2f}",
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "analysis_method": "local_fallback",
            "keyword_sentiment": keyword_analysis
        }