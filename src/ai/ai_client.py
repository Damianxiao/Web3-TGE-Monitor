"""
AI客户端包装器
统一管理AI API调用
"""
import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

logger = structlog.get_logger()


class AIClient:
    """AI API客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化AI客户端
        
        Args:
            config: AI配置，包含api_url, api_key等
        """
        self.api_url = config.get('api_url', 'https://api.gpt.ge/v1/chat/completions')
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'gpt-3.5-turbo')
        self.timeout = config.get('timeout', 30)
        self.max_tokens = config.get('max_tokens', 2048)
        self.temperature = config.get('temperature', 0.3)
        
        # 配置HTTP客户端
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
        )
        
        logger.info("AI client initialized", 
                   api_url=self.api_url,
                   model=self.model)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> Optional[str]:
        """
        调用聊天补全API
        
        Args:
            messages: 消息列表，格式：[{"role": "user", "content": "..."}]
            **kwargs: 其他参数覆盖
            
        Returns:
            AI回复内容，失败返回None
        """
        try:
            # 构建请求参数
            payload = {
                'model': kwargs.get('model', self.model),
                'messages': messages,
                'max_tokens': kwargs.get('max_tokens', self.max_tokens),
                'temperature': kwargs.get('temperature', self.temperature),
                'stream': False
            }
            
            logger.debug("Sending AI request",
                        model=payload['model'],
                        message_count=len(messages),
                        max_tokens=payload['max_tokens'])
            
            # 发送请求
            response = await self.client.post(
                self.api_url,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error("AI API request failed",
                           status_code=response.status_code,
                           response_text=response.text)
                return None
            
            # 解析响应
            data = response.json()
            
            if 'choices' not in data or not data['choices']:
                logger.error("Invalid AI API response", response_data=data)
                return None
            
            content = data['choices'][0]['message']['content']
            
            # 记录使用统计
            usage = data.get('usage', {})
            logger.info("AI request completed",
                       prompt_tokens=usage.get('prompt_tokens', 0),
                       completion_tokens=usage.get('completion_tokens', 0),
                       total_tokens=usage.get('total_tokens', 0))
            
            return content.strip()
            
        except httpx.TimeoutException:
            logger.error("AI API request timeout")
            return None
        except Exception as e:
            logger.error("AI API request failed", error=str(e))
            return None
    
    async def analyze_content(
        self, 
        content: str, 
        analysis_type: str = "tge_analysis"
    ) -> Optional[Dict[str, Any]]:
        """
        分析内容
        
        Args:
            content: 要分析的内容
            analysis_type: 分析类型
            
        Returns:
            分析结果字典
        """
        try:
            # 构建分析提示
            if analysis_type == "tge_analysis":
                prompt = self._build_tge_analysis_prompt(content)
            elif analysis_type == "investment_advice":
                prompt = self._build_investment_prompt(content)
            elif analysis_type == "sentiment_analysis":
                prompt = self._build_sentiment_prompt(content)
            else:
                logger.error("Unknown analysis type", type=analysis_type)
                return None
            
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # 调用AI
            response = await self.chat_completion(messages)
            if not response:
                return None
            
            # 尝试解析JSON响应
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                # 如果不是JSON，返回文本结果
                return {"analysis": response, "type": analysis_type}
                
        except Exception as e:
            logger.error("Content analysis failed", 
                        analysis_type=analysis_type,
                        error=str(e))
            return None
    
    def _build_tge_analysis_prompt(self, content: str) -> str:
        """构建TGE分析提示"""
        return f"""请分析以下Web3/区块链项目内容，提取TGE相关信息。

内容：
{content}

请以JSON格式返回分析结果，包含以下字段：
{{
    "project_name": "项目名称",
    "token_symbol": "代币符号",
    "tge_date": "TGE日期（YYYY-MM-DD格式，如果有）",
    "project_category": "项目类别（DeFi/GameFi/NFT/Layer2/DAO/Other）",
    "key_features": ["关键特性列表"],
    "funding_info": "融资信息",
    "risk_level": "风险等级（Low/Medium/High）",
    "summary": "项目简要总结（50字以内）"
}}

如果某些信息无法从内容中提取，请设置为null。"""
    
    def _build_investment_prompt(self, content: str) -> str:
        """构建投资建议提示"""
        return f"""请基于以下Web3项目信息，提供简洁的投资分析建议。

项目信息：
{content}

请以JSON格式返回投资建议，包含以下字段：
{{
    "investment_rating": "投资评级（1-5分）",
    "risk_assessment": "风险评估（Low/Medium/High）",
    "potential_score": "潜力评分（1-5分）",
    "key_advantages": ["主要优势"],
    "key_risks": ["主要风险"],
    "short_term_outlook": "短期前景（30字以内）",
    "recommendation": "投资建议（关注/谨慎/避免）",
    "reason": "建议理由（50字以内）"
}}

请保持客观分析，基于公开信息进行评估。"""
    
    def _build_sentiment_prompt(self, content: str) -> str:
        """构建情感分析提示"""
        return f"""请分析以下内容的情感倾向和市场情绪。

内容：
{content}

请以JSON格式返回情感分析结果：
{{
    "sentiment_score": "情感评分（-1到1之间，-1最负面，1最正面）",
    "sentiment_label": "情感标签（Positive/Neutral/Negative）",
    "confidence": "置信度（0-1之间）",
    "key_emotions": ["检测到的关键情绪"],
    "market_sentiment": "市场情绪（Bullish/Neutral/Bearish）",
    "explanation": "情感分析说明（30字以内）"
}}

请基于文本的语言表达和情感词汇进行客观分析。"""
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局AI客户端实例（延迟初始化）
_ai_client_instance = None


def get_ai_client(config: Dict[str, Any] = None) -> AIClient:
    """获取AI客户端实例"""
    global _ai_client_instance
    
    if _ai_client_instance is None:
        if config is None:
            from ..config.settings import ai_config
            config = ai_config
        _ai_client_instance = AIClient(config)
    
    return _ai_client_instance


# 便捷访问
ai_client = get_ai_client()