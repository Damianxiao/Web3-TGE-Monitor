#!/usr/bin/env python3
"""
MediaCrawler模块导入测试
验证是否能成功导入MediaCrawler的关键组件
"""
import sys
import os

# 添加MediaCrawler路径到Python路径
mediacrawler_path = '/home/damian/MediaCrawler'
if mediacrawler_path not in sys.path:
    sys.path.insert(0, mediacrawler_path)

def test_imports():
    """测试关键模块的导入"""
    results = {}
    
    # 测试1: 基础模块导入
    try:
        from media_platform.xhs import client as xhs_client
        results['xhs_client'] = "✅ SUCCESS"
        print("✅ XHS client模块导入成功")
    except Exception as e:
        results['xhs_client'] = f"❌ FAILED: {e}"
        print(f"❌ XHS client模块导入失败: {e}")
    
    # 测试2: 核心爬虫模块
    try:
        from media_platform.xhs import core as xhs_core  
        results['xhs_core'] = "✅ SUCCESS"
        print("✅ XHS core模块导入成功")
    except Exception as e:
        results['xhs_core'] = f"❌ FAILED: {e}"
        print(f"❌ XHS core模块导入失败: {e}")
    
    # 测试3: 基础爬虫类
    try:
        from base.base_crawler import AbstractCrawler, AbstractApiClient
        results['base_crawler'] = "✅ SUCCESS"
        print("✅ 基础爬虫类导入成功")
    except Exception as e:
        results['base_crawler'] = f"❌ FAILED: {e}"
        print(f"❌ 基础爬虫类导入失败: {e}")
    
    # 测试4: 数据模型
    try:
        import model.m_xiaohongshu as xhs_models
        results['xhs_models'] = "✅ SUCCESS"
        print("✅ XHS数据模型导入成功")
    except Exception as e:
        results['xhs_models'] = f"❌ FAILED: {e}"
        print(f"❌ XHS数据模型导入失败: {e}")
    
    # 测试5: 配置模块
    try:
        import config
        results['config'] = "✅ SUCCESS"
        print("✅ 配置模块导入成功")
    except Exception as e:
        results['config'] = f"❌ FAILED: {e}"
        print(f"❌ 配置模块导入失败: {e}")
    
    return results

if __name__ == "__main__":
    print("开始测试MediaCrawler模块导入...")
    print(f"MediaCrawler路径: {mediacrawler_path}")
    print("=" * 50)
    
    results = test_imports()
    
    print("\n" + "=" * 50)
    print("测试结果总结:")
    for module, result in results.items():
        print(f"{module}: {result}")
    
    success_count = sum(1 for r in results.values() if "SUCCESS" in r)
    total_count = len(results)
    
    print(f"\n成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("🎉 所有模块导入成功！可以进行下一步。")
    else:
        print("⚠️  存在导入问题，需要进一步调试。")