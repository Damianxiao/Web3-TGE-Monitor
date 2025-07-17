# Web3 TGE Monitor

一个基于MediaCrawler的Web3 TGE（Token Generation Events）数据监控和AI分析API系统。

## 功能特性

- 🕷️ **多平台爬虫**: 支持小红书、微博、知乎、抖音、B站、快手、百度贴吧等7大平台
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
# 1. 克隆项目
git clone <项目地址>
cd Web3-TGE-Monitor

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置

# 3. 一键启动
chmod +x start.sh
./start.sh
```

### MediaCrawler依赖说明

本项目已将MediaCrawler完全集成到代码库中，无需额外配置：

- **集成方式**: MediaCrawler已直接包含在项目中
- **路径配置**: 在`.env`文件中设置`MEDIACRAWLER_PATH=./external/MediaCrawler`
- **配置文件**: 已针对Web3 TGE监控优化配置

## API 集成指南

### 基础信息
- **API Base URL**: `http://localhost:8000/api/v1` (默认端口)
- **文档地址**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/v1/system/health`

### 支持的平台
- 小红书 (xhs)、微博 (weibo)、知乎 (zhihu)、抖音 (douyin)、哔哩哔哩 (bilibili)、快手 (kuaishou)、百度贴吧 (tieba)

### 🚀 核心API接口

#### 1. 同步批次爬虫任务 (推荐)
**适用场景**: 需要立即获取完整结果，不希望处理异步轮询

**请求**:
```bash
curl -X POST "http://localhost:8000/api/v1/crawler/batch/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "platforms": ["xhs", "zhihu", "weibo", "douyin", "bilibili", "kuaishou", "tieba"],
    "keywords": ["Web3", "TGE", "代币发行"],
    "max_count": 10
  }'
```

**响应**:
```json
{
  "success": true,
  "message": "同步批次爬虫任务完成，批次ID: 35e7e579-b19c-48a5-99e9-5c97dd2c1cd5",
  "data": {
    "batch_id": "35e7e579-b19c-48a5-99e9-5c97dd2c1cd5",
    "overall_status": "completed",
    "total_tasks": 7,
    "completed_tasks": 7,
    "failed_tasks": 0,
    "overall_progress": 100,
    "platform_status": {
      "xhs": {"status": "completed", "content_count": 10},
      "zhihu": {"status": "completed", "content_count": 9},
      "weibo": {"status": "completed", "content_count": 0},
      "douyin": {"status": "completed", "content_count": 1},
      "bilibili": {"status": "completed", "content_count": 5},
      "kuaishou": {"status": "completed", "content_count": 4},
      "tieba": {"status": "completed", "content_count": 0}
    },
    "ai_analysis_status": "completed",
    "total_content_found": 29,
    "ai_summary": "批次爬虫总结: 成功爬取29条内容，覆盖7个平台"
  }
}
```

#### 2. 系统健康检查
**请求**:
```bash
curl -X GET "http://localhost:8000/api/v1/system/health"
```

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-17T12:00:00Z",
  "version": "1.0.0",
  "database": "connected",
  "platforms": {
    "registered": 7,
    "available": 7
  }
}
```

#### 3. 获取项目数据
**请求**:
```bash
curl -X GET "http://localhost:8000/api/v1/projects?page=1&size=20&sort_by=crawl_time&sort_order=desc"
```

**响应**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "token_name": "DeFi Token",
        "token_symbol": "DFT",
        "ai_summary": "创新DeFi项目，具有独特的治理机制",
        "sentiment": "看涨",
        "recommendation": "关注",
        "risk_level": "中",
        "confidence_score": 0.85,
        "source_platform": "xhs",
        "crawl_time": "2025-01-17T12:00:00Z"
      }
    ],
    "total": 156,
    "page": 1,
    "size": 20,
    "pages": 8
  }
}
```

#### 4. AI分析处理
**请求**:
```bash
curl -X POST "http://localhost:8000/api/v1/ai/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Web3项目ABC即将进行TGE，预计发行1000万代币",
    "platform": "xhs",
    "enable_token_extraction": true
  }'
```

**响应**:
```json
{
  "success": true,
  "data": {
    "ai_summary": "Web3项目ABC计划进行代币发行",
    "sentiment": "中性",
    "recommendation": "关注",
    "risk_level": "中",
    "confidence_score": 0.75,
    "token_name": "ABC",
    "token_symbol": "ABC",
    "tge_date": null,
    "analysis_time": "2025-01-17T12:00:00Z"
  }
}
```

### 🔍 常用查询接口

#### 获取最近爬取的数据
```bash
curl -X GET "http://localhost:8000/api/v1/projects/recent?limit=10&hours=24"
```

#### 按平台筛选项目
```bash
curl -X GET "http://localhost:8000/api/v1/projects?platform=xhs&sentiment=看涨&limit=20"
```

#### 获取单个项目详情
```bash
curl -X GET "http://localhost:8000/api/v1/projects/123"
```

#### 搜索项目
```bash
curl -X GET "http://localhost:8000/api/v1/projects/search?query=DeFi&limit=20"
```

### 🛠️ 管理接口

#### 获取爬虫日志
```bash
curl -X GET "http://localhost:8000/api/v1/system/crawler/logs?limit=50"
```

#### 获取AI处理日志
```bash
curl -X GET "http://localhost:8000/api/v1/system/ai/logs?limit=50"
```

#### 数据库清理
```bash
curl -X POST "http://localhost:8000/api/v1/system/cleanup" \
  -H "Content-Type: application/json" \
  -d '{"days": 30}'
```

### ⚙️ 最佳实践

#### 接口选择建议
- **快速测试**: 使用 `health` 检查系统状态
- **批量爬取**: 使用 `batch/sync` 一次性获取多平台数据
- **数据查询**: 使用 `projects` 接口获取历史数据
- **实时分析**: 使用 `ai/analyze` 接口分析单条内容

#### 参数设置建议
- `max_count`: 建议设置为5-50之间，避免请求超时
- `platforms`: 根据需要选择平台，全选时处理时间较长
- `keywords`: 支持多关键词，用逗号分隔

#### 错误处理
- **超时处理**: 同步接口建议设置2-5分钟超时
- **重试机制**: 网络错误可重试，业务错误不建议重试
- **限流控制**: 建议单个客户端每分钟不超过30次请求

### 📊 响应状态码

- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `429`: 请求过于频繁
- `500`: 服务器内部错误

### 🔧 启动API服务

```bash
# 使用虚拟环境启动
source venv/bin/activate
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# 或者指定其他端口
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8003 --reload
```

### 📋 API测试清单

**基础测试**:
```bash
# 1. 检查系统健康状态
curl -X GET "http://localhost:8000/api/v1/system/health"

# 2. 测试单平台爬取
curl -X POST "http://localhost:8000/api/v1/crawler/batch/sync" \
  -H "Content-Type: application/json" \
  -d '{"platforms": ["xhs"], "keywords": ["Web3"], "max_count": 5}'

# 3. 测试全平台爬取
curl -X POST "http://localhost:8000/api/v1/crawler/batch/sync" \
  -H "Content-Type: application/json" \
  -d '{"platforms": ["xhs", "zhihu", "weibo", "douyin", "bilibili", "kuaishou", "tieba"], "keywords": ["Web3"], "max_count": 5}'

# 4. 查看最近数据
curl -X GET "http://localhost:8000/api/v1/projects/recent?limit=10"
```

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
│   └── MediaCrawler/       # MediaCrawler完整集成 (已包含)
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