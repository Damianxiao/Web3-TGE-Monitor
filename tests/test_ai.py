"""
AI模块测试
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.ai.ai_client import AIClient, get_ai_client
from src.ai.content_analyzer import ContentAnalyzer
from src.ai.investment_advisor import InvestmentAdvisor
from src.ai.sentiment_analyzer import SentimentAnalyzer
from src.ai.processing_manager import AIProcessingManager


class TestAIClient:
    """测试AI客户端"""
    
    def test_ai_client_initialization(self):
        """AI客户端初始化测试"""
        config = {
            'api_url': 'https://test.api.com',
            'api_key': 'test_key',
            'model': 'gpt-3.5-turbo',
            'timeout': 30
        }
        
        client = AIClient(config)
        
        assert client.api_url == 'https://test.api.com'
        assert client.api_key == 'test_key'
        assert client.model == 'gpt-3.5-turbo'
        assert client.timeout == 30
    
    def test_prompt_building(self):
        """AI提示构建测试"""
        client = AIClient({'api_key': 'test'})
        
        # 测试TGE分析提示
        tge_prompt = client._build_tge_analysis_prompt("测试内容")
        assert "测试内容" in tge_prompt
        assert "project_name" in tge_prompt
        assert "tge_date" in tge_prompt
        
        # 测试投资建议提示
        investment_prompt = client._build_investment_prompt("测试项目")
        assert "测试项目" in investment_prompt
        assert "investment_rating" in investment_prompt
        
        # 测试情感分析提示
        sentiment_prompt = client._build_sentiment_prompt("测试情感")
        assert "测试情感" in sentiment_prompt
        assert "sentiment_score" in sentiment_prompt
    
    @pytest.mark.asyncio
    async def test_ai_client_mock_response(self):
        """AI客户端模拟响应测试"""
        client = AIClient({'api_key': 'test'})
        
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': '{"project_name": "Test Project", "summary": "Test summary"}'
                }
            }],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        }
        
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            messages = [{"role": "user", "content": "test"}]
            result = await client.chat_completion(messages)
            
            assert result is not None
            assert "Test Project" in result


class TestContentAnalyzer:
    """测试内容分析器"""
    
    @pytest.mark.asyncio
    async def test_tge_analysis_standardization(self):
        """TGE分析结果标准化测试"""
        mock_ai_client = AsyncMock()
        analyzer = ContentAnalyzer(mock_ai_client)
        
        # 模拟AI返回结果
        raw_result = {
            "project_name": "TestCoin",
            "token_symbol": "TEST",
            "project_category": "DeFi",
            "tge_date": "2025-02-01",
            "risk_level": "Medium",
            "summary": "测试项目简介"
        }
        
        standardized = analyzer._standardize_tge_analysis(raw_result, "TestCoin")
        
        assert standardized['project_name'] == "TestCoin"
        assert standardized['token_symbol'] == "TEST"
        assert standardized['project_category'] == "DeFi"
        assert standardized['tge_date'] == "2025-02-01"
        assert standardized['risk_level'] == "Medium"
        assert 'analysis_timestamp' in standardized
    
    def test_date_validation(self):
        """TGE日期验证测试"""
        mock_ai_client = Mock()
        analyzer = ContentAnalyzer(mock_ai_client)
        
        # 有效日期
        valid_date = analyzer._validate_date("2025-01-15")
        assert valid_date == "2025-01-15"
        
        # 无效日期
        invalid_date = analyzer._validate_date("invalid-date")
        assert invalid_date is None
        
        # 空日期
        empty_date = analyzer._validate_date("")
        assert empty_date is None
    
    def test_default_analysis_creation(self):
        """TGE默认分析结果创建测试"""
        mock_ai_client = Mock()
        analyzer = ContentAnalyzer(mock_ai_client)
        
        default_analysis = analyzer._create_default_analysis("TestProject")
        
        assert default_analysis['project_name'] == "TestProject"
        assert default_analysis['project_category'] == "Other"
        assert default_analysis['risk_level'] == "Medium"
        assert default_analysis['analysis_confidence'] == 0.0
        assert 'analysis_timestamp' in default_analysis


class TestInvestmentAdvisor:
    """测试投资建议生成器"""
    
    def test_analysis_content_building(self):
        """投资分析内容构建测试"""
        mock_ai_client = Mock()
        advisor = InvestmentAdvisor(mock_ai_client)
        
        tge_analysis = {
            'project_name': 'TestCoin',
            'token_symbol': 'TEST',
            'project_category': 'DeFi',
            'tge_date': '2025-02-01',
            'key_features': ['去中心化', '高收益'],
            'funding_info': '1000万美元A轮融资',
            'summary': '创新的DeFi项目'
        }
        
        content = advisor._build_analysis_content(tge_analysis)
        
        assert 'TestCoin' in content
        assert 'TEST' in content
        assert 'DeFi' in content
        assert '2025-02-01' in content
        assert '去中心化' in content
    
    def test_investment_advice_standardization(self):
        """投资建议标准化测试"""
        mock_ai_client = Mock()
        advisor = InvestmentAdvisor(mock_ai_client)
        
        raw_advice = {
            "investment_rating": "4",
            "risk_assessment": "Medium",
            "potential_score": "3.5",
            "recommendation": "关注",
            "reason": "项目有潜力但需要观察"
        }
        
        tge_analysis = {'project_name': 'TestCoin'}
        standardized = advisor._standardize_investment_advice(raw_advice, tge_analysis)
        
        assert standardized['investment_rating'] == 4
        assert standardized['risk_assessment'] == "Medium"
        assert standardized['potential_score'] == 4  # 3.5四舍五入到4
        assert standardized['recommendation'] == "关注"
        assert 'advice_timestamp' in standardized
    
    def test_overall_score_calculation(self):
        """综合评分计算测试"""
        mock_ai_client = Mock()
        advisor = InvestmentAdvisor(mock_ai_client)
        
        # 低风险项目
        score_low_risk = advisor._calculate_overall_score(4, 3, "Low")
        assert score_low_risk > 3.5  # 应该有加分
        
        # 高风险项目
        score_high_risk = advisor._calculate_overall_score(4, 3, "High")
        assert score_high_risk < 3.5  # 应该有减分
        
        # 中等风险项目
        score_medium_risk = advisor._calculate_overall_score(4, 3, "Medium")
        assert score_medium_risk == 3.5  # 应该等于平均值


class TestSentimentAnalyzer:
    """测试情感分析器"""
    
    def test_keyword_sentiment_analysis(self):
        """关键词情感分析测试"""
        mock_ai_client = Mock()
        analyzer = SentimentAnalyzer(mock_ai_client)
        
        # 积极内容
        positive_content = "这个项目非常看好，有很大潜力，看涨！"
        positive_analysis = analyzer._analyze_keyword_sentiment(positive_content)
        assert positive_analysis['adjustment_factor'] > 0
        assert positive_analysis['positive_score'] > 0
        
        # 消极内容
        negative_content = "这个项目风险太大，看跌，建议避免"
        negative_analysis = analyzer._analyze_keyword_sentiment(negative_content)
        assert negative_analysis['adjustment_factor'] < 0
        assert negative_analysis['negative_score'] > 0
        
        # 中性内容
        neutral_content = "这是一个区块链项目的介绍"
        neutral_analysis = analyzer._analyze_keyword_sentiment(neutral_content)
        assert abs(neutral_analysis['adjustment_factor']) < 0.1
    
    def test_numeric_indicators_extraction(self):
        """数值指标提取测试"""
        mock_ai_client = Mock()
        analyzer = SentimentAnalyzer(mock_ai_client)
        
        content = "代币价格上涨+15%，现价$1.23 USDT，明天可能会继续上涨"
        indicators = analyzer._extract_numeric_indicators(content)
        
        assert len(indicators['percentage_changes']) > 0
        assert '+15%' in indicators['percentage_changes']
        assert len(indicators['price_mentions']) > 0
        assert len(indicators['time_references']) > 0
    
    def test_fallback_sentiment_creation(self):
        """后备情感分析创建测试"""
        mock_ai_client = Mock()
        analyzer = SentimentAnalyzer(mock_ai_client)
        
        # 积极内容
        positive_content = "这个项目非常看好，有潜力"
        positive_sentiment = analyzer._create_fallback_sentiment(positive_content)
        assert positive_sentiment['sentiment_label'] == "Positive"
        assert positive_sentiment['sentiment_score'] > 0
        
        # 消极内容
        negative_content = "这个项目危险，建议避免"
        negative_sentiment = analyzer._create_fallback_sentiment(negative_content)
        assert negative_sentiment['sentiment_label'] == "Negative"
        assert negative_sentiment['sentiment_score'] < 0


class TestAIProcessingManager:
    """测试AI处理管理器"""
    
    def test_analysis_results_integration(self):
        """AI分析结果整合测试"""
        manager = AIProcessingManager()
        
        analysis_results = {
            'tge_analysis': {
                'project_name': 'TestCoin',
                'token_symbol': 'TEST',
                'project_category': 'DeFi',
                'summary': '测试项目',
                'analysis_confidence': 0.8
            },
            'investment_advice': {
                'investment_rating': 4,
                'recommendation': '关注',
                'reason': '有潜力',
                'confidence_level': 0.7,
                'overall_score': 3.8
            },
            'sentiment_analysis': {
                'sentiment_score': 0.3,
                'sentiment_label': 'Positive',
                'market_sentiment': 'Bullish',
                'confidence': 0.6
            }
        }
        
        integrated = manager._integrate_analysis_results(analysis_results)
        
        # 验证关键字段
        assert integrated['project_name'] == 'TestCoin'
        assert integrated['token_symbol'] == 'TEST'
        assert integrated['investment_rating'] == 4
        assert integrated['sentiment_score'] == 0.3
        assert integrated['overall_score'] == 3.8
        
        # 验证综合置信度
        assert 0.6 < integrated['analysis_confidence'] < 0.8
        
        # 验证元数据
        assert 'analysis_timestamp' in integrated
        assert 'raw_results' in integrated
    
    def test_overall_confidence_calculation(self):
        """综合置信度计算测试"""
        manager = AIProcessingManager()
        
        # 包含所有分析类型
        full_results = {
            'tge_analysis': {'analysis_confidence': 0.8},
            'investment_advice': {'confidence_level': 0.7},
            'sentiment_analysis': {'confidence': 0.6}
        }
        
        confidence = manager._calculate_overall_confidence(full_results)
        expected = (0.8 + 0.7 + 0.6) / 3
        assert abs(confidence - expected) < 0.01
        
        # 只包含TGE分析
        partial_results = {
            'tge_analysis': {'analysis_confidence': 0.9}
        }
        
        confidence = manager._calculate_overall_confidence(partial_results)
        assert confidence == 0.9
        
        # 空结果
        empty_results = {}
        confidence = manager._calculate_overall_confidence(empty_results)
        assert confidence == 0.5


# Mock数据和工具函数
class MockAIResponse:
    """模拟AI响应类"""
    
    @staticmethod
    def tge_analysis_response():
        return {
            "project_name": "MockCoin",
            "token_symbol": "MOCK",
            "project_category": "DeFi",
            "tge_date": "2025-03-01",
            "key_features": ["去中心化", "高收益"],
            "risk_level": "Medium",
            "summary": "模拟测试项目"
        }
    
    @staticmethod
    def investment_advice_response():
        return {
            "investment_rating": 3,
            "risk_assessment": "Medium",
            "potential_score": 4,
            "recommendation": "谨慎",
            "reason": "项目有潜力但需要观察"
        }
    
    @staticmethod
    def sentiment_analysis_response():
        return {
            "sentiment_score": 0.2,
            "sentiment_label": "Positive",
            "confidence": 0.7,
            "market_sentiment": "Neutral",
            "explanation": "整体积极但谨慎乐观"
        }


@pytest.fixture
def mock_ai_client():
    """模拟AI客户端固定装置"""
    mock_client = AsyncMock()
    
    async def mock_analyze_content(content, analysis_type):
        if analysis_type == "tge_analysis":
            return MockAIResponse.tge_analysis_response()
        elif analysis_type == "investment_advice":
            return MockAIResponse.investment_advice_response()
        elif analysis_type == "sentiment_analysis":
            return MockAIResponse.sentiment_analysis_response()
        return None
    
    mock_client.analyze_content = mock_analyze_content
    return mock_client


@pytest.mark.asyncio
async def test_integration_full_ai_processing_flow(mock_ai_client):
    """集成测试：完整AI处理流程"""
    # 创建各个组件
    analyzer = ContentAnalyzer(mock_ai_client)
    advisor = InvestmentAdvisor(mock_ai_client)
    sentiment_analyzer = SentimentAnalyzer(mock_ai_client)
    
    # 模拟内容
    test_content = "这是一个创新的DeFi项目MockCoin，将在2025年3月进行TGE"
    project_id = 1
    project_name = "MockCoin"
    
    # 步骤1：TGE分析
    tge_result = await analyzer.analyze_tge_content(
        project_id=project_id,
        content=test_content,
        project_name=project_name
    )
    
    assert tge_result['project_name'] == "MockCoin"
    assert tge_result['project_category'] == "DeFi"
    
    # 步骤2：投资建议
    investment_result = await advisor.generate_investment_advice(
        project_id=project_id,
        tge_analysis=tge_result
    )
    
    assert investment_result['investment_rating'] == 3
    assert investment_result['recommendation'] == "谨慎"
    
    # 步骤3：情感分析
    sentiment_result = await sentiment_analyzer.analyze_sentiment(
        content=test_content,
        project_name=project_name
    )
    
    assert sentiment_result['sentiment_label'] == "Positive"
    assert sentiment_result['sentiment_score'] >= 0
    
    # 验证所有结果都成功返回
    assert tge_result is not None
    assert investment_result is not None
    assert sentiment_result is not None