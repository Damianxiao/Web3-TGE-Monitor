# XHS平台适配器API文档

## 概述

XHS平台适配器是Web3-TGE-Monitor项目中用于小红书内容爬取的核心组件。本文档详细描述了XHS平台适配器在共享库集成模式下的API接口和使用方法。

## 类定义

### XHSPlatform

继承自 `AbstractPlatform`，实现小红书平台的内容爬取功能。

```python
class XHSPlatform(AbstractPlatform):
    """小红书平台实现 - 共享库版本"""
```

## 构造函数

### `__init__(config: Dict[str, Any] = None)`

创建XHS平台适配器实例。

**参数**:
- `config` (Dict[str, Any], 可选): 平台配置字典

**配置参数**:
- `mediacrawler_path` (str): MediaCrawler项目路径

**示例**:
```python
# 使用默认配置
platform = XHSPlatform()

# 指定MediaCrawler路径
platform = XHSPlatform({
    'mediacrawler_path': '/custom/path/to/MediaCrawler'
})
```

**异常**:
- `PlatformError`: 当指定的MediaCrawler路径无效时抛出

## 公共方法

### `get_platform_name() -> Platform`

获取平台名称标识。

**返回值**:
- `Platform.XHS`: 小红书平台枚举值

**示例**:
```python
platform = XHSPlatform()
name = platform.get_platform_name()
print(name)  # Platform.XHS
```

### `async is_available() -> bool`

检查平台是否可用，包括MediaCrawler安装验证和模块导入测试。

**返回值**:
- `bool`: 平台是否可用

**示例**:
```python
platform = XHSPlatform()
if await platform.is_available():
    print("XHS平台可用")
else:
    print("XHS平台不可用")
```

### `async validate_keywords(keywords: List[str]) -> List[str]`

验证并过滤关键词列表。

**参数**:
- `keywords` (List[str]): 原始关键词列表

**返回值**:
- `List[str]`: 验证后的关键词列表

**示例**:
```python
platform = XHSPlatform()
keywords = ["Web3", "", "DeFi", None, "区块链"]
validated = await platform.validate_keywords(keywords)
print(validated)  # ["Web3", "DeFi", "区块链"]
```

### `async crawl(keywords: List[str], max_count: int = 50, **kwargs) -> List[RawContent]`

执行小红书内容爬取的主要方法。

**参数**:
- `keywords` (List[str]): 搜索关键词列表
- `max_count` (int, 默认50): 最大爬取数量
- `**kwargs`: 其他扩展参数

**返回值**:
- `List[RawContent]`: 爬取到的内容列表

**示例**:
```python
platform = XHSPlatform()
results = await platform.crawl(
    keywords=["Web3", "DeFi"],
    max_count=100
)

for content in results:
    print(f"标题: {content.title}")
    print(f"作者: {content.author_name}")
    print(f"点赞数: {content.like_count}")
```

**异常**:
- `PlatformError`: 爬取过程中发生错误时抛出

### `async transform_to_raw_content(xhs_data: Dict[str, Any]) -> RawContent`

将小红书原始数据转换为标准化的RawContent对象。

**参数**:
- `xhs_data` (Dict[str, Any]): 小红书原始数据字典

**返回值**:
- `RawContent`: 标准化的内容对象

**原始数据格式**:
```python
xhs_data = {
    'note_id': str,           # 笔记ID
    'title': str,             # 标题
    'desc': str,              # 描述内容
    'type': str,              # 内容类型 (text/video)
    'time': int,              # 发布时间戳
    'user_id': str,           # 用户ID
    'nickname': str,          # 用户昵称
    'avatar': str,            # 用户头像URL
    'liked_count': str/int,   # 点赞数 (支持中文格式如"1.2万")
    'comment_count': str/int, # 评论数
    'share_count': str/int,   # 分享数
    'collected_count': str/int, # 收藏数
    'note_url': str,          # 笔记URL
    'ip_location': str,       # IP归属地
    'source_keyword': str,    # 来源关键词
    'image_list': List[str],  # 图片URL列表
    'video_url': str,         # 视频URL
    'tag_list': str/List[str] # 标签列表
}
```

**示例**:
```python
platform = XHSPlatform()
xhs_data = {
    'note_id': 'abc123',
    'title': 'Web3项目分析',
    'desc': '详细分析最新的DeFi项目',
    'liked_count': '1.2万',
    'comment_count': '500'
}

raw_content = await platform.transform_to_raw_content(xhs_data)
print(raw_content.like_count)  # 12000
```

**异常**:
- `PlatformError`: 数据转换失败时抛出

### `async filter_content(contents: List[RawContent]) -> List[RawContent]`

过滤内容列表，移除不符合条件的内容。

**参数**:
- `contents` (List[RawContent]): 原始内容列表

**返回值**:
- `List[RawContent]`: 过滤后的内容列表

**过滤规则**:
- 移除空标题或空内容的项目
- 移除重复的内容
- 应用平台特定的质量过滤

**示例**:
```python
platform = XHSPlatform()
filtered_contents = await platform.filter_content(raw_contents)
```

## 私有方法

### `async _get_xhs_client()`

获取XHS爬虫客户端实例，支持延迟初始化。

**返回值**:
- `XiaoHongShuCrawler`: MediaCrawler的XHS爬虫实例

### `async _search_notes_with_client(crawler, keywords: List[str], max_count: int) -> List[Dict[str, Any]]`

使用XHS爬虫客户端搜索笔记内容。

**参数**:
- `crawler`: XHS爬虫实例
- `keywords` (List[str]): 关键词列表
- `max_count` (int): 最大数量

**返回值**:
- `List[Dict[str, Any]]`: 原始笔记数据列表

### `_validate_mediacrawler_path(path) -> bool`

验证MediaCrawler路径是否有效。

**参数**:
- `path`: 要验证的路径

**返回值**:
- `bool`: 路径是否有效

### `_ensure_mediacrawler_in_path()`

确保MediaCrawler路径在Python模块搜索路径中。

## 数据模型

### RawContent

爬取内容的标准化数据模型。

```python
@dataclass
class RawContent:
    platform: Platform              # 平台标识
    content_id: str                 # 内容ID
    content_type: ContentType       # 内容类型
    title: str                      # 标题
    content: str                    # 内容
    raw_content: str               # 原始JSON数据
    author_id: str                 # 作者ID
    author_name: str               # 作者名称
    author_avatar: str             # 作者头像
    publish_time: datetime         # 发布时间
    crawl_time: datetime           # 爬取时间
    last_update_time: datetime     # 最后更新时间
    like_count: int                # 点赞数
    comment_count: int             # 评论数
    share_count: int               # 分享数
    collect_count: int             # 收藏数
    image_urls: List[str]          # 图片URL列表
    video_urls: List[str]          # 视频URL列表
    tags: List[str]                # 标签列表
    source_url: str                # 来源URL
    ip_location: str               # IP归属地
    platform_metadata: Dict[str, Any]  # 平台特定元数据
    source_keywords: List[str]     # 来源关键词
```

## 配置管理

### MediaCrawlerConfig

MediaCrawler配置管理器，负责路径解析和验证。

```python
from src.config.mediacrawler_config import MediaCrawlerConfig

# 创建配置管理器
mc_config = MediaCrawlerConfig(settings)

# 获取MediaCrawler路径
path = mc_config.mediacrawler_path

# 获取平台配置
config = mc_config.get_platform_config("xhs")

# 验证安装
is_valid = mc_config.validate_installation()
```

### 配置优先级

1. 环境变量 `MEDIACRAWLER_PATH`
2. Settings配置文件中的 `mediacrawler_path`
3. 相对路径自动发现
4. 默认路径fallback

## 错误处理

### PlatformError

平台特定的错误类型。

```python
class PlatformError(Exception):
    def __init__(self, platform: str, message: str):
        self.platform = platform
        self.message = message
        super().__init__(f"[{platform}] {message}")
```

### 常见错误

1. **MediaCrawler路径无效**:
   ```
   PlatformError: [xhs] 指定的MediaCrawler路径无效: /invalid/path
   ```

2. **爬取失败**:
   ```
   PlatformError: [xhs] Crawl failed: Network timeout
   ```

3. **数据转换失败**:
   ```
   PlatformError: [xhs] Failed to transform XHS data: Missing required field
   ```

## 使用示例

### 基本爬取示例

```python
import asyncio
from src.crawler.platforms.xhs_platform import XHSPlatform

async def main():
    # 创建平台实例
    platform = XHSPlatform()
    
    # 检查可用性
    if not await platform.is_available():
        print("XHS平台不可用")
        return
    
    # 执行爬取
    try:
        results = await platform.crawl(
            keywords=["Web3", "DeFi", "区块链"],
            max_count=50
        )
        
        print(f"成功爬取 {len(results)} 条内容")
        
        for content in results:
            print(f"标题: {content.title}")
            print(f"作者: {content.author_name}")
            print(f"点赞: {content.like_count}")
            print("-" * 50)
            
    except Exception as e:
        print(f"爬取失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 自定义配置示例

```python
import os
from src.crawler.platforms.xhs_platform import XHSPlatform

# 方法1: 通过配置参数
config = {
    'mediacrawler_path': '/custom/path/to/MediaCrawler'
}
platform = XHSPlatform(config)

# 方法2: 通过环境变量
os.environ['MEDIACRAWLER_PATH'] = '/custom/path/to/MediaCrawler'
platform = XHSPlatform()
```

### 数据处理示例

```python
async def process_xhs_data():
    platform = XHSPlatform()
    
    # 模拟原始数据
    xhs_data = {
        'note_id': 'test123',
        'title': 'DeFi项目分析',
        'desc': '深度分析最新的去中心化金融项目',
        'liked_count': '2.5万',  # 中文格式
        'comment_count': '1500',
        'time': 1700000000000    # 毫秒时间戳
    }
    
    # 转换数据
    raw_content = await platform.transform_to_raw_content(xhs_data)
    
    # 输出转换结果
    print(f"内容ID: {raw_content.content_id}")
    print(f"点赞数: {raw_content.like_count}")  # 25000
    print(f"发布时间: {raw_content.publish_time}")
```

## 性能考虑

### 资源管理

- 爬虫客户端采用延迟初始化
- 自动浏览器资源清理
- 支持实例复用

### 并发控制

- 内置并发限制机制
- 智能资源调度
- 避免资源争用

### 内存优化

- 流式数据处理
- 及时释放大对象
- 避免内存泄漏

## 最佳实践

1. **错误处理**: 总是使用try-catch包装爬取操作
2. **资源管理**: 确保在finally块中清理资源
3. **配置管理**: 使用环境变量进行生产环境配置
4. **性能监控**: 监控爬取速度和成功率
5. **日志记录**: 启用详细日志以便故障排除

---

*API文档版本: v1.0*  
*更新时间: 2025-07-12*