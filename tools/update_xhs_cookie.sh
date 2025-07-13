#!/bin/bash

# XHS Cookie更新脚本 - WSL环境适配版本
# 用于在WSL环境下更新小红书Cookie配置

set -e

# 配置文件路径
CONFIG_FILE="mediacrawler/config/base_config.py"
ENV_FILE=".env"

echo "🔧 XHS Cookie更新脚本 - WSL版本"
echo "=================================="

# 检查WSL环境
if grep -qi microsoft /proc/version 2>/dev/null || [ -n "$WSL_DISTRO_NAME" ]; then
    echo "✅ WSL环境检测成功"
else
    echo "⚠️  未检测到WSL环境，但脚本仍可使用"
fi

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 配置文件不存在: $CONFIG_FILE"
    exit 1
fi

echo ""
echo "📋 当前配置状态:"
echo "------------------------"

# 显示当前登录类型
CURRENT_LOGIN_TYPE=$(grep "LOGIN_TYPE" "$CONFIG_FILE" | head -1 | cut -d'"' -f2)
echo "🔐 登录类型: $CURRENT_LOGIN_TYPE"

# 显示当前关键词
CURRENT_KEYWORDS=$(grep "KEYWORDS" "$CONFIG_FILE" | head -1 | cut -d'"' -f2)
echo "🔍 搜索关键词: $CURRENT_KEYWORDS"

# 显示浏览器模式
CURRENT_HEADLESS=$(grep "HEADLESS" "$CONFIG_FILE" | head -1 | awk '{print $3}')
echo "🌐 浏览器模式: $CURRENT_HEADLESS"

echo ""
echo "📝 操作选项:"
echo "------------------------"
echo "1. 使用扫码登录 (推荐)"
echo "2. 更新Cookie (需要有效的Cookie字符串)"
echo "3. 切换浏览器显示模式"
echo "4. 更新搜索关键词"
echo "5. 查看当前配置"
echo "0. 退出"

read -p "请选择操作 (0-5): " choice

case $choice in
    1)
        echo ""
        echo "🔄 配置扫码登录模式..."
        
        # 设置为扫码登录
        sed -i 's/LOGIN_TYPE = "[^"]*"/LOGIN_TYPE = "qrcode"/' "$CONFIG_FILE"
        
        # 确保浏览器非无头模式以便扫码
        sed -i 's/HEADLESS = True/HEADLESS = False/' "$CONFIG_FILE"
        
        echo "✅ 扫码登录模式已启用"
        echo "✅ 浏览器已设置为显示模式"
        echo ""
        echo "📱 扫码登录流程:"
        echo "   1. 运行爬虫程序"
        echo "   2. 二维码将保存到Windows桌面"
        echo "   3. 打开桌面上的 xhs_qrcode.png"
        echo "   4. 使用小红书APP扫描二维码"
        ;;
        
    2)
        echo ""
        echo "🍪 Cookie登录模式配置"
        echo "------------------------"
        
        read -p "请输入完整的Cookie字符串: " new_cookie
        
        if [ -z "$new_cookie" ]; then
            echo "❌ Cookie不能为空"
            exit 1
        fi
        
        # 设置Cookie登录
        sed -i 's/LOGIN_TYPE = "[^"]*"/LOGIN_TYPE = "cookie"/' "$CONFIG_FILE"
        
        # 更新Cookie
        escaped_cookie=$(echo "$new_cookie" | sed 's/[[\.*^$()+?{|]/\\&/g')
        sed -i "s/COOKIES = os.getenv(\"XHS_COOKIES\", \"[^\"]*\")/COOKIES = os.getenv(\"XHS_COOKIES\", \"$escaped_cookie\")/" "$CONFIG_FILE"
        
        # 更新环境变量文件
        if [ -f "$ENV_FILE" ]; then
            if grep -q "XHS_COOKIES" "$ENV_FILE"; then
                sed -i "s/XHS_COOKIES=.*/XHS_COOKIES=\"$new_cookie\"/" "$ENV_FILE"
            else
                echo "XHS_COOKIES=\"$new_cookie\"" >> "$ENV_FILE"
            fi
        fi
        
        echo "✅ Cookie已更新"
        echo "✅ 环境变量已设置"
        ;;
        
    3)
        echo ""
        echo "🌐 浏览器显示模式设置"
        echo "------------------------"
        echo "1. 显示浏览器 (适合调试和扫码)"
        echo "2. 无头模式 (后台运行)"
        
        read -p "请选择模式 (1-2): " browser_choice
        
        case $browser_choice in
            1)
                sed -i 's/HEADLESS = True/HEADLESS = False/' "$CONFIG_FILE"
                echo "✅ 浏览器已设置为显示模式"
                ;;
            2)
                sed -i 's/HEADLESS = False/HEADLESS = True/' "$CONFIG_FILE"
                echo "✅ 浏览器已设置为无头模式"
                ;;
            *)
                echo "❌ 无效选择"
                ;;
        esac
        ;;
        
    4)
        echo ""
        echo "🔍 搜索关键词设置"
        echo "------------------------"
        echo "当前关键词: $CURRENT_KEYWORDS"
        echo ""
        echo "建议的Web3关键词组合:"
        echo "  - TGE,代币发行,空投,IDO,新币上线"
        echo "  - DeFi,Web3项目,撸毛,测试网"
        echo "  - 区块链,加密货币,NFT,元宇宙"
        echo ""
        
        read -p "请输入新的关键词 (用逗号分隔): " new_keywords
        
        if [ -n "$new_keywords" ]; then
            escaped_keywords=$(echo "$new_keywords" | sed 's/[[\.*^$()+?{|]/\\&/g')
            sed -i "s/KEYWORDS = \"[^\"]*\"/KEYWORDS = \"$escaped_keywords\"/" "$CONFIG_FILE"
            echo "✅ 关键词已更新为: $new_keywords"
        else
            echo "❌ 关键词不能为空"
        fi
        ;;
        
    5)
        echo ""
        echo "📋 当前完整配置:"
        echo "------------------------"
        echo "配置文件: $CONFIG_FILE"
        echo ""
        grep -E "(LOGIN_TYPE|KEYWORDS|HEADLESS|PLATFORM)" "$CONFIG_FILE" | head -10
        ;;
        
    0)
        echo "👋 退出脚本"
        exit 0
        ;;
        
    *)
        echo "❌ 无效的选择"
        exit 1
        ;;
esac

echo ""
echo "🎉 配置更新完成!"
echo "📝 建议下一步操作:"
echo "   1. 运行: python3 -m pytest tests/ -v (测试配置)"
echo "   2. 启动API: python3 -m uvicorn src.api.main:app --reload"
echo "   3. 测试爬虫: curl -X POST http://localhost:8000/api/v1/crawl/xhs"
echo ""