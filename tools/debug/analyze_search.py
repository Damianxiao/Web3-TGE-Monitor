#!/usr/bin/env python3
"""
小红书搜索问题分析脚本
深入分析为什么返回0内容的原因
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
mediacrawler_path = project_root / "mediacrawler"
sys.path.insert(0, str(mediacrawler_path))

async def analyze_search_issue():
    """分析搜索问题"""
    original_cwd = os.getcwd()
    
    try:
        # 切换到mediacrawler目录
        os.chdir(str(mediacrawler_path))
        
        # 导入必要的模块
        from media_platform.xhs.core import XiaoHongShuCrawler
        from media_platform.xhs.client import XiaoHongShuClient
        from playwright.async_api import async_playwright
        import config
        
        print("=== 小红书搜索问题分析 ===")
        print(f"当前配置:")
        print(f"  - 登录类型: {config.LOGIN_TYPE}")
        print(f"  - 无头模式: {config.HEADLESS}")
        print(f"  - CDP模式: {config.ENABLE_CDP_MODE}")
        print(f"  - 最大爬取数量: {config.CRAWLER_MAX_NOTES_COUNT}")
        print()
        
        async with async_playwright() as playwright:
            # 创建爬虫实例
            crawler = XiaoHongShuCrawler()
            
            # 启动浏览器
            print("启动浏览器...")
            chromium = playwright.chromium
            browser_context = await crawler.launch_browser(
                chromium, None, crawler.user_agent, 
                headless=config.HEADLESS
            )
            
            # 设置浏览器上下文到爬虫对象
            crawler.browser_context = browser_context
            
            # 添加必要的脚本和Cookie
            await browser_context.add_init_script(path="libs/stealth.min.js")
            await browser_context.add_cookies([{
                "name": "webId",
                "value": "xxx123",
                "domain": ".xiaohongshu.com",
                "path": "/",
            }])
            
            # 创建页面并导航
            context_page = await browser_context.new_page()
            await context_page.goto(crawler.index_url)
            crawler.context_page = context_page
            
            # 创建XHS客户端
            client = await crawler.create_xhs_client(None)
            crawler.xhs_client = client
            
            print("测试搜索功能...")
            
            # 测试关键词
            test_keywords = ["美食", "旅行", "穿搭", "化妆"]
            
            for keyword in test_keywords:
                print(f"\n--- 测试关键词: {keyword} ---")
                
                try:
                    from media_platform.xhs.field import SearchSortType
                    from media_platform.xhs.help import get_search_id
                    
                    # 搜索笔记
                    search_id = get_search_id()
                    print(f"搜索ID: {search_id}")
                    
                    notes_res = await client.get_note_by_keyword(
                        keyword=keyword,
                        search_id=search_id,
                        page=1,
                        page_size=5,
                        sort=SearchSortType.GENERAL
                    )
                    
                    print(f"API响应结构:")
                    if notes_res:
                        print(f"  - 响应类型: {type(notes_res)}")
                        print(f"  - 响应键: {list(notes_res.keys()) if isinstance(notes_res, dict) else 'not dict'}")
                        
                        if isinstance(notes_res, dict):
                            if "items" in notes_res:
                                items = notes_res["items"]
                                print(f"  - items数量: {len(items) if items else 0}")
                                print(f"  - items类型: {type(items)}")
                                
                                if items and len(items) > 0:
                                    print(f"  - 第一个item键: {list(items[0].keys()) if isinstance(items[0], dict) else 'not dict'}")
                                    print(f"  - 第一个item内容预览: {str(items[0])[:200]}...")
                                else:
                                    print("  - items为空")
                            else:
                                print("  - 没有items字段")
                            
                            if "has_more" in notes_res:
                                print(f"  - has_more: {notes_res['has_more']}")
                            
                            # 打印完整响应（截断）
                            response_str = json.dumps(notes_res, ensure_ascii=False, indent=2)
                            print(f"  - 完整响应 (前500字符): {response_str[:500]}...")
                    else:
                        print("  - 响应为空/None")
                    
                except Exception as e:
                    print(f"搜索关键词 '{keyword}' 失败: {e}")
                    import traceback
                    print(f"详细错误: {traceback.format_exc()}")
                
                print("-" * 50)
            
            print("\n=== 分析完成 ===")
            
    except Exception as e:
        print(f"分析过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 恢复工作目录
        os.chdir(original_cwd)

if __name__ == "__main__":
    asyncio.run(analyze_search_issue())