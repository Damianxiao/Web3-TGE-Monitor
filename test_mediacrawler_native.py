#!/usr/bin/env python3
"""
测试MediaCrawler原生程序能否成功爬取知乎
"""
import sys
import os
import asyncio
from pathlib import Path

# 添加MediaCrawler路径
mediacrawler_path = Path(__file__).parent / "../MediaCrawler"
sys.path.insert(0, str(mediacrawler_path.resolve()))

# 设置环境变量
os.environ['PYTHONPATH'] = str(mediacrawler_path.resolve())

async def test_mediacrawler_zhihu():
    """测试MediaCrawler知乎爬取"""
    print("🚀 开始测试MediaCrawler原生知乎爬取...")
    
    # 切换到MediaCrawler目录
    original_dir = os.getcwd()
    mediacrawler_dir = str(Path(__file__).parent / "../MediaCrawler")
    os.chdir(mediacrawler_dir)
    print(f"📂 切换到MediaCrawler目录: {mediacrawler_dir}")
    
    try:
        # 导入MediaCrawler模块
        print("📦 导入MediaCrawler模块...")
        import config
        from media_platform.zhihu import ZhihuCrawler
        
        # 配置MediaCrawler参数
        print("⚙️ 配置MediaCrawler参数...")
        config.PLATFORM = "zhihu"
        config.LOGIN_TYPE = "cookie"
        config.CRAWLER_TYPE = "search"
        config.KEYWORDS = "Web3,DeFi"
        config.SAVE_DATA_OPTION = "json"
        config.HEADLESS = True
        config.CRAWLER_MAX_NOTES_COUNT = 5  # 限制数量用于测试
        config.ENABLE_GET_COMMENTS = False  # 禁用评论以加快测试
        
        # 设置知乎Cookie
        zhihu_cookie = os.getenv("ZHIHU_COOKIE", "")
        if not zhihu_cookie:
            # 从我们的.env文件读取
            env_path = Path(original_dir) / ".env"
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("ZHIHU_COOKIE="):
                            zhihu_cookie = line.split("=", 1)[1].strip().strip('"')
                            break
        
        if not zhihu_cookie:
            print("❌ 没有找到ZHIHU_COOKIE配置")
            return False
        
        config.COOKIES = zhihu_cookie
        print(f"🍪 使用Cookie (长度: {len(zhihu_cookie)})")
        
        # 创建爬虫实例
        print("🕷️ 创建ZhihuCrawler实例...")
        crawler = ZhihuCrawler()
        
        # 开始爬取
        print("🎯 开始执行爬取...")
        await crawler.start()
        
        print("✅ MediaCrawler知乎爬取完成！")
        
        # 检查输出文件
        data_dir = Path(mediacrawler_dir) / "data"
        if data_dir.exists():
            json_files = list(data_dir.glob("*.json"))
            if json_files:
                print(f"📄 生成的数据文件: {json_files}")
                # 读取并显示部分内容
                import json
                with open(json_files[0]) as f:
                    data = json.load(f)
                    if data:
                        print(f"📊 获取到 {len(data)} 条数据")
                        if len(data) > 0:
                            first_item = data[0]
                            print(f"📝 第一条数据类型: {first_item.get('content_type', 'unknown')}")
                            print(f"📝 第一条数据标题: {first_item.get('title', '')[:50]}...")
                        return True
                    else:
                        print("⚠️ 数据文件为空")
                        return False
            else:
                print("⚠️ 没有找到生成的JSON文件")
                return False
        else:
            print("⚠️ 没有找到data目录")
            return False
            
    except ImportError as e:
        print(f"❌ MediaCrawler模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ MediaCrawler测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 恢复原始工作目录
        os.chdir(original_dir)


async def test_minimal_zhihu_client():
    """测试最小化的知乎客户端"""
    print("\n🧪 测试最小化知乎客户端...")
    
    # 切换到MediaCrawler目录
    original_dir = os.getcwd()
    mediacrawler_dir = str(Path(__file__).parent / "../MediaCrawler")
    os.chdir(mediacrawler_dir)
    print(f"📂 切换到MediaCrawler目录: {mediacrawler_dir}")
    
    try:
        # 导入必要模块
        sys.path.insert(0, mediacrawler_dir)
        
        from media_platform.zhihu.client import ZhiHuClient
        from media_platform.zhihu.field import SearchSort, SearchTime, SearchType
        import httpx
        
        # 获取Cookie
        zhihu_cookie = os.getenv("ZHIHU_COOKIE", "")
        if not zhihu_cookie:
            env_path = Path(original_dir) / ".env"
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("ZHIHU_COOKIE="):
                            zhihu_cookie = line.split("=", 1)[1].strip().strip('"')
                            break
        
        if not zhihu_cookie:
            print("❌ 没有ZHIHU_COOKIE")
            return False
        
        # 解析Cookie
        cookie_dict = {}
        for item in zhihu_cookie.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookie_dict[key] = value
        
        # 创建客户端
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "cookie": zhihu_cookie,
        }
        
        client = ZhiHuClient(
            timeout=20,
            headers=headers,
            playwright_page=None,
            cookie_dict=cookie_dict
        )
        
        # 测试搜索
        print("🔍 执行搜索请求...")
        results = await client.get_note_by_keyword(
            keyword="Web3",
            page=1,
            page_size=5,
            sort=SearchSort.DEFAULT,
            note_type=SearchType.DEFAULT,
            search_time=SearchTime.DEFAULT
        )
        
        if results:
            print(f"✅ 搜索成功，获得 {len(results)} 条结果")
            for i, result in enumerate(results[:2]):
                print(f"📝 结果 {i+1}: {result.title[:50]}...")
            return True
        else:
            print("⚠️ 搜索返回空结果")
            return False
            
    except Exception as e:
        print(f"❌ 最小化客户端测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 恢复原始工作目录
        os.chdir(original_dir)


async def main():
    """主测试函数"""
    print("🧪 MediaCrawler原生程序测试开始")
    print("=" * 60)
    
    # 测试1: 完整MediaCrawler程序
    success1 = await test_mediacrawler_zhihu()
    
    # 测试2: 最小化客户端
    success2 = await test_minimal_zhihu_client()
    
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    print(f"MediaCrawler完整程序: {'✅ 成功' if success1 else '❌ 失败'}")
    print(f"最小化知乎客户端: {'✅ 成功' if success2 else '❌ 失败'}")
    
    if success1 or success2:
        print("\n🎉 至少一种方式成功！MediaCrawler原生程序可以工作")
        print("💡 建议: 直接集成MediaCrawler而不是重新实现")
    else:
        print("\n💥 所有测试都失败了")
        print("💡 可能原因:")
        print("   1. Cookie已过期，需要重新获取")
        print("   2. 知乎加强了反爬虫机制") 
        print("   3. MediaCrawler版本与知乎API不兼容")


if __name__ == "__main__":
    asyncio.run(main())