#!/usr/bin/env python3
"""
简单测试Playwright + MediaCrawler集成
"""
import asyncio
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
sys.path.insert(0, '../MediaCrawler')

from dotenv import load_dotenv
import structlog

# 加载环境变量
load_dotenv()

# 配置日志
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def test_playwright_basic():
    """测试基础Playwright功能"""
    try:
        from playwright.async_api import async_playwright
        
        logger.info("🎭 测试Playwright基础功能...")
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 测试基本页面访问
        await page.goto("https://www.zhihu.com")
        title = await page.title()
        
        logger.info(f"✅ 成功访问知乎首页: {title}")
        
        await browser.close()
        await playwright.stop()
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Playwright导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Playwright测试失败: {e}")
        return False


async def test_mediacrawler_constants():
    """测试MediaCrawler常量导入"""
    try:
        from constant.zhihu import ZHIHU_URL
        logger.info(f"✅ MediaCrawler常量导入成功: {ZHIHU_URL}")
        return True
    except Exception as e:
        logger.error(f"❌ MediaCrawler常量导入失败: {e}")
        return False


async def test_js_signature():
    """测试JS签名功能"""
    try:
        import execjs
        
        # 检查zhihu.js文件
        js_path = os.path.join(os.getcwd(), "libs", "zhihu.js")
        if not os.path.exists(js_path):
            logger.error(f"❌ zhihu.js文件不存在: {js_path}")
            return False
        
        # 读取并编译JS
        with open(js_path, 'r', encoding='utf-8') as f:
            js_code = f.read()
        
        js_ctx = execjs.compile(js_code)
        
        # 测试签名
        test_url = "https://www.zhihu.com/api/v4/search_v3?t=general&q=test"
        test_cookie = os.getenv("ZHIHU_COOKIE", "")
        
        if not test_cookie:
            logger.warning("⚠️ 没有提供ZHIHU_COOKIE，跳过签名测试")
            return False
        
        result = js_ctx.call("get_sign", test_url, test_cookie)
        
        if result and 'x-zst-81' in result and 'x-zse-96' in result:
            logger.info("✅ JS签名功能正常")
            logger.info(f"签名结果: x-zst-81={result['x-zst-81'][:20]}...")
            return True
        else:
            logger.error("❌ JS签名返回格式不正确")
            return False
            
    except ImportError as e:
        logger.error(f"❌ execjs导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ JS签名测试失败: {e}")
        return False


async def test_combined_request():
    """测试完整的请求流程"""
    try:
        from playwright.async_api import async_playwright
        import execjs
        
        cookie = os.getenv("ZHIHU_COOKIE", "")
        if not cookie:
            logger.error("❌ 没有ZHIHU_COOKIE配置")
            return False
        
        logger.info("🚀 测试完整的Playwright + JS签名请求...")
        
        # 启动Playwright
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        
        # 创建上下文并添加Cookie
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        
        # 解析Cookie
        cookies = []
        for item in cookie.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies.append({
                    'name': key,
                    'value': value,
                    'domain': '.zhihu.com',
                    'path': '/'
                })
        
        await context.add_cookies(cookies)
        page = await context.new_page()
        
        # 准备JS签名
        js_path = os.path.join(os.getcwd(), "libs", "zhihu.js")
        with open(js_path, 'r', encoding='utf-8') as f:
            js_code = f.read()
        js_ctx = execjs.compile(js_code)
        
        # 构建请求
        test_url = "https://www.zhihu.com/api/v4/search_v3?gk_version=gz-gaokao&t=general&q=Web3&correction=1&offset=0&limit=10&filter_fields=&lc_idx=0&show_all_topics=0&search_source=Filter&time_interval=0&sort=default&vertical=default"
        sign_result = js_ctx.call("get_sign", test_url, cookie)
        
        # 构建请求头
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Cookie": cookie,
            "Referer": "https://www.zhihu.com/search?type=content&q=Web3",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "x-zst-81": sign_result.get("x-zst-81", ""),
            "x-zse-96": sign_result.get("x-zse-96", "")
        }
        
        # 提取XSRF token
        xsrf_token = ""
        if '_xsrf=' in cookie:
            for part in cookie.split(';'):
                if '_xsrf=' in part:
                    xsrf_token = part.split('=')[1].strip()
                    break
        
        if xsrf_token:
            headers["X-Xsrftoken"] = xsrf_token
        
        # 发送请求
        response = await page.request.get(test_url, headers=headers)
        
        logger.info(f"请求状态: {response.status}")
        
        if response.status == 200:
            data = await response.json()
            results = data.get('data', [])
            logger.info(f"✅ 成功获取搜索结果: {len(results)} 条")
            
            if results:
                first_result = results[0]
                logger.info(f"第一条结果类型: {first_result.get('type')}")
                logger.info(f"第一条结果标题: {first_result.get('title', '')[:50]}")
            
            await browser.close()
            await playwright.stop()
            return True
        else:
            response_text = await response.text()
            logger.error(f"❌ 请求失败，响应: {response_text[:200]}")
            
            await browser.close()
            await playwright.stop()
            return False
            
    except Exception as e:
        logger.error(f"❌ 完整请求测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("🧪 开始MediaCrawler集成测试...")
    
    tests = [
        ("MediaCrawler常量导入", test_mediacrawler_constants()),
        ("Playwright基础功能", test_playwright_basic()),
        ("JS签名功能", test_js_signature()),
        ("完整请求流程", test_combined_request())
    ]
    
    results = {}
    for test_name, test_coro in tests:
        logger.info(f"\n--- 测试: {test_name} ---")
        try:
            result = await test_coro
            results[test_name] = result
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            logger.error(f"{test_name}: ❌ 异常 - {e}")
            results[test_name] = False
    
    # 打印总结
    logger.info("\n" + "="*60)
    logger.info("📊 测试结果总结")
    logger.info("="*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\n总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！MediaCrawler集成成功！")
    else:
        logger.info("💥 部分测试失败，需要进一步调试")


if __name__ == "__main__":
    asyncio.run(main())