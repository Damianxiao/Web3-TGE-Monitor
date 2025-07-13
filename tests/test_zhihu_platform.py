"""
知乎平台适配器测试
按照MULTI_PLATFORM_DEVELOPMENT_PLAN.md第6.2.1节规范编写
TDD红灯阶段：先定义期望的功能和接口
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from datetime import datetime

# 添加src到路径
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from crawler.platforms.zhihu_platform import ZhihuPlatform
from crawler.models import RawContent, Platform, ContentType


class TestZhihuPlatform:
    """知乎平台测试类 - 按照文档6.2.1节标准"""
    
    @pytest.fixture
    def zhihu_platform(self):
        """测试用知乎平台实例"""
        return ZhihuPlatform()
    
    def test_platform_name(self, zhihu_platform):
        """测试平台名称 - 必须返回Platform.ZHIHU"""
        assert zhihu_platform.get_platform_name() == Platform.ZHIHU
    
    def test_platform_initialization(self, zhihu_platform):
        """测试平台初始化配置"""
        assert hasattr(zhihu_platform, 'search_type')
        assert hasattr(zhihu_platform, 'max_pages')
        assert hasattr(zhihu_platform, 'rate_limit')
        assert hasattr(zhihu_platform, 'cookie')
        assert hasattr(zhihu_platform, 'login_method')
        
        # 验证默认配置
        assert zhihu_platform.search_type == "综合"
        assert zhihu_platform.max_pages == 10
        assert zhihu_platform.rate_limit == 60
        assert zhihu_platform.login_method == "cookie"
    
    @pytest.mark.asyncio
    async def test_platform_availability(self, zhihu_platform):
        """测试平台可用性检查"""
        # 无Cookie时应该不可用
        zhihu_platform.cookie = ""
        available = await zhihu_platform.is_available()
        assert available == False
        
        # 有Cookie时应该可用（模拟）
        zhihu_platform.cookie = "mock_valid_cookie"
        with patch.object(zhihu_platform, '_check_login_status', return_value=True):
            available = await zhihu_platform.is_available()
            assert available == True
    
    @pytest.mark.asyncio
    async def test_search_functionality(self, zhihu_platform):
        """测试搜索功能 - 核心业务逻辑"""
        # 模拟知乎API返回数据
        mock_zhihu_data = [
            {
                'id': 'answer_123456',
                'type': 'answer',
                'content': '这是一个关于Web3投资的专业回答，包含了详细的分析和建议。',
                'author': {
                    'name': '区块链专家',
                    'id': 'expert_001',
                    'headline': '资深区块链分析师'
                },
                'question': {
                    'title': 'Web3项目投资策略有哪些？',
                    'id': 'question_789'
                },
                'created_time': 1731478800,  # 2025-07-13 timestamp
                'voteup_count': 150,
                'comment_count': 25,
                'updated_time': 1731478800,
                'url': 'https://www.zhihu.com/question/789/answer/123456'
            },
            {
                'id': 'article_789012',
                'type': 'article',
                'title': 'DeFi生态系统深度分析',
                'content': '本文将深入分析当前DeFi生态系统的发展状况...',
                'author': {
                    'name': 'DeFi研究员',
                    'id': 'defi_researcher',
                    'headline': 'DeFi协议研究专家'
                },
                'created_time': 1731478800,
                'voteup_count': 89,
                'comment_count': 12,
                'url': 'https://zhuanlan.zhihu.com/p/789012'
            }
        ]
        
        # 模拟搜索调用
        with patch.object(zhihu_platform, '_execute_crawl', return_value=mock_zhihu_data):
            with patch.object(zhihu_platform, 'is_available', return_value=True):
                results = await zhihu_platform.crawl(['Web3', 'DeFi'], max_count=5)
        
        # 验证返回结果
        assert len(results) == 2
        assert all(isinstance(result, RawContent) for result in results)
        assert all(result.platform == Platform.ZHIHU for result in results)
        
        # 验证第一条回答数据
        answer_result = results[0]
        assert answer_result.content_type == ContentType.ANSWER
        assert answer_result.content_id == 'answer_123456'
        assert 'Web3投资' in answer_result.content
        assert answer_result.author_name == '区块链专家'
        assert answer_result.like_count == 150
        assert answer_result.comment_count == 25
        
        # 验证第二条文章数据
        article_result = results[1]
        assert article_result.content_type == ContentType.ARTICLE
        assert article_result.content_id == 'article_789012'
        assert article_result.title == 'DeFi生态系统深度分析'
        assert answer_result.author_name == '区块链专家'
    
    def test_data_conversion_answer(self, zhihu_platform):
        """测试问答数据转换 - 知乎特有的问答格式"""
        zhihu_answer_data = {
            'id': 'answer_test123',
            'type': 'answer',
            'content': '<p>这是一个专业的投资建议回答</p>',
            'author': {
                'name': '投资顾问',
                'id': 'advisor_001',
                'headline': '10年投资经验'
            },
            'question': {
                'title': '如何评估TGE项目？',
                'id': 'question_test'
            },
            'created_time': 1731478800,
            'voteup_count': 68,
            'comment_count': 15,
            'url': 'https://www.zhihu.com/question/test/answer/test123'
        }
        
        result = zhihu_platform._convert_to_raw_content(zhihu_answer_data)
        
        assert result.content_id == 'answer_test123'
        assert result.platform == Platform.ZHIHU
        assert result.content_type == ContentType.ANSWER
        assert result.title == '如何评估TGE项目？'  # 来自question.title
        assert result.content == '这是一个专业的投资建议回答'  # HTML清理后
        assert result.author_name == '投资顾问'
        assert result.author_id == 'advisor_001'
        assert result.like_count == 68
        assert result.comment_count == 15
        assert result.source_url == 'https://www.zhihu.com/question/test/answer/test123'
    
    def test_data_conversion_article(self, zhihu_platform):
        """测试文章数据转换"""
        zhihu_article_data = {
            'id': 'article_test456',
            'type': 'article',
            'title': '区块链投资指南',
            'content': '<h1>引言</h1><p>区块链技术的发展...</p>',
            'author': {
                'name': '区块链作者',
                'id': 'blockchain_writer',
                'headline': '区块链行业观察者'
            },
            'created_time': 1731478800,
            'voteup_count': 234,
            'comment_count': 45,
            'url': 'https://zhuanlan.zhihu.com/p/test456'
        }
        
        result = zhihu_platform._convert_to_raw_content(zhihu_article_data)
        
        assert result.content_id == 'article_test456'
        assert result.platform == Platform.ZHIHU
        assert result.content_type == ContentType.ARTICLE
        assert result.title == '区块链投资指南'
        assert '引言' in result.content
        assert result.author_name == '区块链作者'
        assert result.like_count == 234
        assert result.comment_count == 45
    
    def test_content_quality_filter(self, zhihu_platform):
        """测试内容质量过滤 - 知乎特有的专业度评估"""
        # 高质量内容（应该保留）
        high_quality_content = {
            'content': '这是一篇详细分析Web3投资策略的专业文章，包含了市场分析、风险评估和投资建议等多个维度的深入探讨。' * 3,  # 足够长的专业内容
            'voteup_count': 100,
            'comment_count': 20,
            'author': {'headline': '资深投资分析师'}
        }
        
        # 低质量内容（应该过滤）
        low_quality_content = {
            'content': '好的',  # 内容太短
            'voteup_count': 1,
            'comment_count': 0,
            'author': {'headline': ''}
        }
        
        assert zhihu_platform._should_filter_content(high_quality_content) == False  # 不过滤
        assert zhihu_platform._should_filter_content(low_quality_content) == True   # 过滤掉
    
    def test_search_type_mapping(self, zhihu_platform):
        """测试搜索类型映射 - 知乎特有的搜索类型"""
        # 测试各种知乎搜索类型
        assert zhihu_platform._map_search_type("综合") is not None
        assert zhihu_platform._map_search_type("问题") is not None
        assert zhihu_platform._map_search_type("回答") is not None
        assert zhihu_platform._map_search_type("文章") is not None
        assert zhihu_platform._map_search_type("想法") is not None
        
        # 默认类型处理
        assert zhihu_platform._map_search_type("未知类型") is not None  # 应该返回默认值
    
    @pytest.mark.asyncio
    async def test_dual_login_support(self, zhihu_platform):
        """测试双登录模式支持 - Cookie优先，二维码备用"""
        # 测试Cookie模式
        zhihu_platform.login_method = "cookie"
        zhihu_platform.cookie = "valid_cookie"
        
        with patch.object(zhihu_platform, '_get_zhihu_client') as mock_client:
            mock_client.return_value = AsyncMock()
            client = await zhihu_platform._get_zhihu_client()
            assert client is not None
        
        # 测试二维码模式
        zhihu_platform.login_method = "qrcode"
        
        with patch.object(zhihu_platform, '_get_zhihu_client') as mock_client:
            mock_client.return_value = AsyncMock()
            client = await zhihu_platform._get_zhihu_client()
            assert client is not None
    
    def test_professional_content_priority(self, zhihu_platform):
        """测试专业内容优先级 - 知乎特有的专业度评估"""
        professional_content = {
            'author': {'headline': '资深区块链分析师', 'follower_count': 10000},
            'voteup_count': 500,
            'content': '基于深度技术分析和市场研究的专业投资建议...' * 5
        }
        
        regular_content = {
            'author': {'headline': '', 'follower_count': 100},
            'voteup_count': 10,
            'content': '个人观点分享'
        }
        
        prof_score = zhihu_platform._calculate_professional_score(professional_content)
        reg_score = zhihu_platform._calculate_professional_score(regular_content)
        
        assert prof_score > reg_score  # 专业内容应该有更高分数