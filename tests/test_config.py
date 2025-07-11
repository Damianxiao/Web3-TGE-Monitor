"""
配置模块测试
"""
import pytest
from src.config.settings import Settings
from src.config.keywords import (
    get_all_keywords, 
    get_weighted_keywords, 
    is_risk_keyword, 
    get_sentiment_score,
    CORE_KEYWORDS,
    RISK_KEYWORDS,
    POSITIVE_KEYWORDS,
    NEGATIVE_KEYWORDS
)


class TestSettings:
    """设置配置测试"""
    
    def test_default_settings(self):
        """测试默认设置"""
        settings = Settings()
        
        assert settings.mysql_host == "localhost"
        assert settings.mysql_port == 3306
        assert settings.app_port == 8000
        assert settings.ai_model == "gpt-4o"
    
    def test_database_url(self):
        """测试数据库URL生成"""
        settings = Settings(
            mysql_user="test_user",
            mysql_password="test_pass",
            mysql_host="test_host",
            mysql_port=3307,
            mysql_db="test_db"
        )
        
        expected_url = "mysql+aiomysql://test_user:test_pass@test_host:3307/test_db"
        assert settings.database_url == expected_url
    
    def test_redis_url_with_password(self):
        """测试带密码的Redis URL"""
        settings = Settings(
            redis_host="test_host",
            redis_port=6380,
            redis_password="test_pass",
            redis_db=1
        )
        
        expected_url = "redis://:test_pass@test_host:6380/1"
        assert settings.redis_url == expected_url
    
    def test_redis_url_without_password(self):
        """测试不带密码的Redis URL"""
        settings = Settings(
            redis_host="test_host",
            redis_port=6379,
            redis_password="",
            redis_db=0
        )
        
        expected_url = "redis://test_host:6379/0"
        assert settings.redis_url == expected_url


class TestKeywords:
    """关键词配置测试"""
    
    def test_get_all_keywords(self):
        """测试获取所有关键词"""
        all_keywords = get_all_keywords()
        
        assert isinstance(all_keywords, list)
        assert len(all_keywords) > 0
        assert "TGE" in all_keywords
        assert "代币发行" in all_keywords
    
    def test_get_weighted_keywords(self):
        """测试获取带权重的关键词"""
        weighted_keywords = get_weighted_keywords()
        
        assert isinstance(weighted_keywords, dict)
        assert "TGE" in weighted_keywords
        assert weighted_keywords["TGE"] == 1.0
        assert all(isinstance(weight, float) for weight in weighted_keywords.values())
    
    def test_is_risk_keyword(self):
        """测试风险关键词检测"""
        # 包含风险关键词的文本
        risk_text = "这个项目风险很高，请谨慎投资"
        assert is_risk_keyword(risk_text) is True
        
        # 不包含风险关键词的文本
        normal_text = "这是一个DeFi项目，即将进行TGE"
        assert is_risk_keyword(normal_text) is False
    
    def test_get_sentiment_score(self):
        """测试情感得分计算"""
        # 正面文本
        positive_text = "看涨的好项目，强烈推荐，潜力巨大"
        positive_score = get_sentiment_score(positive_text)
        assert positive_score > 0
        
        # 负面文本
        negative_text = "看跌的项目，风险高，不推荐投资"
        negative_score = get_sentiment_score(negative_text)
        assert negative_score < 0
        
        # 中性文本
        neutral_text = "这是一个新的DeFi项目"
        neutral_score = get_sentiment_score(neutral_text)
        assert neutral_score == 0.0
        
        # 混合文本（更多正面）
        mixed_text = "看涨的项目，但是风险不小，总体推荐关注"
        mixed_score = get_sentiment_score(mixed_text)
        assert -1.0 <= mixed_score <= 1.0
    
    def test_core_keywords_not_empty(self):
        """测试核心关键词列表不为空"""
        assert len(CORE_KEYWORDS) > 0
        assert "TGE" in CORE_KEYWORDS
        assert "代币发行" in CORE_KEYWORDS
    
    def test_risk_keywords_not_empty(self):
        """测试风险关键词列表不为空"""
        assert len(RISK_KEYWORDS) > 0
        assert "风险" in RISK_KEYWORDS
    
    def test_sentiment_keywords_not_empty(self):
        """测试情感关键词列表不为空"""
        assert len(POSITIVE_KEYWORDS) > 0
        assert len(NEGATIVE_KEYWORDS) > 0
        assert "看涨" in POSITIVE_KEYWORDS
        assert "看跌" in NEGATIVE_KEYWORDS
    
    def test_keywords_no_overlap(self):
        """测试正负情感关键词没有重叠"""
        positive_set = set(POSITIVE_KEYWORDS)
        negative_set = set(NEGATIVE_KEYWORDS)
        
        overlap = positive_set.intersection(negative_set)
        assert len(overlap) == 0, f"Found overlapping keywords: {overlap}"