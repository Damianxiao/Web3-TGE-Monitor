#!/usr/bin/env python3
"""
小红书QR码登录脚本 - CDP模式
直接操作Windows Chrome浏览器进行登录
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
mediacrawler_path = project_root / "mediacrawler"
sys.path.insert(0, str(mediacrawler_path))

async def perform_qr_login():
    """执行QR码登录"""
    original_cwd = os.getcwd()
    
    try:
        # 切换到mediacrawler目录
        os.chdir(str(mediacrawler_path))
        
        # 导入必要的模块
        from media_platform.xhs.login import XiaoHongShuLogin
        from media_platform.xhs.core import XiaoHongShuCrawler
        from playwright.async_api import async_playwright
        import config
        
        print("开始QR码登录流程...")
        print(f"CDP模式: {config.ENABLE_CDP_MODE}")
        print(f"浏览器路径: {config.CUSTOM_BROWSER_PATH}")
        
        async with async_playwright() as playwright:
            # 创建爬虫实例
            crawler = XiaoHongShuCrawler()
            
            # 根据配置启动浏览器
            if config.ENABLE_CDP_MODE:
                print("使用CDP模式启动浏览器...")
                browser_context = await crawler.launch_browser_with_cdp(
                    playwright, None, crawler.user_agent,
                    headless=config.CDP_HEADLESS
                )
            else:
                print("使用普通模式启动浏览器...")
                chromium = playwright.chromium
                browser_context = await crawler.launch_browser(
                    chromium, None, crawler.user_agent, 
                    headless=config.HEADLESS
                )
            
            # 创建新页面
            context_page = await browser_context.new_page()
            
            print("导航到小红书主页...")
            await context_page.goto("https://www.xiaohongshu.com")
            
            # 等待页面加载
            await asyncio.sleep(2)
            
            # 创建登录实例
            print("创建登录实例...")
            login_instance = XiaoHongShuLogin(
                login_type=config.LOGIN_TYPE,
                browser_context=browser_context,
                context_page=context_page,
                cookie_str=""
            )
            
            print("开始登录流程，请在浏览器中扫描QR码...")
            await login_instance.begin()
            
            print("登录流程完成!")
            
            # 保持浏览器打开一段时间以便用户操作
            print("保持浏览器打开30秒以确认登录状态...")
            await asyncio.sleep(30)
            
    except Exception as e:
        print(f"登录失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 恢复工作目录
        os.chdir(original_cwd)

if __name__ == "__main__":
    asyncio.run(perform_qr_login())