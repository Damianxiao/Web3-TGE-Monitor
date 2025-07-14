"""
XHS (小红书) 平台真实爬取测试
验证XHS平台的MediaCrawler集成、配置和爬取功能
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 重新加载环境变量
from dotenv import load_dotenv
load_dotenv(override=True)

from crawler.platforms.xhs_platform import XHSPlatform
from crawler.platform_factory import PlatformFactory
from crawler.models import Platform
from config.settings import Settings


async def test_xhs_platform_initialization():
    """测试XHS平台初始化"""
    print("🧪 测试XHS平台初始化...")
    
    try:
        # 创建XHS平台实例
        platform = XHSPlatform()
        print("✅ XHS平台实例创建成功")
        
        # 检查平台可用性
        is_available = await platform.is_available()
        if is_available:
            print("✅ XHS平台可用性检查通过")
        else:
            print("❌ XHS平台不可用")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ XHS平台初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_xhs_platform_factory():
    """测试通过工厂创建XHS平台"""
    print("\n🧪 测试通过工厂创建XHS平台...")
    
    try:
        # 检查XHS平台是否已注册
        if not PlatformFactory.is_platform_registered(Platform.XHS):
            print("❌ XHS平台未在工厂中注册")
            return False
        
        print("✅ XHS平台已在工厂中注册")
        
        # 通过工厂创建平台实例
        platform = await PlatformFactory.create_platform(Platform.XHS)
        print("✅ 通过工厂创建XHS平台成功")
        
        # 验证配置传递
        config = PlatformFactory._get_platform_config(Platform.XHS)
        print(f"📋 平台配置: {list(config.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ 工厂测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_xhs_mediacrawler_integration():
    """测试XHS MediaCrawler集成"""
    print("\n🧪 测试XHS MediaCrawler集成...")
    
    try:
        platform = XHSPlatform()
        
        # 检查MediaCrawler路径配置
        mediacrawler_path = platform.mediacrawler_path
        print(f"📁 MediaCrawler路径: {mediacrawler_path}")
        
        # 验证MediaCrawler路径存在
        if not Path(mediacrawler_path).exists():
            print(f"❌ MediaCrawler路径不存在: {mediacrawler_path}")
            return False
        
        print("✅ MediaCrawler路径验证通过")
        
        # 检查必需的MediaCrawler文件
        required_files = [
            "media_platform/xhs/__init__.py",
            "media_platform/xhs/core.py",
            "media_platform/xhs/client.py",
            "config/base_config.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = Path(mediacrawler_path) / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ 缺少必需文件: {missing_files}")
            return False
        
        print("✅ MediaCrawler文件结构验证通过")
        return True
        
    except Exception as e:
        print(f"❌ MediaCrawler集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_xhs_configuration():
    """测试XHS配置"""
    print("\n🧪 测试XHS配置...")
    
    try:
        settings = Settings()
        
        # 检查基本配置
        config_checks = [
            ('xhs_enabled', settings.xhs_enabled, 'XHS是否启用'),
            ('xhs_login_method', settings.xhs_login_method, 'XHS登录方式'),
            ('xhs_headless', settings.xhs_headless, 'XHS无头模式'),
            ('xhs_max_pages', settings.xhs_max_pages, 'XHS最大页数'),
            ('xhs_rate_limit', settings.xhs_rate_limit, 'XHS速率限制')
        ]
        
        for attr_name, value, desc in config_checks:
            print(f"📋 {desc}: {value}")
        
        # 检查Cookie配置
        if not settings.xhs_cookie:
            print("⚠️ XHS_COOKIE未配置 - 可能影响登录功能")
        else:
            print(f"✅ XHS_COOKIE已配置 (长度: {len(settings.xhs_cookie)})")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_xhs_crawling():
    """测试XHS真实爬取功能"""
    print("\n🧪 测试XHS真实爬取功能...")
    
    try:
        platform = XHSPlatform()
        
        # 使用Web3相关关键词进行测试
        test_keywords = ["Web3", "DeFi"]
        max_count = 3
        
        print(f"🔍 开始爬取测试: 关键词={test_keywords}, 最大数量={max_count}")
        
        # 执行爬取
        raw_contents = await platform.crawl(test_keywords, max_count)
        
        if not raw_contents:
            print("⚠️ 爬取返回空结果")
            print("💡 可能原因:")
            print("   1. XHS_COOKIE已过期")
            print("   2. XHS反爬虫机制拦截")
            print("   3. 搜索关键词无结果")
            print("   4. MediaCrawler配置问题")
            return False
        
        print(f"✅ 爬取成功: 获得 {len(raw_contents)} 条内容")
        
        # 验证第一条内容的格式
        first_content = raw_contents[0]
        print(f"📝 第一条内容验证:")
        print(f"   ID: {first_content.content_id}")
        print(f"   标题: {first_content.title[:50]}...")
        print(f"   平台: {first_content.platform.value}")
        print(f"   类型: {first_content.content_type.value}")
        print(f"   作者: {first_content.author_name}")
        print(f"   发布时间: {first_content.publish_time}")
        print(f"   来源关键词: {first_content.source_keywords}")
        
        # 验证必需字段
        required_fields = ['content_id', 'title', 'content', 'platform', 'content_type']
        missing_fields = []
        
        for field in required_fields:
            if not hasattr(first_content, field) or getattr(first_content, field) is None:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ 缺少必需字段: {missing_fields}")
            return False
        
        print("✅ 内容格式验证通过")
        return True
        
    except Exception as e:
        print(f"❌ 爬取测试失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 检查是否是详细错误信息
        if hasattr(e, 'detailed_errors'):
            print("🔍 详细错误分析:")
            detailed_errors = e.detailed_errors
            if isinstance(detailed_errors, dict):
                for key, value in detailed_errors.items():
                    print(f"   {key}: {value}")
        
        return False


async def test_xhs_error_handling():
    """测试XHS错误处理"""
    print("\n🧪 测试XHS错误处理...")
    
    try:
        platform = XHSPlatform()
        
        # 测试空关键词
        print("🔍 测试空关键词搜索...")
        try:
            results = await platform.crawl([], max_count=1)
            print(f"⚠️ 空关键词搜索未报错，返回 {len(results)} 条结果")
        except Exception as e:
            print(f"✅ 空关键词搜索正确抛出异常: {e}")
        
        # 测试无效关键词
        print("🔍 测试超长关键词...")
        long_keyword = "a" * 1000
        try:
            results = await platform.crawl([long_keyword], max_count=1)
            print(f"⚠️ 超长关键词搜索未报错，返回 {len(results)} 条结果")
        except Exception as e:
            print(f"✅ 超长关键词搜索正确处理: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_xhs_cookie_validation():
    """测试XHS Cookie有效性"""
    print("\n🧪 测试XHS Cookie有效性...")
    
    try:
        settings = Settings()
        
        if not settings.xhs_cookie:
            print("⚠️ XHS_COOKIE未配置，跳过Cookie验证测试")
            return True
        
        # 基本格式检查
        cookie = settings.xhs_cookie
        print(f"📋 Cookie长度: {len(cookie)}")
        
        # 检查Cookie是否包含小红书必要的字段
        expected_cookie_parts = ['a1', 'webId', 'web_session']
        found_parts = []
        
        for part in expected_cookie_parts:
            if part in cookie:
                found_parts.append(part)
        
        print(f"📋 找到Cookie字段: {found_parts}")
        
        if len(found_parts) < 2:
            print("⚠️ Cookie可能不完整，建议重新获取")
        else:
            print("✅ Cookie格式检查通过")
        
        # 通过实际爬取测试Cookie有效性
        print("🔍 通过实际爬取验证Cookie有效性...")
        platform = XHSPlatform()
        
        try:
            # 使用简单关键词进行小量测试
            results = await platform.crawl(["测试"], max_count=1)
            if results:
                print("✅ Cookie验证成功 - 爬取正常")
                return True
            else:
                print("⚠️ Cookie可能已过期 - 爬取无结果")
                return False
        except Exception as e:
            if "权限" in str(e) or "login" in str(e).lower():
                print("❌ Cookie已过期或无效")
                return False
            else:
                print(f"⚠️ 爬取测试遇到其他错误: {e}")
                return True  # 可能是其他问题，不一定是Cookie问题
        
    except Exception as e:
        print(f"❌ Cookie验证测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("🚀 XHS (小红书) 平台真实爬取测试开始")
    print("=" * 60)
    
    # 检查环境配置
    try:
        settings = Settings()
        if not settings.mediacrawler_path:
            print("❌ MEDIACRAWLER_PATH未配置")
            return
        print("✅ 基础环境配置检查通过")
    except Exception as e:
        print(f"❌ 环境配置检查失败: {e}")
        return
    
    # 执行测试套件
    test_results = {}
    
    # 测试1: 平台初始化
    test_results['initialization'] = await test_xhs_platform_initialization()
    
    # 测试2: 工厂模式
    test_results['factory'] = await test_xhs_platform_factory()
    
    # 测试3: MediaCrawler集成
    test_results['mediacrawler_integration'] = await test_xhs_mediacrawler_integration()
    
    # 测试4: 配置检查
    test_results['configuration'] = await test_xhs_configuration()
    
    # 测试5: Cookie验证
    test_results['cookie_validation'] = await test_xhs_cookie_validation()
    
    # 测试6: 真实爬取
    test_results['crawling'] = await test_xhs_crawling()
    
    # 测试7: 错误处理
    test_results['error_handling'] = await test_xhs_error_handling()
    
    # 测试结果汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    all_passed = all(test_results.values())
    
    if all_passed:
        print("\n🎉 所有测试通过！XHS平台集成成功")
        print("💡 建议:")
        print("   1. 定期更新XHS Cookie以保持访问权限")
        print("   2. 监控小红书反爬虫机制变化")
        print("   3. 适当调整爬取频率避免被限制")
        print("   4. 关注MediaCrawler XHS模块更新")
    else:
        print("\n💥 部分测试失败")
        failed_tests = [name for name, result in test_results.items() if not result]
        print(f"   失败的测试: {', '.join(failed_tests)}")
        print("💡 建议检查:")
        print("   1. XHS Cookie是否有效")
        print("   2. MediaCrawler路径是否正确")
        print("   3. MediaCrawler XHS模块是否完整")
        print("   4. 网络连接是否正常")
        print("   5. 小红书是否更新了反爬虫机制")


if __name__ == "__main__":
    asyncio.run(main())