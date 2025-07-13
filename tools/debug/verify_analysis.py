#!/usr/bin/env python3
"""
验证用户分析：QR码登录成功但内容被过滤的问题
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "mediacrawler"))

async def verify_content_filtering():
    """验证内容过滤问题"""
    
    print("🔍 验证内容过滤分析")
    print("="*60)
    
    # 切换到mediacrawler目录
    original_cwd = os.getcwd()
    mediacrawler_path = project_root / "mediacrawler"
    
    try:
        os.chdir(mediacrawler_path)
        
        # 导入必要模块
        from media_platform.xhs.core import XiaoHongShuCrawler
        from media_platform.xhs.client import XiaoHongShuClient
        from media_platform.xhs.help import get_search_id
        from media_platform.xhs.field import SearchSortType, SearchNoteType
        from playwright.async_api import async_playwright
        import config
        
        print(f"📝 当前配置:")
        print(f"   - LOGIN_TYPE: {config.LOGIN_TYPE}")
        print(f"   - HEADLESS: {config.HEADLESS}")
        
        # 创建爬虫实例
        crawler = XiaoHongShuCrawler()
        
        async with async_playwright() as playwright:
            print(f"\n🚀 启动浏览器...")
            
            # 启动浏览器
            chromium = playwright.chromium
            browser_context = await crawler.launch_browser(
                chromium, None, crawler.user_agent, headless=config.HEADLESS
            )
            
            # 设置浏览器上下文
            crawler.browser_context = browser_context
            
            # 添加脚本和Cookie
            await browser_context.add_init_script(path="libs/stealth.min.js")
            
            # 创建页面
            context_page = await browser_context.new_page()
            await context_page.goto(crawler.index_url)
            crawler.context_page = context_page
            
            print("✅ 浏览器启动成功")
            
            # 创建XHS客户端
            print(f"\n🔧 创建XHS客户端...")
            client = await crawler.create_xhs_client(None)
            
            print("✅ XHS客户端创建成功")
            
            # 测试不同的搜索参数组合
            test_cases = [
                {
                    "name": "基础搜索-美食",
                    "params": {
                        "keyword": "美食",
                        "search_id": get_search_id(),
                        "page": 1,
                        "page_size": 10,
                        "sort": SearchSortType.GENERAL,
                        "note_type": SearchNoteType.ALL
                    }
                },
                {
                    "name": "热门排序-美食",
                    "params": {
                        "keyword": "美食",
                        "search_id": get_search_id(),
                        "page": 1,
                        "page_size": 10,
                        "sort": SearchSortType.MOST_POPULAR,
                        "note_type": SearchNoteType.ALL
                    }
                },
                {
                    "name": "最新排序-美食",
                    "params": {
                        "keyword": "美食",
                        "search_id": get_search_id(),
                        "page": 1,
                        "page_size": 10,
                        "sort": SearchSortType.LATEST,
                        "note_type": SearchNoteType.ALL
                    }
                },
                {
                    "name": "视频类型-美食",
                    "params": {
                        "keyword": "美食",
                        "search_id": get_search_id(),
                        "page": 1,
                        "page_size": 10,
                        "sort": SearchSortType.GENERAL,
                        "note_type": SearchNoteType.VIDEO
                    }
                },
                {
                    "name": "图文类型-美食",
                    "params": {
                        "keyword": "美食",
                        "search_id": get_search_id(),
                        "page": 1,
                        "page_size": 10,
                        "sort": SearchSortType.GENERAL,
                        "note_type": SearchNoteType.IMAGE
                    }
                }
            ]
            
            for test_case in test_cases:
                print(f"\n" + "="*50)
                print(f"🧪 测试案例: {test_case['name']}")
                
                try:
                    # 执行搜索
                    notes_res = await client.get_note_by_keyword(**test_case['params'])
                    
                    print(f"📊 响应分析:")
                    print(f"   - 响应类型: {type(notes_res)}")
                    
                    if isinstance(notes_res, dict):
                        print(f"   - 响应键: {list(notes_res.keys())}")
                        
                        # 检查是否有权限错误
                        if 'code' in notes_res:
                            code = notes_res.get('code')
                            success = notes_res.get('success')
                            msg = notes_res.get('msg', '')
                            print(f"   - 错误代码: {code}")
                            print(f"   - 成功状态: {success}")
                            print(f"   - 错误信息: {msg}")
                            
                            if code == -104:
                                print(f"   ❌ 权限错误确认")
                            else:
                                print(f"   ✅ 非权限错误")
                        
                        # 检查正常响应结构
                        elif 'has_more' in notes_res:
                            has_more = notes_res.get('has_more')
                            items = notes_res.get('items', [])
                            print(f"   - has_more: {has_more}")
                            print(f"   - items数量: {len(items) if items else 0}")
                            
                            if len(items) == 0 and not has_more:
                                print(f"   🎯 用户分析正确：内容被过滤！")
                            elif len(items) > 0:
                                print(f"   ✅ 找到内容！")
                                print(f"   - 第一个item: {json.dumps(items[0], indent=2, ensure_ascii=False)[:200]}...")
                        
                        else:
                            print(f"   - 未知响应格式: {json.dumps(notes_res, indent=2, ensure_ascii=False)[:300]}...")
                    
                    else:
                        print(f"   - 非字典响应: {str(notes_res)[:200]}...")
                        
                except Exception as e:
                    print(f"❌ 测试失败: {type(e).__name__}: {e}")
                
                # 添加延迟
                await asyncio.sleep(3)
            
            # 清理资源
            try:
                await browser_context.close()
                print(f"\n🧹 浏览器已关闭")
            except:
                pass
                
    except Exception as e:
        print(f"❌ 验证异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    print("🔬 验证内容过滤分析工具")
    asyncio.run(verify_content_filtering())
