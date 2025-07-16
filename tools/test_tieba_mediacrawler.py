#!/usr/bin/env python3
"""
百度贴吧平台MediaCrawler集成测试脚本
验证贴吧平台适配器是否能正常工作
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crawler.platforms.tieba_platform import TiebaPlatform
from crawler.models import Platform
from config.settings import settings
import structlog

logger = structlog.get_logger()

async def test_tieba_availability():
    """测试贴吧平台是否可用"""
    print("=" * 50)
    print("测试贴吧平台可用性")
    print("=" * 50)
    
    try:
        # 创建平台实例
        config = {
            'mediacrawler_path': settings.mediacrawler_path,
            'tieba_cookie': settings.tieba_cookie,
            'tieba_enabled': settings.tieba_enabled,
            'tieba_login_method': settings.tieba_login_method,
            'tieba_headless': settings.tieba_headless,
        }
        
        platform = TiebaPlatform(config)
        
        # 测试平台可用性
        is_available = await platform.is_available()
        print(f"贴吧平台可用性: {'✓ 可用' if is_available else '✗ 不可用'}")
        
        if not is_available:
            print("贴吧平台不可用，请检查MediaCrawler配置")
            return False
        
        return True
        
    except Exception as e:
        print(f"测试贴吧平台可用性失败: {e}")
        return False

async def test_tieba_search():
    """测试贴吧搜索功能"""
    print("\n" + "=" * 50)
    print("测试贴吧搜索功能")
    print("=" * 50)
    
    try:
        # 创建平台实例
        config = {
            'mediacrawler_path': settings.mediacrawler_path,
            'tieba_cookie': settings.tieba_cookie,
            'tieba_enabled': settings.tieba_enabled,
            'tieba_login_method': settings.tieba_login_method,
            'tieba_headless': settings.tieba_headless,
        }
        
        platform = TiebaPlatform(config)
        
        # 测试搜索关键词
        test_keywords = ["TGE", "代币发行", "空投"]
        max_count = 5
        
        print(f"搜索关键词: {test_keywords}")
        print(f"最大获取数量: {max_count}")
        
        # 执行搜索
        results = await platform.crawl(test_keywords, max_count)
        
        print(f"\n搜索结果统计:")
        print(f"总共获取到 {len(results)} 条数据")
        
        # 显示结果详情
        for i, result in enumerate(results, 1):
            print(f"\n--- 结果 {i} ---")
            print(f"平台: {result.platform}")
            print(f"内容ID: {result.content_id}")
            print(f"内容类型: {result.content_type}")
            print(f"标题: {result.title}")
            print(f"作者: {result.author_name}")
            print(f"发布时间: {result.publish_time}")
            print(f"来源URL: {result.source_url}")
            print(f"点赞数: {result.like_count}")
            print(f"评论数: {result.comment_count}")
            print(f"来源关键词: {result.source_keywords}")
            print(f"内容预览: {result.content[:100] if result.content else '无'}...")
            
            if result.images:
                print(f"图片数量: {len(result.images)}")
            if result.videos:
                print(f"视频数量: {len(result.videos)}")
                
            # 贴吧特有信息
            if result.platform_specific:
                tieba_info = result.platform_specific
                print(f"贴吧名称: {tieba_info.get('tieba_name', '未知')}")
                print(f"回复数量: {tieba_info.get('total_replay_count', 0)}")
                
        return True
        
    except Exception as e:
        print(f"测试贴吧搜索功能失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_tieba_data_structure():
    """测试贴吧数据结构"""
    print("\n" + "=" * 50)
    print("测试贴吧数据结构")
    print("=" * 50)
    
    try:
        # 创建平台实例
        config = {
            'mediacrawler_path': settings.mediacrawler_path,
            'tieba_cookie': settings.tieba_cookie,
            'tieba_enabled': settings.tieba_enabled,
            'tieba_login_method': settings.tieba_login_method,
            'tieba_headless': settings.tieba_headless,
        }
        
        platform = TiebaPlatform(config)
        
        # 获取一条数据进行结构验证
        results = await platform.crawl(["TGE"], 1)
        
        if not results:
            print("没有获取到测试数据")
            return False
        
        result = results[0]
        
        print("数据结构验证:")
        print(f"✓ 平台类型: {result.platform} (应为 {Platform.TIEBA})")
        print(f"✓ 内容ID: {result.content_id} (非空: {bool(result.content_id)})")
        print(f"✓ 内容类型: {result.content_type}")
        print(f"✓ 标题: {bool(result.title)}")
        print(f"✓ 作者名称: {bool(result.author_name)}")
        print(f"✓ 作者ID: {bool(result.author_id)}")
        print(f"✓ 发布时间: {result.publish_time}")
        print(f"✓ 抓取时间: {result.crawl_time}")
        print(f"✓ 来源URL: {bool(result.source_url)}")
        print(f"✓ 互动数据: 点赞={result.like_count}, 评论={result.comment_count}")
        print(f"✓ 媒体资源: 图片={len(result.images)}, 视频={len(result.videos)}")
        print(f"✓ 平台特定数据: {bool(result.platform_specific)}")
        print(f"✓ 互动统计: {bool(result.engagement_stats)}")
        
        # 验证贴吧特有字段
        if result.platform_specific:
            tieba_specific = result.platform_specific
            print(f"✓ 贴吧名称: {tieba_specific.get('tieba_name', '未设置')}")
            print(f"✓ 贴吧链接: {bool(tieba_specific.get('tieba_link'))}")
            print(f"✓ 回复数量: {tieba_specific.get('total_replay_count', 0)}")
        
        # 验证必需字段
        required_fields = ['platform', 'content_id', 'content_type', 'title', 'content', 'raw_content', 
                          'author_name', 'author_id', 'publish_time', 'crawl_time', 'source_url']
        
        missing_fields = []
        for field in required_fields:
            if not hasattr(result, field) or getattr(result, field) is None:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"✗ 缺少必需字段: {missing_fields}")
            return False
        else:
            print("✓ 所有必需字段都存在")
        
        return True
        
    except Exception as e:
        print(f"测试贴吧数据结构失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("贴吧平台MediaCrawler集成测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"MediaCrawler路径: {settings.mediacrawler_path}")
    print(f"Cookie配置: {'已配置' if settings.tieba_cookie else '未配置'}")
    
    test_results = []
    
    # 测试1: 平台可用性
    result1 = await test_tieba_availability()
    test_results.append(("平台可用性", result1))
    
    if result1:
        # 测试2: 搜索功能
        result2 = await test_tieba_search()
        test_results.append(("搜索功能", result2))
        
        if result2:
            # 测试3: 数据结构
            result3 = await test_tieba_data_structure()
            test_results.append(("数据结构", result3))
    
    # 显示测试结果总结
    print("\n" + "=" * 50)
    print("测试结果总结")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in test_results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\n总体结果: {'✓ 所有测试通过' if all_passed else '✗ 存在测试失败'}")
    
    if all_passed:
        print("\n贴吧平台MediaCrawler集成测试成功完成！")
        print("可以开始使用贴吧平台进行数据爬取。")
    else:
        print("\n贴吧平台MediaCrawler集成测试失败！")
        print("请检查MediaCrawler配置和Cookie设置。")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(main())