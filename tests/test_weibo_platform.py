"""
微博平台单元测试
按照MULTI_PLATFORM_DEVELOPMENT_PLAN.md第6.2.1节规范
"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime
from src.crawler.platforms.weibo_platform import WeiboPlatform
from src.crawler.models import RawContent, Platform


class TestWeiboPlatform:
    """微博平台测试"""
    
    @pytest.fixture
    def weibo_platform(self):
        """测试用微博平台实例"""
        return WeiboPlatform()
    
    def test_platform_name(self, weibo_platform):
        """测试平台名称"""
        assert weibo_platform.get_platform_name() == Platform.WEIBO
    
    @pytest.mark.asyncio
    async def test_login_functionality(self, weibo_platform):
        """测试登录功能"""
        # Mock MediaCrawler登录
        with patch.object(weibo_platform, '_check_login_status', return_value=True) as mock_login:
            result = await weibo_platform.is_available()
            assert result is True
            mock_login.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_functionality(self, weibo_platform):
        """测试搜索功能"""
        # Mock数据 - 按照文档示例格式
        mock_data = [
            {
                'id': '123456',
                'text': '测试微博内容关于TGE代币发行',
                'user': {'screen_name': '测试用户', 'id': 'user123'},
                'created_at': '2025-07-13T10:00:00',
                'reposts_count': 10,
                'comments_count': 5,
                'attitudes_count': 20,
                'pic_urls': ['http://example.com/pic1.jpg']
            }
        ]
        
        # 模拟搜索
        with patch.object(weibo_platform, '_execute_crawl', return_value=mock_data):
            results = await weibo_platform.crawl(['TGE', 'Web3'])
            
        assert len(results) == 1
        assert isinstance(results[0], RawContent)
        assert results[0].platform == Platform.WEIBO
        assert 'TGE' in results[0].content
    
    def test_data_conversion(self, weibo_platform):
        """测试数据转换 - 按照文档3.1.2节实现细节"""
        weibo_data = {
            'id': '123456',
            'text': '测试转换功能关于Web3项目',
            'user': {'screen_name': '测试用户', 'id': 'user123'},
            'created_at': '2025-07-13T10:00:00',
            'pic_urls': ['http://example.com/pic1.jpg'],
            'reposts_count': 10,
            'comments_count': 5,
            'attitudes_count': 20
        }
        
        result = weibo_platform._convert_to_raw_content(weibo_data)
        
        assert result.content_id == '123456'
        assert result.platform == Platform.WEIBO
        assert result.content == '测试转换功能关于Web3项目'
        assert result.author_name == '测试用户'
        assert len(result.image_urls) == 1
        assert result.like_count == 20
        assert result.comment_count == 5
        assert result.share_count == 10
    
    def test_parse_timestamp(self, weibo_platform):
        """测试时间戳解析"""
        # 测试字符串时间格式
        time_str = '2025-07-13T10:00:00'
        result = weibo_platform._parse_timestamp(time_str)
        assert isinstance(result, datetime)
        
        # 测试Unix时间戳
        timestamp = 1673596800  # 2023-01-13 10:00:00
        result = weibo_platform._parse_timestamp(timestamp)
        assert isinstance(result, datetime)
    
    def test_parse_count(self, weibo_platform):
        """测试数量解析"""
        # 测试整数
        assert weibo_platform._parse_count(100) == 100
        
        # 测试中文数字
        assert weibo_platform._parse_count('1.2万') == 12000
        assert weibo_platform._parse_count('5千') == 5000
        
        # 测试字符串数字
        assert weibo_platform._parse_count('500') == 500
        
        # 测试无效值
        assert weibo_platform._parse_count(None) == 0
        assert weibo_platform._parse_count('') == 0


class TestWeiboIntegration:
    """微博平台集成测试"""
    
    @pytest.mark.asyncio
    async def test_platform_factory_integration(self):
        """测试平台工厂集成"""
        from src.crawler.platform_factory import PlatformFactory
        from src.crawler.models import Platform
        
        # 验证微博平台已注册
        registered_platforms = PlatformFactory.get_registered_platforms()
        assert Platform.WEIBO in registered_platforms
        
        # 验证可以创建微博平台实例
        platform = await PlatformFactory.create_platform(Platform.WEIBO)
        assert isinstance(platform, WeiboPlatform)
        assert platform.get_platform_name() == Platform.WEIBO
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理 - 按照文档4.2节规范"""
        from src.crawler.base_platform import PlatformError
        
        weibo_platform = WeiboPlatform()
        
        # 测试登录失败处理
        with patch.object(weibo_platform, '_check_login_status', return_value=False):
            with pytest.raises(PlatformError):
                await weibo_platform.crawl(['test'])
    
    def test_logging_functionality(self):
        """测试日志功能 - 按照文档4.3节规范"""
        import structlog
        
        weibo_platform = WeiboPlatform()
        
        # 验证logger配置
        assert hasattr(weibo_platform, 'logger')
        # 检查logger是否有structlog的特征方法
        assert hasattr(weibo_platform.logger, 'bind')
        assert hasattr(weibo_platform.logger, 'info')
        assert hasattr(weibo_platform.logger, 'error')
        
        # 验证平台上下文是否正确绑定
        # structlog的logger具有context属性
        if hasattr(weibo_platform.logger, '_context'):
            assert 'platform' in str(weibo_platform.logger._context) or 'weibo' in str(weibo_platform.logger)