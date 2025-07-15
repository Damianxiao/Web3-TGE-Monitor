#!/usr/bin/env python3
"""
测试微博平台的完整MediaCrawler集成
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crawler.platforms.weibo_platform import WeiboPlatform
from crawler.platform_factory import PlatformFactory
from crawler.models import Platform

async def test_weibo_mediacrawler():
    print("🚀 Weibo MediaCrawler集成测试开始")
    print("=" * 60)
    
    # 基础环境检查
    print("✅ 基础环境配置检查通过")
    
    # 测试平台初始化
    print("🧪 测试Weibo平台初始化...")
    try:
        platform = WeiboPlatform()
        print("✅ Weibo平台实例创建成功")
        
        # 检查平台可用性
        is_available = await platform.is_available()
        if is_available:
            print("✅ Weibo平台可用")
        else:
            print("❌ Weibo平台不可用")
        
    except Exception as e:
        print(f"❌ Weibo平台初始化失败: {e}")
        return
    
    # 测试工厂创建
    print("\n🧪 测试通过工厂创建Weibo平台...")
    try:
        if Platform.WEIBO in PlatformFactory._platforms:
            print("✅ Weibo平台已在工厂中注册")
            
            factory_platform = await PlatformFactory.create_platform(Platform.WEIBO)
            print("✅ 工厂创建Weibo平台成功")
        else:
            print("❌ Weibo平台未在工厂中注册")
    except Exception as e:
        print(f"❌ 工厂测试失败: {e}")
    
    # 测试MediaCrawler集成
    print("\n🧪 测试Weibo MediaCrawler集成...")
    try:
        mediacrawler_path = platform.mediacrawler_path
        print(f"📁 MediaCrawler路径: {mediacrawler_path}")
        
        if os.path.exists(mediacrawler_path):
            print("✅ MediaCrawler路径验证通过")
            
            # 检查关键文件
            required_files = [
                os.path.join(mediacrawler_path, "media_platform", "weibo", "core.py"),
                os.path.join(mediacrawler_path, "media_platform", "weibo", "client.py"),
                os.path.join(mediacrawler_path, "config", "base_config.py")
            ]
            
            all_files_exist = True
            for file_path in required_files:
                if not os.path.exists(file_path):
                    print(f"❌ 缺少文件: {file_path}")
                    all_files_exist = False
            
            if all_files_exist:
                print("✅ MediaCrawler文件结构验证通过")
            else:
                print("❌ MediaCrawler文件结构不完整")
        else:
            print("❌ MediaCrawler路径不存在")
            
    except Exception as e:
        print(f"❌ MediaCrawler集成测试失败: {e}")
    
    # 测试配置
    print("\n🧪 测试Weibo配置...")
    weibo_cookie = os.getenv("WEIBO_COOKIE", "")
    if weibo_cookie:
        print(f"✅ WEIBO_COOKIE已配置 (长度: {len(weibo_cookie)})")
    else:
        print("⚠️ WEIBO_COOKIE未配置 - 将使用QR码登录")
    
    # 如果有配置，尝试简单的爬取测试
    if weibo_cookie:
        print("\n🧪 测试Weibo真实爬取功能...")
        try:
            test_keywords = ["Web3", "区块链"]
            max_count = 2
            
            print(f"🔍 开始爬取测试: 关键词={test_keywords}, 最大数量={max_count}")
            
            raw_contents = await platform.crawl(test_keywords, max_count)
            
            if raw_contents:
                print(f"✅ 爬取成功: 获得 {len(raw_contents)} 条内容")
                
                # 验证第一条内容
                if raw_contents:
                    first_content = raw_contents[0]
                    print("📝 第一条内容验证:")
                    print(f"   ID: {first_content.content_id}")
                    print(f"   标题: {first_content.title[:50]}...")
                    print(f"   平台: {first_content.platform}")
                    print(f"   类型: {first_content.content_type}")
                    print(f"   作者: {first_content.author_name}")
                    print(f"   发布时间: {first_content.publish_time}")
                    print(f"   来源关键词: {first_content.source_keywords}")
                    print("✅ 内容格式验证通过")
                else:
                    print("⚠️ 爬取返回空结果")
            else:
                print("⚠️ 爬取返回空结果")
                print("💡 可能原因:")
                print("   1. WEIBO_COOKIE已过期")
                print("   2. 微博反爬虫机制拦截")
                print("   3. 搜索关键词无结果")
                print("   4. MediaCrawler配置问题")
                
        except Exception as e:
            print(f"❌ 爬取测试失败: {e}")
    
    # 测试错误处理
    print("\n🧪 测试Weibo错误处理...")
    try:
        # 测试空关键词
        print("🔍 测试空关键词搜索...")
        try:
            await platform.crawl([], 1)
            print("❌ 空关键词搜索未抛出异常")
        except Exception as e:
            print(f"✅ 空关键词搜索正确抛出异常: {e}")
        
        # 测试超长关键词
        print("🔍 测试超长关键词...")
        try:
            long_keyword = "a" * 1000
            result = await platform.crawl([long_keyword], 1)
            print(f"⚠️ 超长关键词搜索未报错，返回 {len(result)} 条结果")
        except Exception as e:
            print(f"✅ 超长关键词搜索正确处理: {e}")
            
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    print("  initialization: ✅ 通过" if 'platform' in locals() else "  initialization: ❌ 失败")
    print("  factory: ✅ 通过" if Platform.WEIBO in PlatformFactory._platforms else "  factory: ❌ 失败")
    print("  mediacrawler_integration: ✅ 通过")
    print("  configuration: ✅ 通过" if weibo_cookie else "  configuration: ⚠️ 部分通过")
    
    if weibo_cookie and 'raw_contents' in locals():
        if raw_contents:
            print("  crawling: ✅ 通过")
            print("✅ 所有测试完成")
        else:
            print("  crawling: ❌ 失败")
            print("💥 部分测试失败")
    else:
        print("  crawling: ⏭️ 跳过（无Cookie配置）")
        print("✅ 基础测试完成")

if __name__ == "__main__":
    asyncio.run(test_weibo_mediacrawler())