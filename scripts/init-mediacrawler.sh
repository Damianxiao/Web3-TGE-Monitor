#!/bin/bash

# MediaCrawler Submodule 初始化脚本
# 用于自动化初始化和配置MediaCrawler依赖

set -e

echo "=== MediaCrawler Submodule 初始化脚本 ==="
echo ""

# 检查Git是否存在
if ! command -v git &> /dev/null; then
    echo "错误: Git 未安装，请先安装Git"
    exit 1
fi

# 检查是否在项目根目录
if [ ! -f "CLAUDE.md" ]; then
    echo "错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 初始化submodule
echo "1. 初始化 MediaCrawler submodule..."
if [ -d "external/MediaCrawler" ]; then
    echo "   MediaCrawler submodule 已存在，更新中..."
    git submodule update --init --recursive
else
    echo "   添加 MediaCrawler submodule..."
    git submodule add git@github.com:NanmiCoder/MediaCrawler.git external/MediaCrawler
    git submodule update --init --recursive
fi

# 检查submodule状态
echo "2. 检查 submodule 状态..."
git submodule status

# 创建符号链接
echo "3. 创建符号链接..."
if [ ! -L "mediacrawler" ]; then
    ln -sf external/MediaCrawler mediacrawler
    echo "   创建符号链接: mediacrawler -> external/MediaCrawler"
else
    echo "   符号链接已存在"
fi

# 检查环境变量配置
echo "4. 检查环境变量配置..."
if [ -f ".env" ]; then
    if grep -q "MEDIACRAWLER_PATH" .env; then
        echo "   .env 文件中已存在 MEDIACRAWLER_PATH 配置"
    else
        echo "   在 .env 文件中添加 MEDIACRAWLER_PATH 配置..."
        echo "MEDIACRAWLER_PATH=./external/MediaCrawler" >> .env
    fi
else
    echo "   .env 文件不存在，请先复制 .env.example 到 .env"
    echo "   运行: cp .env.example .env"
fi

# 验证MediaCrawler依赖
echo "5. 验证 MediaCrawler 依赖..."
if [ -f "external/MediaCrawler/package.json" ]; then
    echo "   MediaCrawler 依赖验证成功"
else
    echo "   警告: MediaCrawler 结构异常，请检查submodule状态"
fi

echo ""
echo "=== 初始化完成 ==="
echo "MediaCrawler submodule 已成功配置"
echo ""
echo "下一步："
echo "1. 确保 .env 文件配置正确"
echo "2. 运行 ./start.sh 启动服务"
echo "3. 或者运行 python3 -m pytest tests/ 进行测试"