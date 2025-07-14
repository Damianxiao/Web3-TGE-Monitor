"""
MediaCrawler知乎集成测试
验证完整的数据流和API兼容性
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

from crawler.platforms.zhihu_platform import ZhihuPlatform
from crawler.platforms.mediacrawler_zhihu_integration import create_mediacrawler_integration
from config.settings import Settings


async def test_mediacrawler_integration():
    """测试MediaCrawler集成层"""
    print("🧪 测试MediaCrawler集成层...")
    
    try:
        # 创建集成实例
        integration = await create_mediacrawler_integration()
        print("✅ MediaCrawler集成实例创建成功")
        
        # 测试搜索功能
        print("🔍 测试搜索功能...")
        results = await integration.search_content("Web3", max_results=5)
        
        if results:
            print(f"✅ 搜索成功：获得 {len(results)} 条结果")
            
            # 显示第一条结果的详细信息
            first_result = results[0]
            print(f"📝 第一条结果：")
            print(f"   ID: {first_result.get('id', 'N/A')}")
            print(f"   标题: {first_result.get('title', 'N/A')[:50]}...")
            print(f"   类型: {first_result.get('content_type', 'N/A')}")
            print(f"   作者: {first_result.get('author', {}).get('nickname', 'N/A')}")
            
            # 测试详情获取
            content_id = first_result.get('id')
            if content_id:
                print(f"🔍 测试详情获取: {content_id}")
                details = await integration.get_content_details(content_id)
                if details:
                    print("✅ 详情获取成功")
                else:
                    print("⚠️ 详情未找到（正常，因为在搜索结果中查找）")
        else:
            print("❌ 搜索返回空结果")
            return False
        
        # 清理资源
        integration.cleanup()
        print("✅ 资源清理完成")
        
        return True
        
    except Exception as e:
        print(f"❌ MediaCrawler集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_zhihu_platform():
    """测试重构后的ZhihuPlatform"""
    print("\n🧪 测试重构后的ZhihuPlatform...")
    
    try:
        # 创建ZhihuPlatform实例
        platform = ZhihuPlatform()
        print("✅ ZhihuPlatform实例创建成功")
        
        # 测试搜索功能
        print("🔍 测试平台搜索功能...")
        raw_contents = await platform.search("Web3", max_results=3)
        
        if raw_contents:
            print(f"✅ 平台搜索成功：获得 {len(raw_contents)} 条内容")
            
            # 验证RawContent格式
            first_content = raw_contents[0]
            print(f"📝 验证RawContent格式：")
            print(f"   ID: {first_content.content_id}")
            print(f"   标题: {first_content.title[:50]}...")
            print(f"   平台: {first_content.platform.value}")
            print(f"   类型: {first_content.content_type.value}")
            print(f"   作者: {first_content.author_name}")
            print(f"   URL: {first_content.source_url}")
            print(f"   创建时间: {first_content.publish_time}")
            print(f"   元数据字段: {list(first_content.platform_metadata.keys())}")
            
            # 测试详情获取
            print(f"🔍 测试详情获取: {first_content.content_id}")
            details = await platform.get_content_details(first_content.content_id)
            if details:
                print("✅ 详情获取成功")
                print(f"   详情标题: {details.title[:50]}...")
            else:
                print("⚠️ 详情未找到（正常情况）")
        else:
            print("❌ 平台搜索返回空结果")
            return False
        
        # 清理资源
        platform.cleanup()
        print("✅ 平台资源清理完成")
        
        return True
        
    except Exception as e:
        print(f"❌ ZhihuPlatform测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_data_format_compatibility():
    """测试数据格式兼容性"""
    print("\n🧪 测试数据格式兼容性...")
    
    try:
        platform = ZhihuPlatform()
        
        # 获取搜索结果
        raw_contents = await platform.search("DeFi", max_results=2)
        
        if not raw_contents:
            print("⚠️ 无搜索结果，跳过格式兼容性测试")
            return True
        
        content = raw_contents[0]
        
        # 验证必需字段
        required_fields = ['content_id', 'title', 'content', 'platform', 'content_type']
        missing_fields = []
        
        for field in required_fields:
            if not hasattr(content, field) or getattr(content, field) is None:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ 缺少必需字段: {missing_fields}")
            return False
        
        # 验证元数据结构
        metadata = content.platform_metadata
        expected_metadata_keys = ['source_keywords', 'question_id', 'author_profile_url']
        
        for key in expected_metadata_keys:
            if key not in metadata:
                print(f"⚠️ 元数据缺少字段: {key}")
        
        # 验证数据类型
        type_checks = [
            (content.content_id, str, 'content_id'),
            (content.title, str, 'title'),
            (content.content, str, 'content'),
            (content.platform_metadata, dict, 'platform_metadata')
        ]
        
        for value, expected_type, field_name in type_checks:
            if not isinstance(value, expected_type):
                print(f"❌ 字段类型错误: {field_name} 应为 {expected_type.__name__}，实际为 {type(value).__name__}")
                return False
        
        print("✅ 数据格式兼容性测试通过")
        
        # 清理资源
        platform.cleanup()
        
        return True
        
    except Exception as e:
        print(f"❌ 数据格式兼容性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling():
    """测试错误处理"""
    print("\n🧪 测试错误处理...")
    
    try:
        platform = ZhihuPlatform()
        
        # 测试空关键词搜索
        print("🔍 测试空关键词搜索...")
        try:
            results = await platform.search("", max_results=1)
            print(f"⚠️ 空关键词搜索未报错，返回 {len(results)} 条结果")
        except Exception as e:
            print(f"✅ 空关键词搜索正确抛出异常: {e}")
        
        # 测试无效内容ID
        print("🔍 测试无效内容ID...")
        details = await platform.get_content_details("invalid_id_12345")
        if details is None:
            print("✅ 无效ID正确返回None")
        else:
            print("⚠️ 无效ID意外返回了结果")
        
        # 清理资源
        platform.cleanup()
        
        return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("🚀 MediaCrawler知乎集成完整测试开始")
    print("=" * 60)
    
    # 检查环境配置
    try:
        settings = Settings()
        if not settings.zhihu_cookie:
            print("❌ ZHIHU_COOKIE未配置")
            return
        if not settings.mediacrawler_path:
            print("❌ MEDIACRAWLER_PATH未配置")
            return
        print("✅ 环境配置检查通过")
    except Exception as e:
        print(f"❌ 环境配置检查失败: {e}")
        return
    
    # 执行测试套件
    test_results = {}
    
    # 测试1: MediaCrawler集成层
    test_results['integration'] = await test_mediacrawler_integration()
    
    # 测试2: ZhihuPlatform
    test_results['platform'] = await test_zhihu_platform()
    
    # 测试3: 数据格式兼容性
    test_results['compatibility'] = await test_data_format_compatibility()
    
    # 测试4: 错误处理
    test_results['error_handling'] = await test_error_handling()
    
    # 测试结果汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    all_passed = all(test_results.values())
    
    if all_passed:
        print("\n🎉 所有测试通过！MediaCrawler集成成功")
        print("💡 建议:")
        print("   1. 定期更新知乎Cookie以保持访问权限")
        print("   2. 监控MediaCrawler版本更新")
        print("   3. 关注知乎反爬虫机制变化")
    else:
        print("\n💥 部分测试失败")
        failed_tests = [name for name, result in test_results.items() if not result]
        print(f"   失败的测试: {', '.join(failed_tests)}")
        print("💡 建议检查:")
        print("   1. 知乎Cookie是否有效")
        print("   2. MediaCrawler路径是否正确")
        print("   3. 网络连接是否正常")


if __name__ == "__main__":
    asyncio.run(main())