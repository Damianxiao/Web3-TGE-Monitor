#!/bin/bash

# Web3 TGE Monitor 一键启动脚本

set -e

echo "🚀 启动 Web3 TGE Monitor..."

# 检查是否在正确的目录
if [ ! -f "pyproject.toml" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 检查Python版本
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ 错误: 需要Python 3.9或更高版本，当前版本: $python_version"
    exit 1
fi

# 检查环境配置文件
if [ ! -f ".env" ]; then
    echo "📝 创建环境配置文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，填入必要的配置（特别是AI_API_KEY）"
    echo "   然后重新运行此脚本"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "🔧 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📦 安装依赖包..."
pip install --upgrade pip
pip install -r requirements.txt

# 检查数据库连接
echo "🗄️  检查数据库连接..."
python3 -c "
import os
import sys
sys.path.insert(0, '.')
from src.config.settings import settings
print(f'数据库配置: {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}')
print('数据库连接配置正常')
" || {
    echo "❌ 数据库配置有误，请检查 .env 文件中的数据库配置"
    exit 1
}

# 创建数据库表（如果需要）
echo "🏗️  初始化数据库..."
python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from src.database.database import init_database
asyncio.run(init_database())
print('数据库初始化完成')
" || echo "⚠️  数据库初始化失败，请确保数据库服务正在运行"

# 运行测试
echo "🧪 运行测试..."
python3 -m pytest tests/ -v --tb=short || {
    echo "⚠️  部分测试失败，但服务仍可启动"
}

# 启动API服务
echo "🌐 启动API服务..."
echo "📍 API文档地址: http://localhost:8000/docs"
echo "📍 健康检查: http://localhost:8000/api/v1/health"
echo ""
echo "按 Ctrl+C 停止服务"

python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload