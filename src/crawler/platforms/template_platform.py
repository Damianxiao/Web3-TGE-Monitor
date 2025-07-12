"""
平台扩展模板
展示如何添加新平台的示例代码
"""
from datetime import datetime
from typing import List, Dict, Any
import structlog

from ..base_platform import AbstractPlatform
from ..models import RawContent, Platform, ContentType

logger = structlog.get_logger()


class TemplatePlatform(AbstractPlatform):
    """
    平台模板类
    复制此文件并修改为新平台的实现
    """
    
    def get_platform_name(self) -> Platform:
        """获取平台名称 - 需要修改"""
        # 1. 在models.py的Platform枚举中添加新平台
        # 2. 在这里返回对应的枚举值
        return Platform.XHS  # 替换为新平台
    
    async def is_available(self) -> bool:
        """检查平台是否可用 - 需要实现"""
        try:
            # 在这里添加平台可用性检查逻辑：
            # - 检查必要的依赖是否安装
            # - 检查配置是否正确
            # - 检查网络连接等
            
            self.logger.info("Platform availability check")
            return True  # 替换为实际检查逻辑
            
        except Exception as e:
            self.logger.error("Platform availability check failed", error=str(e))
            return False
    
    async def crawl(
        self, 
        keywords: List[str], 
        max_count: int = 50,
        **kwargs
    ) -> List[RawContent]:
        """爬取内容 - 需要实现"""
        
        # 1. 验证关键词
        validated_keywords = await self.validate_keywords(keywords)
        
        # 2. 执行实际爬取
        raw_data = await self._execute_crawl(validated_keywords, max_count, **kwargs)
        
        # 3. 转换数据格式
        raw_contents = []
        for item in raw_data:
            try:
                content = await self.transform_to_raw_content(item)
                raw_contents.append(content)
            except Exception as e:
                self.logger.warning("Failed to transform content", 
                                  content_id=item.get('id', 'unknown'),
                                  error=str(e))
        
        # 4. 过滤内容
        filtered_contents = await self.filter_content(raw_contents)
        
        self.logger.info("Crawl completed",
                        keywords=validated_keywords,
                        raw_count=len(raw_data),
                        filtered_count=len(filtered_contents))
        
        return filtered_contents
    
    async def _execute_crawl(
        self, 
        keywords: List[str], 
        max_count: int, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """执行实际的爬取逻辑 - 需要实现"""
        
        # 在这里实现具体的爬取逻辑：
        # 1. 构建搜索请求
        # 2. 发送HTTP请求或调用API
        # 3. 解析响应数据
        # 4. 处理分页等
        
        # 示例数据结构
        mock_data = [
            {
                'id': 'example_001',
                'title': '示例标题',
                'content': '示例内容包含Web3相关信息',
                'author_id': 'author_001', 
                'author_name': '示例作者',
                'publish_time': datetime.utcnow().timestamp(),
                'like_count': 100,
                'comment_count': 20,
                'url': 'https://example.com/post/001'
            }
        ]
        
        self.logger.info("Mock crawl executed", 
                        keywords=keywords, 
                        result_count=len(mock_data))
        
        return mock_data
    
    async def transform_to_raw_content(self, platform_data: Dict[str, Any]) -> RawContent:
        """将平台数据转换为统一格式 - 需要实现"""
        
        # 根据平台的数据结构进行转换
        # 确保映射到RawContent的所有必要字段
        
        return RawContent(
            platform=self.get_platform_name(),
            content_id=platform_data.get('id', ''),
            content_type=ContentType.TEXT,  # 根据实际内容类型调整
            title=platform_data.get('title', ''),
            content=platform_data.get('content', ''),
            raw_content=str(platform_data),
            author_id=platform_data.get('author_id', ''),
            author_name=platform_data.get('author_name', ''),
            publish_time=self._parse_timestamp(platform_data.get('publish_time')),
            crawl_time=datetime.utcnow(),
            like_count=platform_data.get('like_count', 0),
            comment_count=platform_data.get('comment_count', 0),
            source_url=platform_data.get('url', ''),
            platform_metadata=platform_data  # 保存原始数据
        )
    
    def _parse_timestamp(self, timestamp_value: Any) -> datetime:
        """解析时间戳 - 根据平台格式调整"""
        if isinstance(timestamp_value, (int, float)):
            if timestamp_value > 10**12:
                return datetime.fromtimestamp(timestamp_value / 1000)
            else:
                return datetime.fromtimestamp(timestamp_value)
        return datetime.utcnow()


# ================================
# 添加新平台的步骤说明
# ================================

"""
如何添加新平台：

1. 在 src/crawler/models.py 中的 Platform 枚举添加新平台：
   ```python
   class Platform(str, Enum):
       XHS = "xhs"
       NEW_PLATFORM = "new_platform"  # 添加这一行
   ```

2. 复制此模板文件为新平台文件：
   ```bash
   cp template_platform.py new_platform.py
   ```

3. 修改新平台文件：
   - 更改类名：TemplatePlatform -> NewPlatform
   - 实现 get_platform_name() 返回正确的枚举值
   - 实现 is_available() 检查平台可用性
   - 实现 _execute_crawl() 具体爬取逻辑
   - 调整 transform_to_raw_content() 数据转换逻辑

4. 在 src/crawler/platform_factory.py 的 auto_register_platforms() 中注册：
   ```python
   def auto_register_platforms():
       try:
           from .platforms.new_platform import NewPlatform
           PlatformFactory.register(Platform.NEW_PLATFORM, NewPlatform)
       except ImportError as e:
           logger.warning("Failed to register new platform", error=str(e))
   ```

5. 在配置文件中添加平台配置（可选）：
   ```python
   # src/config/settings.py
   new_platform_config = {
       'api_key': 'your_api_key',
       'rate_limit': {'requests_per_minute': 30}
   }
   ```

6. 编写测试用例：
   ```python
   # tests/test_new_platform.py
   def test_new_platform_crawl():
       # 测试爬取功能
       pass
   ```

7. 更新文档说明支持的新平台

完成后，新平台就可以通过 PlatformFactory 创建和使用了！
"""