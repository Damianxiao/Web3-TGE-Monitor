# Web3 TGE Monitor

一个基于MediaCrawler的Web3 TGE（Token Generation Events）数据监控和AI分析API系统。

## 功能特性

- 🕷️ **多平台爬虫**: 支持小红书、微博、抖音、B站、快手、百度贴吧等6大平台
- 🤖 **AI分析**: 集成第三方AI API，生成精炼的投资建议和风险评估
- 📡 **RESTful API**: 提供完整的API接口，支持同步/异步、实时搜索等多种调用方式
- 🔄 **智能去重**: 基于内容哈希的去重机制，避免重复分析
- 📊 **结构化数据**: 30天历史数据存储，支持多种查询方式
- ⚡ **高性能**: 异步批量处理，支持并发爬取和AI分析

## 快速开始

### 环境要求

- Python 3.9+
- MySQL 5.7+
- Node.js 16+ (MediaCrawler依赖)

### 一键启动

```bash
# 1. 克隆项目（包含submodule）
git clone --recurse-submodules <项目地址>
cd Web3-TGE-Monitor

# 如果已经克隆但未初始化submodule，运行：
# git submodule update --init --recursive

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置

# 3. 一键启动
chmod +x start.sh
./start.sh
```

### MediaCrawler依赖说明

本项目依赖MediaCrawler进行社交媒体数据采集。我们使用Git submodule管理这个依赖：

- **推荐方式**: 使用Git submodule（已自动配置）
- **路径配置**: 在`.env`文件中设置`MEDIACRAWLER_PATH=./external/MediaCrawler`
- **手动管理**: 如果您有独立的MediaCrawler安装，可以设置自定义路径

## API 集成指南

### 基础信息
- **API Base URL**: `http://localhost:9527/api/v1`
- **文档地址**: `http://localhost:9527/docs`
- **Health Check**: `http://localhost:9527/api/v1/system/health`

### 支持的平台
- 小红书 (xhs)、微博 (weibo)、抖音 (douyin)、哔哩哔哩 (bilibili)、快手 (kuaishou)、百度贴吧 (tieba)

### 🚀 核心API接口

#### 1. 同步批次爬虫任务 (推荐)
**适用场景**: 需要立即获取完整结果，不希望处理异步轮询

**请求**:
```http
POST /api/v1/crawler/batch/sync
Content-Type: application/json

{
    "keywords": ["Web3", "TGE", "代币发行"],
    "platforms": ["xhs", "weibo", "douyin"],
    "max_count_per_platform": 10,
    "enable_ai_analysis": true
}
```

**响应**:
```json
{
    "success": true,
    "data": {
        "batch_id": "batch_20250716_001",
        "overall_status": "completed",
        "total_tasks": 3,
        "completed_tasks": 3,
        "failed_tasks": 0,
        "overall_progress": 100,
        "platform_status": {
            "xhs": {"status": "completed", "count": 8},
            "weibo": {"status": "completed", "count": 12}
        },
        "ai_analysis_status": "completed",
        "total_content_found": 26,
        "ai_summary": {
            "total_projects": 26,
            "processed_projects": 26,
            "top_projects": [...]
        }
    },
    "message": "同步批次爬虫任务完成"
}
```

#### 2. 实时TGE搜索 (推荐)
**适用场景**: 快速搜索，智能缓存，减少重复爬取

**请求**:
```http
GET /api/v1/search/realtime?keywords=Web3,TGE&platforms=xhs,weibo,douyin&max_count=20&enable_crawl=true&cache_hours=2
```

**响应**:
```json
{
    "success": true,
    "data": {
        "analysis_results": [
            {
                "token_name": "DeFi Token",
                "token_symbol": "DFT",
                "ai_summary": "新兴DeFi项目，具有创新的流动性挖矿机制",
                "sentiment": "看涨",
                "recommendation": "关注",
                "risk_level": "中",
                "confidence_score": 0.85,
                "tge_date": "2025-01-15",
                "source_platform": "xhs",
                "source_count": 1
            }
        ],
        "search_summary": {
            "total_results": 18,
            "cached_results": 12,
            "crawled_results": 6,
            "execution_time": 15.2
        }
    }
}
```

#### 3. 批次结果聚合
**适用场景**: 获取已完成批次的详细聚合分析

**请求**:
```http
GET /api/v1/crawler/batch/{batch_id}/results?include_raw_data=false&limit_per_platform=50
```

**响应**:
```json
{
    "success": true,
    "data": {
        "batch_id": "batch_20250716_001",
        "platform_results": {
            "xhs": {
                "total_count": 10,
                "success_count": 8,
                "duplicate_count": 2,
                "error_count": 0
            }
        },
        "aggregated_stats": {
            "total_count": 30,
            "success_count": 26,
            "platforms_count": 3
        },
        "ai_analysis_summary": {
            "total_projects": 26,
            "investment_recommendations": {"关注": 15, "谨慎": 8, "回避": 3},
            "risk_levels": {"高": 3, "中": 18, "低": 5},
            "top_projects": [...]
        }
    }
}
```

### 🔍 数据查询接口

#### 项目列表查询
```http
GET /api/v1/projects?page=1&size=20&category=DEFI&risk_level=MEDIUM&sort_by=overall_score&sort_order=desc
```

#### 项目详情查询
```http
GET /api/v1/projects/{project_id}
```

#### 项目搜索
```http
GET /api/v1/projects/search?query=DeFi&page=1&size=20&category=DEFI
```

#### 获取最近分析结果
```http
GET /api/v1/search/recent?limit=20&hours=24
```

### ⚙️ 最佳实践

#### 接口选择建议
- **快速获取结果**: 使用 `realtime_search`
- **完整数据分析**: 使用 `sync_batch_crawl`
- **历史数据查询**: 使用 `projects` 接口

#### 参数设置建议
- `max_count`: 根据需求设置，避免过大
- `cache_hours`: 根据数据新鲜度要求设置
- `platforms`: 只选择需要的平台

#### 安全注意事项
- **请求频率限制**: 建议单个客户端每分钟不超过60次请求
- **超时设置**: 同步接口建议设置5分钟超时
- **错误重试**: 网络错误建议指数退避重试

## 项目结构

```
Web3-TGE-Monitor/
├── src/                     # 源代码
│   ├── config/             # 配置管理
│   ├── crawler/            # 爬虫模块
│   ├── ai_processor/       # AI处理模块
│   ├── api/                # API服务
│   ├── database/           # 数据库模块
│   └── utils/              # 工具模块
├── external/               # 外部依赖
│   └── MediaCrawler/       # MediaCrawler submodule
├── tests/                  # 测试代码
├── data/                   # 数据存储
└── docs/                   # 文档
```

## 开发模式

本项目采用TDD（测试驱动开发）模式，每个功能模块都有完整的测试覆盖。

## 技术栈

- **后端框架**: FastAPI
- **爬虫引擎**: MediaCrawler + Playwright
- **数据库**: MySQL + SQLAlchemy
- **AI处理**: 第三方AI API (gpt.ge)
- **容器化**: Docker
- **测试框架**: pytest

## 许可证

本项目仅供学习研究使用，请遵守相关法律法规和平台使用条款。

---

**⚠️ 免责声明**: 本工具仅用于技术学习和研究，不构成任何投资建议。使用者需自行承担投资风险。