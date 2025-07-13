# 工具使用说明

## 📂 目录结构

```
tools/
├── qr_login/          # QR码登录相关工具
├── debug/             # 调试分析工具
└── update_xhs_cookie.sh  # 配置更新工具
```

## 🔧 主要工具

### 1. QR码登录工具 (`tools/qr_login/`)

#### `simple_qr_login.py` ⭐ **推荐使用**
- **功能**: WSL环境下的QR码登录
- **特点**: 简化版，兼容性最好
- **使用**: `python3 tools/qr_login/simple_qr_login.py`
- **说明**: 会在WSL中打开浏览器显示QR码，扫码完成登录

#### `qr_login.py`
- **功能**: 集成MediaCrawler的完整QR码登录
- **使用**: `python3 tools/qr_login/qr_login.py`

#### `qr_monitor.py`
- **功能**: 实时监控QR码文件变化
- **使用**: `python3 tools/qr_login/qr_monitor.py`

### 2. 调试分析工具 (`tools/debug/`)

#### `analyze_search.py` ⭐ **问题诊断**
- **功能**: 深入分析搜索问题，检查API响应结构
- **使用**: `python3 tools/debug/analyze_search.py`
- **输出**: 详细的搜索结果分析报告

#### `debug_login_status.py`
- **功能**: 检查登录状态和Cookie有效性
- **使用**: `python3 tools/debug/debug_login_status.py`

#### `test_search_api.py`
- **功能**: 测试搜索API功能
- **使用**: `python3 tools/debug/test_search_api.py`

### 3. 配置管理工具

#### `update_xhs_cookie.sh`
- **功能**: 交互式Cookie配置管理
- **使用**: `./tools/update_xhs_cookie.sh`
- **功能**: 提供菜单式的配置更新界面

## 🚀 快速使用指南

### 首次设置QR码登录
```bash
# 1. 运行QR码登录工具
python3 tools/qr_login/simple_qr_login.py

# 2. 在浏览器中扫描QR码完成登录

# 3. 测试搜索功能
curl -X POST "http://localhost:8003/api/v1/tge/search" \
     -H "Content-Type: application/json" \
     -d '{"keywords": ["测试"], "max_count": 3}'
```

### 诊断搜索问题
```bash
# 运行搜索分析工具
python3 tools/debug/analyze_search.py
```

### 更新配置
```bash
# 使用交互式配置工具
./tools/update_xhs_cookie.sh
```

## 📋 常见问题

### Q: QR码不显示怎么办？
A: 使用 `simple_qr_login.py`，它兼容性最好

### Q: 搜索返回0内容？
A: 运行 `analyze_search.py` 进行详细诊断

### Q: 如何更新Cookie？
A: 运行 `update_xhs_cookie.sh` 或手动编辑配置文件

## 🛠️ 开发调试

所有调试工具都在 `tools/debug/` 目录下，包含详细的错误分析和API响应检查功能。

## 📝 日志位置

- API服务器日志: `api.log`
- MediaCrawler日志: 控制台输出
- 调试工具日志: 直接输出到控制台