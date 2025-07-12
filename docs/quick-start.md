# MediaCrawler共享库集成 - 快速开始指南

## 概述

本指南帮助开发者快速上手使用Web3-TGE-Monitor项目中的MediaCrawler共享库集成功能。

## 环境要求

### 系统要求
- Python 3.8+
- Linux/macOS/Windows
- 8GB+ RAM (推荐)
- 稳定的网络连接

### 依赖安装

1. **克隆项目**:
   ```bash
   git clone https://github.com/your-org/Web3-TGE-Monitor.git
   cd Web3-TGE-Monitor
   ```

2. **安装Python依赖**:
   ```bash
   pip install -r requirements.txt
   ```

3. **安装MediaCrawler依赖**:
   ```bash
   # MediaCrawler特定依赖
   pip install playwright Pillow opencv-python requests parsel pyexecjs pandas wordcloud matplotlib jieba
   
   # 安装浏览器
   playwright install chromium
   ```

## MediaCrawler设置

### 获取MediaCrawler

1. **克隆MediaCrawler项目**:
   ```bash
   cd ..  # 回到上级目录
   git clone https://github.com/NanmiCoder/MediaCrawler.git
   ```

2. **验证目录结构**:
   ```
   your-workspace/
   ├── Web3-TGE-Monitor/
   └── MediaCrawler/
   ```

### 配置MediaCrawler路径

有三种方式配置MediaCrawler路径：

#### 方法1: 环境变量 (推荐)
```bash
export MEDIACRAWLER_PATH="/path/to/MediaCrawler"
```

#### 方法2: 配置文件
编辑 `src/config/settings.py`:
```python
class Settings(BaseSettings):
    mediacrawler_path: str = "/absolute/path/to/MediaCrawler"
```

#### 方法3: 代码配置
```python
from src.crawler.platforms.xhs_platform import XHSPlatform

config = {'mediacrawler_path': '/path/to/MediaCrawler'}
platform = XHSPlatform(config)
```

## 快速验证

### 1. 运行导入测试
```bash
cd Web3-TGE-Monitor
python3 test_mediacrawler_import.py
```

期望输出:
```
开始测试MediaCrawler模块导入...
✅ XHS client模块导入成功
✅ XHS core模块导入成功
✅ 基础爬虫类导入成功
✅ XHS数据模型导入成功
✅ 配置模块导入成功

成功率: 5/5 (100.0%)
🎉 所有模块导入成功！可以进行下一步。
```

### 2. 运行集成测试
```bash
python3 integration_test_suite.py
```

期望输出:
```
🚀 Step 5: MediaCrawler共享库集成测试
======================================================================
✅ 配置管理测试: 通过
✅ 模块导入测试: 通过
✅ 平台初始化测试: 通过
...
成功率: 100.0%
🎉 Step 5 完成！集成测试通过
```

### 3. 运行端到端测试
```bash
python3 end_to_end_test.py
```

## 基本使用

### 创建平台实例

```python
import asyncio
from src.crawler.platforms.xhs_platform import XHSPlatform

async def main():
    # 创建XHS平台实例
    platform = XHSPlatform()
    
    # 检查平台可用性
    if await platform.is_available():
        print("✅ XHS平台可用")
    else:
        print("❌ XHS平台不可用")

asyncio.run(main())
```

### 执行内容爬取

```python
import asyncio
from src.crawler.platforms.xhs_platform import XHSPlatform

async def crawl_example():
    platform = XHSPlatform()
    
    try:
        # 执行爬取
        results = await platform.crawl(
            keywords=["Web3", "DeFi"],
            max_count=20
        )
        
        print(f"成功爬取 {len(results)} 条内容")
        
        # 处理结果
        for content in results:
            print(f"标题: {content.title}")
            print(f"作者: {content.author_name}")
            print(f"点赞: {content.like_count}")
            print("-" * 50)
            
    except Exception as e:
        print(f"爬取失败: {e}")

asyncio.run(crawl_example())
```

## 配置选项

### 基本配置

在 `src/config/settings.py` 中配置:

```python
class Settings(BaseSettings):
    # MediaCrawler配置
    mediacrawler_path: str = "../MediaCrawler"
    mediacrawler_enable_proxy: bool = False
    mediacrawler_headless: bool = True
    mediacrawler_save_data: bool = True
    
    # 爬虫配置
    crawler_max_pages: int = 5
    crawler_delay_seconds: int = 3
    
    # Web3关键词
    web3_keywords: str = "TGE,代币发行,空投,IDO,新币上线,DeFi,Web3项目"
```

### 环境变量配置

创建 `.env` 文件:
```bash
# MediaCrawler配置
MEDIACRAWLER_PATH=/path/to/MediaCrawler
MEDIACRAWLER_ENABLE_PROXY=false
MEDIACRAWLER_HEADLESS=true

# 应用配置
LOG_LEVEL=INFO
APP_DEBUG=false
```

## 故障排除

### 常见问题

#### 1. "MediaCrawler not found" 错误

**问题**: 找不到MediaCrawler路径
**解决方案**:
```bash
# 检查MediaCrawler是否存在
ls -la /path/to/MediaCrawler

# 设置正确的环境变量
export MEDIACRAWLER_PATH="/correct/path/to/MediaCrawler"

# 验证路径
python3 -c "
import sys
sys.path.insert(0, '/path/to/MediaCrawler')
import media_platform.xhs.core
print('MediaCrawler路径正确')
"
```

#### 2. 模块导入失败

**问题**: 无法导入MediaCrawler模块
**解决方案**:
```bash
# 安装缺失的依赖
pip install playwright Pillow opencv-python requests parsel pyexecjs

# 安装浏览器
playwright install chromium

# 检查Python路径
python3 -c "import sys; print(sys.path)"
```

#### 3. 浏览器启动失败

**问题**: Playwright浏览器无法启动
**解决方案**:
```bash
# 重新安装浏览器
playwright install --force chromium

# 检查系统依赖
sudo apt-get install -y libxss1 libgconf-2-4 libxrandr2 libasound2 libpangocairo-1.0-0 libatk1.0-0 libcairo-gobject2 libgtk-3-0 libgdk-pixbuf2.0-0

# 测试浏览器
python3 -c "
from playwright.async_api import async_playwright
import asyncio

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        print('浏览器启动成功')
        await browser.close()

asyncio.run(test())
"
```

### 调试技巧

1. **启用详细日志**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **检查配置**:
   ```python
   from src.config.mediacrawler_config import MediaCrawlerConfig
   from src.config.settings import settings
   
   mc_config = MediaCrawlerConfig(settings)
   print(f"MediaCrawler路径: {mc_config.mediacrawler_path}")
   print(f"安装验证: {mc_config.validate_installation()}")
   ```

3. **分步测试**:
   ```bash
   # 测试配置
   python3 verify_step4_completion.py
   
   # 测试集成
   python3 integration_test_suite.py
   
   # 测试端到端
   python3 end_to_end_test.py
   ```

## 性能优化

### 建议配置

1. **开发环境**:
   ```python
   mediacrawler_headless = False  # 显示浏览器，便于调试
   crawler_delay_seconds = 5      # 较长延迟，避免被限制
   ```

2. **生产环境**:
   ```python
   mediacrawler_headless = True   # 无头模式，节省资源
   crawler_delay_seconds = 2      # 较短延迟，提高效率
   mediacrawler_enable_proxy = True  # 启用代理，避免IP限制
   ```

### 监控指标

```python
import time
from src.crawler.platforms.xhs_platform import XHSPlatform

async def benchmark():
    platform = XHSPlatform()
    
    start_time = time.time()
    results = await platform.crawl(keywords=["Web3"], max_count=10)
    end_time = time.time()
    
    print(f"爬取耗时: {end_time - start_time:.2f}秒")
    print(f"成功率: {len(results)}/10")
    print(f"平均速度: {len(results)/(end_time - start_time):.2f} 条/秒")
```

## 部署指南

### Docker部署

1. **创建Dockerfile**:
   ```dockerfile
   FROM python:3.9-slim
   
   # 安装系统依赖
   RUN apt-get update && apt-get install -y \
       chromium \
       && rm -rf /var/lib/apt/lists/*
   
   # 设置工作目录
   WORKDIR /app
   
   # 复制项目文件
   COPY . .
   COPY MediaCrawler/ ./MediaCrawler/
   
   # 安装Python依赖
   RUN pip install -r requirements.txt
   RUN playwright install chromium
   
   # 设置环境变量
   ENV MEDIACRAWLER_PATH=/app/MediaCrawler
   ENV MEDIACRAWLER_HEADLESS=true
   
   # 启动应用
   CMD ["python", "main.py"]
   ```

2. **构建和运行**:
   ```bash
   docker build -t web3-tge-monitor .
   docker run -d --name tge-monitor web3-tge-monitor
   ```

### 云服务部署

**环境变量设置**:
```bash
MEDIACRAWLER_PATH=/opt/MediaCrawler
MEDIACRAWLER_HEADLESS=true
MEDIACRAWLER_ENABLE_PROXY=true
LOG_LEVEL=INFO
```

## 下一步

1. **阅读完整文档**: 查看 `docs/mediacrawler-integration.md`
2. **API参考**: 查看 `docs/xhs-platform-api.md`
3. **扩展到其他平台**: 复用集成模式支持更多平台
4. **性能优化**: 根据实际使用情况调整配置

## 获取帮助

- **问题反馈**: 在项目Issue中报告问题
- **技术讨论**: 参与项目Discussion
- **代码贡献**: 提交Pull Request

---

*快速开始指南版本: v1.0*  
*更新时间: 2025-07-12*