# Web3 TGE Monitor

一个基于MediaCrawler的Web3 TGE（Token Generation Events）数据监控和AI分析API系统。

## 功能特性

- 🕷️ **智能爬虫**: 基于MediaCrawler，支持小红书等社交媒体平台
- 🤖 **AI分析**: 集成第三方AI API，生成精炼的投资建议和风险评估
- 📡 **RESTful API**: 提供完整的API接口，支持按需查询和数据获取
- 🔄 **去重机制**: 智能去重避免重复分析
- 📊 **结构化数据**: 30天历史数据存储，支持多种查询方式

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

### API接口

- **获取最新TGE数据**: `GET /api/v1/tge/latest`
- **按需分析**: `GET /api/v1/tge/analyze?keywords=xxx`
- **健康检查**: `GET /api/v1/health`

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