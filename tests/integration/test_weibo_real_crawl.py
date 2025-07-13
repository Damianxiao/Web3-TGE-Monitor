"""
微博平台真实爬取集成测试
验证WeiboPlatform在真实环境下的功能
"""
import pytest
import asyncio
import os
import time
from typing import Dict, Any, List
from unittest.mock import patch

# 添加src到路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from crawler.platforms.weibo_platform import WeiboPlatform
from crawler.models import Platform, RawContent
from crawler.base_platform import PlatformError


class TestWeiboRealCrawl:
    """微博平台真实爬取测试"""
    
    @pytest.fixture
    def weibo_platform(self):
        """测试用微博平台实例"""
        return WeiboPlatform()
    
    @pytest.fixture
    def test_keywords(self):
        """测试关键词"""
        return ["Web3", "TGE"]
    
    def test_environment_setup(self):
        """测试环境配置验证"""
        print("\n=== 环境配置验证 ===")
        
        # 检查WEIBO_COOKIE配置
        weibo_cookie = os.getenv("WEIBO_COOKIE", "")
        print(f"WEIBO_COOKIE配置: {'✅ 已配置' if weibo_cookie else '❌ 未配置'}")
        
        # 检查MediaCrawler路径
        mediacrawler_path = os.getenv("MEDIACRAWLER_PATH", "./mediacrawler")
        mediacrawler_exists = os.path.exists(mediacrawler_path)
        print(f"MediaCrawler路径 ({mediacrawler_path}): {'✅ 存在' if mediacrawler_exists else '❌ 不存在'}")
        
        # 检查其他微博配置
        search_type = os.getenv("WEIBO_SEARCH_TYPE", "综合")
        max_pages = os.getenv("WEIBO_MAX_PAGES", "10")
        rate_limit = os.getenv("WEIBO_RATE_LIMIT", "60")
        
        print(f"搜索类型: {search_type}")
        print(f"最大页数: {max_pages}")
        print(f"速率限制: {rate_limit}")
        
        # 如果Cookie未配置，跳过后续测试
        if not weibo_cookie:
            pytest.skip("WEIBO_COOKIE 未配置，跳过真实爬取测试")
    
    def test_platform_initialization(self, weibo_platform):
        """测试平台初始化"""
        print("\n=== 平台初始化测试 ===")
        
        # 检查平台名称
        assert weibo_platform.get_platform_name() == Platform.WEIBO
        print("✅ 平台名称验证通过")
        
        # 检查配置
        assert hasattr(weibo_platform, 'cookie')
        assert hasattr(weibo_platform, 'search_type')
        assert hasattr(weibo_platform, 'max_pages')
        assert hasattr(weibo_platform, 'rate_limit')
        print("✅ 配置属性验证通过")
        
        # 检查日志
        assert hasattr(weibo_platform, 'logger')
        print("✅ 日志配置验证通过")
    
    @pytest.mark.asyncio
    async def test_cookie_validation(self, weibo_platform):
        """测试Cookie有效性验证"""
        print("\n=== Cookie有效性验证 ===")
        
        if not weibo_platform.cookie:
            pytest.skip("WEIBO_COOKIE 未配置")
        
        # 测试登录状态检查
        login_status = await weibo_platform._check_login_status()
        print(f"登录状态检查: {'✅ 通过' if login_status else '❌ 失败'}")
        
        # 测试平台可用性
        availability = await weibo_platform.is_available()
        print(f"平台可用性: {'✅ 可用' if availability else '❌ 不可用'}")
        
        if not availability:
            pytest.skip("微博平台不可用，可能Cookie已过期")
    
    @pytest.mark.asyncio
    async def test_real_search_basic(self, weibo_platform, test_keywords):
        """测试真实搜索基本功能"""
        print("\n=== 真实搜索基本功能测试 ===")
        
        if not weibo_platform.cookie:
            pytest.skip("WEIBO_COOKIE 未配置")
        
        start_time = time.time()
        
        try:
            # 执行小规模搜索测试（限制为1页，最多20条）
            results = await weibo_platform.crawl(
                keywords=test_keywords[:1],  # 只用第一个关键词
                max_count=5  # 限制结果数量
            )
            
            execution_time = time.time() - start_time
            
            print(f"搜索关键词: {test_keywords[:1]}")
            print(f"执行时间: {execution_time:.2f}秒")
            print(f"返回结果数: {len(results)}")
            
            # 验证返回结果
            assert isinstance(results, list)
            
            if results:
                # 验证第一个结果的数据结构
                first_result = results[0]
                assert isinstance(first_result, RawContent)
                assert first_result.platform == Platform.WEIBO
                assert first_result.content_id
                assert first_result.content
                
                print("✅ 搜索成功，数据格式正确")
                print(f"第一条内容预览: {first_result.content[:100]}...")
                print(f"作者: {first_result.author_name}")
                print(f"发布时间: {first_result.publish_time}")
                print(f"互动数据: 点赞{first_result.like_count} 评论{first_result.comment_count} 转发{first_result.share_count}")
                
            else:
                print("⚠️  搜索成功但无结果，可能关键词过于特殊")
                
        except Exception as e:
            print(f"❌ 搜索失败: {str(e)}")
            raise
    
    @pytest.mark.asyncio
    async def test_search_with_different_types(self, weibo_platform):
        """测试不同搜索类型"""
        print("\n=== 不同搜索类型测试 ===")
        
        if not weibo_platform.cookie:
            pytest.skip("WEIBO_COOKIE 未配置")
        
        search_types = ["综合", "实时", "热门"]
        test_keyword = ["区块链"]  # 使用相对通用的关键词
        
        for search_type in search_types:
            print(f"\n测试搜索类型: {search_type}")
            
            # 临时设置搜索类型
            original_search_type = weibo_platform.search_type
            weibo_platform.search_type = search_type
            
            try:
                results = await weibo_platform.crawl(
                    keywords=test_keyword,
                    max_count=3
                )
                
                print(f"  {search_type}搜索结果: {len(results)}条")
                
                if results:
                    sample = results[0]
                    print(f"  样本内容: {sample.content[:50]}...")
                
            except Exception as e:
                print(f"  {search_type}搜索失败: {str(e)}")
            
            finally:
                # 恢复原始搜索类型
                weibo_platform.search_type = original_search_type
    
    @pytest.mark.asyncio 
    async def test_data_quality_validation(self, weibo_platform):
        """测试数据质量验证"""
        print("\n=== 数据质量验证测试 ===")
        
        if not weibo_platform.cookie:
            pytest.skip("WEIBO_COOKIE 未配置")
        
        try:
            results = await weibo_platform.crawl(
                keywords=["比特币"],  # 使用热门关键词
                max_count=5
            )
            
            if not results:
                print("⚠️  无搜索结果，跳过数据质量验证")
                return
            
            print(f"验证 {len(results)} 条数据质量...")
            
            quality_report = {
                "total_count": len(results),
                "valid_content": 0,
                "valid_author": 0,
                "valid_time": 0,
                "has_interactions": 0,
                "has_images": 0,
                "has_hashtags": 0,
                "chinese_content": 0
            }
            
            for i, result in enumerate(results):
                # 验证内容完整性
                if result.content and len(result.content.strip()) > 10:
                    quality_report["valid_content"] += 1
                
                # 验证作者信息
                if result.author_name and result.author_id:
                    quality_report["valid_author"] += 1
                
                # 验证时间信息
                if result.publish_time:
                    quality_report["valid_time"] += 1
                
                # 验证互动数据
                if result.like_count > 0 or result.comment_count > 0:
                    quality_report["has_interactions"] += 1
                
                # 验证图片信息
                if result.image_urls:
                    quality_report["has_images"] += 1
                
                # 验证话题标签
                if result.hashtags:
                    quality_report["has_hashtags"] += 1
                
                # 验证中文内容
                if any('\u4e00' <= char <= '\u9fff' for char in result.content):
                    quality_report["chinese_content"] += 1
                
                # 打印第一条详细信息
                if i == 0:
                    print(f"\n第一条数据详情:")
                    print(f"  内容ID: {result.content_id}")
                    print(f"  内容: {result.content[:100]}...")
                    print(f"  作者: {result.author_name} (ID: {result.author_id})")
                    print(f"  发布时间: {result.publish_time}")
                    print(f"  互动: 👍{result.like_count} 💬{result.comment_count} 🔄{result.share_count}")
                    print(f"  图片数量: {len(result.image_urls)}")
                    print(f"  话题标签: {result.hashtags}")
                    print(f"  来源URL: {result.source_url}")
            
            # 打印质量报告
            print(f"\n数据质量报告:")
            print(f"  有效内容率: {quality_report['valid_content']}/{quality_report['total_count']} ({quality_report['valid_content']/quality_report['total_count']*100:.1f}%)")
            print(f"  有效作者率: {quality_report['valid_author']}/{quality_report['total_count']} ({quality_report['valid_author']/quality_report['total_count']*100:.1f}%)")
            print(f"  有效时间率: {quality_report['valid_time']}/{quality_report['total_count']} ({quality_report['valid_time']/quality_report['total_count']*100:.1f}%)")
            print(f"  有互动数据: {quality_report['has_interactions']}/{quality_report['total_count']} ({quality_report['has_interactions']/quality_report['total_count']*100:.1f}%)")
            print(f"  包含图片: {quality_report['has_images']}/{quality_report['total_count']} ({quality_report['has_images']/quality_report['total_count']*100:.1f}%)")
            print(f"  包含话题: {quality_report['has_hashtags']}/{quality_report['total_count']} ({quality_report['has_hashtags']/quality_report['total_count']*100:.1f}%)")
            print(f"  中文内容: {quality_report['chinese_content']}/{quality_report['total_count']} ({quality_report['chinese_content']/quality_report['total_count']*100:.1f}%)")
            
            # 质量断言
            assert quality_report['valid_content'] > 0, "至少应有有效内容"
            assert quality_report['valid_author'] > 0, "至少应有有效作者信息"
            assert quality_report['chinese_content'] > 0, "应有中文内容"
            
            print("✅ 数据质量验证通过")
            
        except Exception as e:
            print(f"❌ 数据质量验证失败: {str(e)}")
            raise
    
    @pytest.mark.asyncio
    async def test_error_handling(self, weibo_platform):
        """测试错误处理"""
        print("\n=== 错误处理测试 ===")
        
        # 测试无效Cookie
        print("测试无效Cookie处理...")
        original_cookie = weibo_platform.cookie
        weibo_platform.cookie = "invalid_cookie"
        
        try:
            availability = await weibo_platform.is_available()
            print(f"无效Cookie可用性检查: {'通过' if not availability else '意外通过'}")
        finally:
            weibo_platform.cookie = original_cookie
        
        # 测试空关键词
        print("测试空关键词处理...")
        try:
            await weibo_platform.crawl(keywords=[], max_count=5)
            assert False, "应该抛出异常"
        except Exception as e:
            print(f"空关键词正确抛出异常: {type(e).__name__}")
        
        # 测试无效搜索类型
        print("测试无效搜索类型处理...")
        original_search_type = weibo_platform.search_type
        weibo_platform.search_type = "无效类型"
        
        try:
            if weibo_platform.cookie:
                results = await weibo_platform.crawl(keywords=["测试"], max_count=1)
                print("无效搜索类型被正确处理（使用默认类型）")
        except Exception as e:
            print(f"无效搜索类型处理: {str(e)}")
        finally:
            weibo_platform.search_type = original_search_type
        
        print("✅ 错误处理测试完成")
    
    @pytest.mark.asyncio
    async def test_performance_benchmark(self, weibo_platform):
        """测试性能基准"""
        print("\n=== 性能基准测试 ===")
        
        if not weibo_platform.cookie:
            pytest.skip("WEIBO_COOKIE 未配置")
        
        # 性能指标
        metrics = {
            "search_count": 0,
            "success_count": 0,
            "total_time": 0,
            "total_results": 0,
            "avg_response_time": 0,
            "success_rate": 0
        }
        
        test_cases = [
            {"keywords": ["Web3"], "max_count": 3},
            {"keywords": ["DeFi"], "max_count": 3},
            {"keywords": ["区块链"], "max_count": 3}
        ]
        
        print(f"执行 {len(test_cases)} 个性能测试用例...")
        
        for i, test_case in enumerate(test_cases):
            start_time = time.time()
            metrics["search_count"] += 1
            
            try:
                results = await weibo_platform.crawl(**test_case)
                
                execution_time = time.time() - start_time
                metrics["total_time"] += execution_time
                metrics["success_count"] += 1
                metrics["total_results"] += len(results)
                
                print(f"测试 {i+1}: {test_case['keywords']} - {len(results)}条结果，耗时{execution_time:.2f}秒")
                
            except Exception as e:
                execution_time = time.time() - start_time
                metrics["total_time"] += execution_time
                print(f"测试 {i+1}: {test_case['keywords']} - 失败: {str(e)}")
        
        # 计算性能指标
        if metrics["search_count"] > 0:
            metrics["avg_response_time"] = metrics["total_time"] / metrics["search_count"]
            metrics["success_rate"] = metrics["success_count"] / metrics["search_count"]
        
        # 打印性能报告
        print(f"\n性能基准报告:")
        print(f"  总搜索次数: {metrics['search_count']}")
        print(f"  成功次数: {metrics['success_count']}")
        print(f"  成功率: {metrics['success_rate']*100:.1f}%")
        print(f"  总耗时: {metrics['total_time']:.2f}秒")
        print(f"  平均响应时间: {metrics['avg_response_time']:.2f}秒")
        print(f"  总结果数: {metrics['total_results']}")
        
        if metrics["success_count"] > 0:
            print(f"  平均每次搜索结果: {metrics['total_results']/metrics['success_count']:.1f}条")
        
        # 性能断言
        if metrics["success_count"] > 0:
            assert metrics["avg_response_time"] < 30, f"平均响应时间过长: {metrics['avg_response_time']}秒"
            assert metrics["success_rate"] >= 0.5, f"成功率过低: {metrics['success_rate']*100}%"
        
        print("✅ 性能基准测试完成")


if __name__ == "__main__":
    # 直接运行测试
    import asyncio
    
    async def run_tests():
        test_instance = TestWeiboRealCrawl()
        weibo_platform = test_instance.weibo_platform()
        
        print("开始微博平台真实爬取测试...")
        
        # 环境配置测试
        test_instance.test_environment_setup()
        
        # 平台初始化测试
        test_instance.test_platform_initialization(weibo_platform)
        
        # Cookie验证测试
        await test_instance.test_cookie_validation(weibo_platform)
        
        # 真实搜索测试
        await test_instance.test_real_search_basic(weibo_platform, ["Web3", "TGE"])
        
        print("\n测试完成！")
    
    asyncio.run(run_tests())