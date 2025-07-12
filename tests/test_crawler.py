"""
爬虫模块测试
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from src.crawler.models import Platform, RawContent, ContentType, CrawlTask, CrawlResult
from src.crawler.platform_factory import PlatformFactory
from src.crawler.crawler_manager import CrawlerManager
from src.crawler.data_service import CrawlDataService


class TestCrawlerModels:
    """爬虫模型测试"""
    
    def test_raw_content_creation(self):
        """测试RawContent创建"""
        content = RawContent(
            platform=Platform.XHS,
            content_id="test_001",
            content_type=ContentType.TEXT,
            title="测试标题",
            content="测试内容",
            raw_content="原始内容",
            author_id="author_001",
            author_name="测试作者",
            publish_time=datetime.utcnow(),
            crawl_time=datetime.utcnow(),
            source_url="https://test.com/001"
        )
        
        assert content.platform == Platform.XHS
        assert content.content_id == "test_001"
        assert content.title == "测试标题"
        assert isinstance(content.to_dict(), dict)
    
    def test_raw_content_count_parsing(self):
        """测试数量字段解析"""
        # 测试中文数字解析
        content = RawContent(
            platform=Platform.XHS,
            content_id="test_002",
            content_type=ContentType.TEXT,
            title="测试",
            content="测试",
            raw_content="测试",
            author_id="test",
            author_name="test",
            publish_time=datetime.utcnow(),
            crawl_time=datetime.utcnow(),
            source_url="https://test.com",
            like_count="1.5万",
            comment_count="500"
        )
        
        assert content.like_count == 15000
        assert content.comment_count == 500
    
    def test_crawl_task_creation(self):
        """测试爬取任务创建"""
        task = CrawlTask(
            task_id="task_001",
            platform=Platform.XHS,
            keywords=["TGE", "代币发行"],
            max_count=50,
            created_at=datetime.utcnow()
        )
        
        assert task.task_id == "task_001"
        assert task.platform == Platform.XHS
        assert len(task.keywords) == 2
        assert task.status == "pending"
    
    def test_crawl_result_summary(self):
        """测试爬取结果摘要"""
        result = CrawlResult(
            task_id="task_001",
            platform=Platform.XHS,
            contents=[],
            total_count=10,
            success_count=8,
            duplicate_count=1,
            error_count=1,
            execution_time=15.5,
            keywords_used=["TGE"]
        )
        
        summary = result.get_summary()
        assert summary["total_found"] == 10
        assert summary["success_saved"] == 8
        assert summary["duplicates_skipped"] == 1
        assert "15.50s" in summary["execution_time"]


class TestPlatformFactory:
    """平台工厂测试"""
    
    def setUp(self):
        """测试前清理"""
        PlatformFactory.clear_instances()
    
    def test_platform_registration(self):
        """测试平台注册"""
        # 创建Mock平台类
        mock_platform_class = Mock()
        
        # 注册平台
        PlatformFactory.register(Platform.XHS, mock_platform_class)
        
        # 验证注册
        assert PlatformFactory.is_platform_registered(Platform.XHS)
        assert Platform.XHS in PlatformFactory.get_registered_platforms()
    
    def test_platform_unregistration(self):
        """测试平台注销"""
        mock_platform_class = Mock()
        
        # 注册然后注销
        PlatformFactory.register(Platform.XHS, mock_platform_class)
        PlatformFactory.unregister(Platform.XHS)
        
        # 验证注销
        assert not PlatformFactory.is_platform_registered(Platform.XHS)
    
    @pytest.mark.asyncio
    async def test_create_platform_not_registered(self):
        """测试创建未注册的平台"""
        with pytest.raises(ValueError, match="not registered"):
            await PlatformFactory.create_platform(Platform.DOUYIN)
    
    @pytest.mark.asyncio
    async def test_create_platform_unavailable(self):
        """测试创建不可用的平台"""
        # 创建Mock平台
        mock_platform = Mock()
        mock_platform.is_available = AsyncMock(return_value=False)
        mock_platform_class = Mock(return_value=mock_platform)
        
        # 注册平台
        PlatformFactory.register(Platform.XHS, mock_platform_class)
        
        # 尝试创建应该失败
        with pytest.raises(RuntimeError, match="not available"):
            await PlatformFactory.create_platform(Platform.XHS)


class TestCrawlerManager:
    """爬虫管理器测试"""
    
    def setUp(self):
        """测试前清理"""
        self.crawler_manager = CrawlerManager()
    
    @pytest.mark.asyncio
    async def test_submit_crawl_task(self):
        """测试提交爬取任务"""
        task_id = await self.crawler_manager.submit_crawl_task(
            platform=Platform.XHS,
            keywords=["TGE", "代币发行"],
            max_count=10
        )
        
        assert task_id is not None
        assert len(task_id) > 0
        
        # 验证任务已创建
        task = await self.crawler_manager.get_task_status(task_id)
        assert task is not None
        assert task.platform == Platform.XHS
        assert task.keywords == ["TGE", "代币发行"]
    
    @pytest.mark.asyncio
    async def test_submit_task_with_default_keywords(self):
        """测试使用默认关键词提交任务"""
        task_id = await self.crawler_manager.submit_crawl_task(
            platform=Platform.XHS,
            max_count=5
        )
        
        task = await self.crawler_manager.get_task_status(task_id)
        assert task is not None
        assert len(task.keywords) > 0  # 应该有默认关键词
    
    def test_contains_web3_keywords(self):
        """测试Web3关键词检查"""
        manager = CrawlerManager()
        
        # 包含Web3关键词的文本
        text_with_web3 = "这个项目即将进行TGE，代币发行总量1亿"
        assert manager._contains_web3_keywords(text_with_web3)
        
        # 不包含Web3关键词的文本
        text_without_web3 = "今天天气很好，适合出门"
        assert not manager._contains_web3_keywords(text_without_web3)


class TestCrawlDataService:
    """爬虫数据服务测试"""
    
    @pytest.mark.asyncio
    async def test_process_single_content_extraction(self):
        """测试单个内容处理中的信息提取"""
        service = CrawlDataService()
        
        # 创建测试内容
        content = RawContent(
            platform=Platform.XHS,
            content_id="test_content",
            content_type=ContentType.TEXT,
            title="ABC Token项目TGE公告",
            content="ABC项目将于2025年1月15日进行代币发行，总供应量1亿ABC代币",
            raw_content="测试原始内容",
            author_id="author_test",
            author_name="测试作者",
            publish_time=datetime.utcnow(),
            crawl_time=datetime.utcnow(),
            source_url="https://test.com/abc",
            like_count=1000,
            comment_count=50
        )
        
        # 测试项目名称提取
        project_name = service._extract_project_name_from_title(content.title)
        assert project_name is not None
        
        # 测试参与度评分计算
        engagement_score = service._calculate_engagement_score(content)
        assert 0.0 <= engagement_score <= 1.0
        
        # 测试关键词匹配
        keyword_matches = service._get_keyword_matches(f"{content.title} {content.content}")
        assert len(keyword_matches) > 0  # 应该匹配到一些关键词
    
    def test_classify_project_category(self):
        """测试项目分类"""
        service = CrawlDataService()
        
        # 测试DeFi分类
        defi_data = {'cleaned_text': '这是一个DeFi去中心化金融项目'}
        category = service._classify_project_category(defi_data)
        assert category == 'DeFi'
        
        # 测试GameFi分类
        gamefi_data = {'cleaned_text': '链游GameFi项目'}
        category = service._classify_project_category(gamefi_data)
        assert category == 'GameFi'
        
        # 测试其他分类
        other_data = {'cleaned_text': '普通项目介绍'}
        category = service._classify_project_category(other_data)
        assert category == 'Other'


class MockXHSPlatform:
    """Mock XHS平台用于测试"""
    
    def __init__(self, config=None):
        self.config = config or {}
    
    def get_platform_name(self):
        return Platform.XHS
    
    async def is_available(self):
        return True
    
    async def crawl(self, keywords, max_count=50, **kwargs):
        # 返回模拟数据
        return [
            RawContent(
                platform=Platform.XHS,
                content_id=f"mock_{i}",
                content_type=ContentType.TEXT,
                title=f"测试标题{i}",
                content=f"包含{keywords[0]}的测试内容{i}",
                raw_content="mock raw content",
                author_id=f"author_{i}",
                author_name=f"作者{i}",
                publish_time=datetime.utcnow(),
                crawl_time=datetime.utcnow(),
                source_url=f"https://test.com/{i}"
            )
            for i in range(min(3, max_count))  # 返回最多3个测试数据
        ]


@pytest.mark.asyncio
async def test_integration_crawl_flow():
    """集成测试：完整的爬取流程"""
    # 注册Mock平台
    PlatformFactory.clear_instances()
    PlatformFactory.register(Platform.XHS, MockXHSPlatform)
    
    # 创建爬虫管理器
    manager = CrawlerManager()
    
    # 提交任务
    task_id = await manager.submit_crawl_task(
        platform=Platform.XHS,
        keywords=["TGE"],
        max_count=5
    )
    
    # 执行任务
    result = await manager.execute_task(task_id)
    
    # 验证结果
    assert result.task_id == task_id
    assert result.platform == Platform.XHS
    assert result.total_count > 0
    assert result.success_count > 0
    assert len(result.contents) > 0
    
    # 验证任务状态
    task = await manager.get_task_status(task_id)
    assert task.status == "completed"