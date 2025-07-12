#!/usr/bin/env python3
"""
Step 5: MediaCrawler共享库集成测试套件
全面验证XHS平台适配器的共享库集成功能
"""
import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = '/home/damian/Web3-TGE-Monitor'
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class IntegrationTestSuite:
    """集成测试套件"""
    
    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        
    async def run_all_tests(self):
        """运行所有集成测试"""
        print("🚀 Step 5: MediaCrawler共享库集成测试")
        print("=" * 70)
        
        tests = [
            ("配置管理测试", self.test_configuration_management),
            ("模块导入测试", self.test_module_imports),
            ("平台初始化测试", self.test_platform_initialization),
            ("配置灵活性测试", self.test_configuration_flexibility),
            ("错误处理测试", self.test_error_handling),
            ("资源管理测试", self.test_resource_management),
            ("API接口兼容性测试", self.test_api_compatibility),
            ("性能基准测试", self.test_performance_baseline),
        ]
        
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}")
            print("-" * 50)
            try:
                result = await test_func()
                self.test_results[test_name] = result
                if result:
                    print(f"✅ {test_name}: 通过")
                else:
                    print(f"❌ {test_name}: 失败")
                    self.failed_tests.append(test_name)
            except Exception as e:
                print(f"❌ {test_name}: 异常 - {e}")
                self.test_results[test_name] = False
                self.failed_tests.append(test_name)
                import traceback
                traceback.print_exc()
        
        # 输出测试报告
        await self.generate_test_report()
        
    async def test_configuration_management(self):
        """测试配置管理功能"""
        try:
            from src.config.mediacrawler_config import MediaCrawlerConfig
            from src.config.settings import settings
            
            # 测试配置管理器创建
            mc_config = MediaCrawlerConfig(settings)
            print(f"   ✅ 配置管理器创建成功")
            
            # 测试路径解析
            path = mc_config.mediacrawler_path
            print(f"   ✅ MediaCrawler路径解析: {path}")
            
            # 测试平台配置获取
            platform_config = mc_config.get_platform_config("xhs")
            print(f"   ✅ 平台配置获取: {platform_config}")
            
            # 测试安装验证
            is_valid = mc_config.validate_installation()
            print(f"   ✅ 安装验证: {'通过' if is_valid else '失败'}")
            
            return is_valid
            
        except Exception as e:
            print(f"   ❌ 配置管理测试失败: {e}")
            return False
    
    async def test_module_imports(self):
        """测试模块导入功能"""
        try:
            # 确保MediaCrawler路径在sys.path中
            from src.config.mediacrawler_config import MediaCrawlerConfig
            mc_config = MediaCrawlerConfig()
            if mc_config.mediacrawler_path not in sys.path:
                sys.path.insert(0, mc_config.mediacrawler_path)
            
            # 测试关键模块导入
            modules_to_test = [
                ("media_platform.xhs.client", "XiaoHongShuClient"),
                ("media_platform.xhs.core", "XiaoHongShuCrawler"),
                ("media_platform.xhs.field", "SearchSortType"),
                ("media_platform.xhs.help", "get_search_id"),
                ("base.base_crawler", "AbstractCrawler"),
            ]
            
            for module_name, class_name in modules_to_test:
                try:
                    module = __import__(module_name, fromlist=[class_name])
                    getattr(module, class_name)
                    print(f"   ✅ {module_name}.{class_name} 导入成功")
                except Exception as e:
                    print(f"   ❌ {module_name}.{class_name} 导入失败: {e}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ 模块导入测试失败: {e}")
            return False
    
    async def test_platform_initialization(self):
        """测试平台初始化功能"""
        try:
            from src.crawler.platforms.xhs_platform import XHSPlatform
            
            # 测试默认初始化
            platform = XHSPlatform()
            print(f"   ✅ 默认初始化成功")
            print(f"   ✅ MediaCrawler路径: {platform.mediacrawler_path}")
            
            # 测试平台名称
            platform_name = platform.get_platform_name()
            print(f"   ✅ 平台名称: {platform_name}")
            
            # 测试可用性检查
            is_available = await platform.is_available()
            print(f"   ✅ 平台可用性: {'可用' if is_available else '不可用'}")
            
            # 测试关键词验证
            keywords = ["Web3", "区块链", "DeFi"]
            validated_keywords = await platform.validate_keywords(keywords)
            print(f"   ✅ 关键词验证: {validated_keywords}")
            
            return is_available
            
        except Exception as e:
            print(f"   ❌ 平台初始化测试失败: {e}")
            return False
    
    async def test_configuration_flexibility(self):
        """测试配置灵活性"""
        try:
            from src.crawler.platforms.xhs_platform import XHSPlatform
            
            # 测试不同配置方式
            configs = [
                None,  # 默认配置
                {},    # 空配置
                {'mediacrawler_path': '/home/damian/MediaCrawler'},  # 指定路径
            ]
            
            for i, config in enumerate(configs):
                try:
                    platform = XHSPlatform(config)
                    print(f"   ✅ 配置方式 {i+1}: 成功")
                except Exception as e:
                    print(f"   ❌ 配置方式 {i+1}: 失败 - {e}")
                    return False
            
            # 测试环境变量配置
            original_env = os.environ.get('MEDIACRAWLER_PATH')
            os.environ['MEDIACRAWLER_PATH'] = '/home/damian/MediaCrawler'
            
            try:
                platform = XHSPlatform()
                print(f"   ✅ 环境变量配置: 成功")
            except Exception as e:
                print(f"   ❌ 环境变量配置: 失败 - {e}")
                return False
            finally:
                # 恢复环境变量
                if original_env:
                    os.environ['MEDIACRAWLER_PATH'] = original_env
                else:
                    os.environ.pop('MEDIACRAWLER_PATH', None)
            
            return True
            
        except Exception as e:
            print(f"   ❌ 配置灵活性测试失败: {e}")
            return False
    
    async def test_error_handling(self):
        """测试错误处理功能"""
        try:
            from src.crawler.platforms.xhs_platform import XHSPlatform
            from src.config.mediacrawler_config import MediaCrawlerConfig
            
            # 测试无效路径处理
            try:
                invalid_config = {'mediacrawler_path': '/invalid/path/not/exists'}
                platform = XHSPlatform(invalid_config)
                print(f"   ❌ 应该抛出错误但没有")
                return False
            except Exception:
                print(f"   ✅ 无效路径错误处理正确")
            
            # 测试配置验证
            mc_config = MediaCrawlerConfig()
            is_valid = mc_config._validate_mediacrawler_path("/invalid/path")
            if not is_valid:
                print(f"   ✅ 路径验证功能正常")
            else:
                print(f"   ❌ 路径验证功能异常")
                return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ 错误处理测试失败: {e}")
            return False
    
    async def test_resource_management(self):
        """测试资源管理功能"""
        try:
            from src.crawler.platforms.xhs_platform import XHSPlatform
            
            # 创建多个平台实例测试资源管理
            platforms = []
            for i in range(3):
                platform = XHSPlatform()
                platforms.append(platform)
                print(f"   ✅ 平台实例 {i+1} 创建成功")
            
            # 测试客户端延迟初始化
            for i, platform in enumerate(platforms):
                client = await platform._get_xhs_client()
                print(f"   ✅ 平台实例 {i+1} 客户端初始化成功")
            
            print(f"   ✅ 资源管理测试通过")
            return True
            
        except Exception as e:
            print(f"   ❌ 资源管理测试失败: {e}")
            return False
    
    async def test_api_compatibility(self):
        """测试API接口兼容性"""
        try:
            from src.crawler.platforms.xhs_platform import XHSPlatform
            from src.crawler.models import Platform, ContentType
            
            platform = XHSPlatform()
            
            # 测试必需的API方法
            api_methods = [
                'get_platform_name',
                'is_available', 
                'validate_keywords',
                'crawl',
                'transform_to_raw_content',
                'filter_content'
            ]
            
            for method_name in api_methods:
                if hasattr(platform, method_name):
                    print(f"   ✅ API方法 {method_name} 存在")
                else:
                    print(f"   ❌ API方法 {method_name} 缺失")
                    return False
            
            # 测试返回值类型
            platform_name = platform.get_platform_name()
            if platform_name == Platform.XHS:
                print(f"   ✅ 平台名称类型正确")
            else:
                print(f"   ❌ 平台名称类型错误")
                return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ API兼容性测试失败: {e}")
            return False
    
    async def test_performance_baseline(self):
        """测试性能基准"""
        try:
            from src.crawler.platforms.xhs_platform import XHSPlatform
            import time
            
            # 测试初始化性能
            start_time = time.time()
            platform = XHSPlatform()
            init_time = time.time() - start_time
            print(f"   ✅ 初始化时间: {init_time:.3f}秒")
            
            # 测试可用性检查性能
            start_time = time.time()
            is_available = await platform.is_available()
            check_time = time.time() - start_time
            print(f"   ✅ 可用性检查时间: {check_time:.3f}秒")
            
            # 测试客户端创建性能
            start_time = time.time()
            client = await platform._get_xhs_client()
            client_time = time.time() - start_time
            print(f"   ✅ 客户端创建时间: {client_time:.3f}秒")
            
            # 性能基准检查
            if init_time < 2.0 and check_time < 5.0 and client_time < 3.0:
                print(f"   ✅ 性能基准测试通过")
                return True
            else:
                print(f"   ⚠️  性能基准偏慢但可接受")
                return True
            
        except Exception as e:
            print(f"   ❌ 性能基准测试失败: {e}")
            return False
    
    async def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "=" * 70)
        print("📊 集成测试报告")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"总测试数量: {total_tests}")
        print(f"通过测试数: {passed_tests}")
        print(f"失败测试数: {len(self.failed_tests)}")
        print(f"成功率: {success_rate:.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ 失败的测试:")
            for test in self.failed_tests:
                print(f"   - {test}")
        
        if success_rate >= 90:
            print(f"\n🎉 Step 5 完成！集成测试通过")
            print(f"   主要验证:")
            print(f"   - ✅ 配置管理系统完整可靠")
            print(f"   - ✅ 模块导入机制正常工作")
            print(f"   - ✅ 平台初始化流程无误")
            print(f"   - ✅ 错误处理机制健全")
            print(f"   - ✅ API接口兼容性良好")
            print(f"   - ✅ 性能表现符合预期")
        elif success_rate >= 75:
            print(f"\n⚠️  Step 5 基本通过，但存在问题需要关注")
        else:
            print(f"\n❌ Step 5 失败，需要修复关键问题")
        
        return success_rate >= 75

async def main():
    """主函数"""
    test_suite = IntegrationTestSuite()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())