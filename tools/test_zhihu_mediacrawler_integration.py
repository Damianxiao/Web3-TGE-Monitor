#!/usr/bin/env python3
"""
知乎MediaCrawler真实集成测试
Phase 2 真实集成测试 - 使用MediaCrawler原生实现

验证MediaCrawler适配器的完整爬取流程
"""
import asyncio
import sys
import os
from typing import Dict, Any, List

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

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


class ZhihuMediaCrawlerIntegrationTester:
    """知乎MediaCrawler集成测试器"""
    
    def __init__(self):
        from crawler.platforms.zhihu_platform import ZhihuPlatform
        
        self.cookie = os.getenv("ZHIHU_COOKIE", "")
        self.platform = ZhihuPlatform()
        
    async def test_platform_availability(self) -> Dict[str, Any]:
        """测试平台可用性"""
        logger.info("🔍 测试知乎平台可用性...")
        
        try:
            is_available = await self.platform.is_available()
            
            if is_available:
                logger.info("✅ 知乎平台可用 (MediaCrawler)")
                return {
                    'success': True,
                    'message': '知乎平台通过MediaCrawler验证可用'
                }
            else:
                logger.error("❌ 知乎平台不可用")
                return {
                    'success': False,
                    'message': '知乎平台不可用，检查Cookie配置'
                }
                
        except Exception as e:
            logger.error("❌ 平台可用性测试失败", error=str(e))
            return {
                'success': False,
                'message': f'平台可用性测试异常: {str(e)}'
            }
    
    async def test_mediacrawler_adapter(self) -> Dict[str, Any]:
        """测试MediaCrawler适配器"""
        logger.info("🔧 测试MediaCrawler适配器...")
        
        try:
            # 获取适配器
            adapter = await self.platform._get_mediacrawler_adapter()
            
            if not adapter:
                return {
                    'success': False,
                    'message': 'MediaCrawler适配器创建失败'
                }
            
            # 测试ping
            ping_result = await adapter.ping()
            
            if ping_result:
                logger.info("✅ MediaCrawler适配器工作正常")
                return {
                    'success': True,
                    'message': 'MediaCrawler适配器连接成功，已启用完整集成'
                }
            else:
                logger.error("❌ MediaCrawler适配器ping失败")
                return {
                    'success': False,
                    'message': 'MediaCrawler适配器连接失败'
                }
                
        except Exception as e:
            logger.error("❌ MediaCrawler适配器测试失败", error=str(e))
            return {
                'success': False,
                'message': f'适配器测试异常: {str(e)}'
            }
    
    async def test_search_functionality(self) -> Dict[str, Any]:
        """测试搜索功能"""
        logger.info("🔍 测试知乎搜索功能...")
        
        test_keywords = ["Web3", "DeFi", "区块链投资"]
        results = {
            'success': False,
            'total_results': 0,
            'keyword_results': {},
            'content_types': {},
            'sample_data': []
        }
        
        try:
            for keyword in test_keywords:
                logger.info(f"📝 搜索关键词: {keyword}")
                
                try:
                    # 使用平台的crawl方法
                    search_results = await self.platform.crawl(
                        keywords=[keyword],
                        max_count=10
                    )
                    
                    results['keyword_results'][keyword] = len(search_results)
                    results['total_results'] += len(search_results)
                    
                    # 分析内容类型
                    for content in search_results:
                        content_type = content.content_type.value
                        results['content_types'][content_type] = \
                            results['content_types'].get(content_type, 0) + 1
                        
                        # 保存前3个样本
                        if len(results['sample_data']) < 3:
                            results['sample_data'].append({
                                'keyword': keyword,
                                'content_id': content.content_id,
                                'content_type': content_type,
                                'title': content.title[:50],
                                'author': content.author_name,
                                'like_count': content.like_count,
                                'professional_score': content.platform_metadata.get('professional_score', 0)
                            })
                    
                    logger.info(f"✅ '{keyword}' 搜索成功: {len(search_results)} 条结果")
                    
                except Exception as e:
                    logger.error(f"❌ '{keyword}' 搜索失败", error=str(e))
                    results['keyword_results'][keyword] = 0
                
                # 延迟避免过快请求
                await asyncio.sleep(2)
            
            if results['total_results'] > 0:
                results['success'] = True
                results['message'] = f'搜索成功，共获得 {results["total_results"]} 条结果'
                logger.info("✅ 知乎搜索功能测试成功")
            else:
                results['message'] = '搜索未获得任何结果'
                logger.warning("⚠️ 搜索未获得结果")
            
            return results
            
        except Exception as e:
            logger.error("❌ 搜索功能测试失败", error=str(e))
            results['message'] = f'搜索功能测试异常: {str(e)}'
            return results
    
    async def test_data_conversion(self, sample_data: List[Dict]) -> Dict[str, Any]:
        """测试数据转换功能"""
        logger.info("🔧 测试数据转换功能...")
        
        if not sample_data:
            return {
                'success': False,
                'message': '无样本数据进行转换测试'
            }
        
        conversion_results = {
            'success': True,
            'sample_count': len(sample_data),
            'content_types_found': set(),
            'professional_score_range': {'min': 1.0, 'max': 0.0, 'avg': 0.0},
            'quality_analysis': {
                'high_quality': 0,
                'medium_quality': 0,
                'low_quality': 0
            }
        }
        
        total_score = 0.0
        
        for sample in sample_data:
            # 记录内容类型
            conversion_results['content_types_found'].add(sample['content_type'])
            
            # 分析专业度分数
            prof_score = sample.get('professional_score', 0)
            total_score += prof_score
            
            conversion_results['professional_score_range']['min'] = min(
                conversion_results['professional_score_range']['min'], prof_score
            )
            conversion_results['professional_score_range']['max'] = max(
                conversion_results['professional_score_range']['max'], prof_score
            )
            
            # 质量分析
            if prof_score >= 0.6:
                conversion_results['quality_analysis']['high_quality'] += 1
            elif prof_score >= 0.3:
                conversion_results['quality_analysis']['medium_quality'] += 1
            else:
                conversion_results['quality_analysis']['low_quality'] += 1
        
        conversion_results['professional_score_range']['avg'] = total_score / len(sample_data)
        conversion_results['content_types_found'] = list(conversion_results['content_types_found'])
        
        logger.info("✅ 数据转换功能测试完成")
        conversion_results['message'] = f'成功分析 {len(sample_data)} 个样本，发现 {len(conversion_results["content_types_found"])} 种内容类型'
        
        return conversion_results
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合集成测试"""
        logger.info("🚀 开始知乎MediaCrawler综合集成测试...")
        
        test_results = {
            'availability_test': {},
            'adapter_test': {},
            'search_test': {},
            'conversion_test': {},
            'overall_success': False
        }
        
        # 1. 平台可用性测试
        logger.info("=" * 50)
        logger.info("第1步: 平台可用性测试")
        availability_result = await self.test_platform_availability()
        test_results['availability_test'] = availability_result
        
        if not availability_result['success']:
            logger.error("❌ 平台不可用，停止后续测试")
            return test_results
        
        # 2. MediaCrawler适配器测试
        logger.info("=" * 50)
        logger.info("第2步: MediaCrawler适配器测试")
        adapter_result = await self.test_mediacrawler_adapter()
        test_results['adapter_test'] = adapter_result
        
        if not adapter_result['success']:
            logger.error("❌ 适配器不可用，停止后续测试")
            return test_results
        
        # 3. 搜索功能测试
        logger.info("=" * 50)
        logger.info("第3步: 搜索功能测试")
        search_result = await self.test_search_functionality()
        test_results['search_test'] = search_result
        
        # 4. 数据转换测试
        logger.info("=" * 50)
        logger.info("第4步: 数据转换测试")
        conversion_result = await self.test_data_conversion(search_result.get('sample_data', []))
        test_results['conversion_test'] = conversion_result
        
        # 综合评估
        test_results['overall_success'] = (
            availability_result['success'] and
            adapter_result['success'] and
            search_result['success'] and
            conversion_result['success']
        )
        
        # 清理资源
        try:
            await self.platform.cleanup()
            logger.info("测试资源清理完成")
        except Exception as e:
            logger.warning(f"清理资源时出错: {e}")
        
        return test_results


async def main():
    """主函数"""
    logger.info("🎯 Phase 2 知乎MediaCrawler真实集成测试开始")
    
    tester = ZhihuMediaCrawlerIntegrationTester()
    results = await tester.run_comprehensive_test()
    
    print("\n" + "="*80)
    print("📊 知乎MediaCrawler真实集成测试报告")
    print("="*80)
    
    # 平台可用性测试结果
    print(f"\n🔍 平台可用性测试:")
    availability = results.get('availability_test', {})
    status = "✅ 通过" if availability.get('success') else "❌ 失败"
    print(f"  状态: {status}")
    print(f"  信息: {availability.get('message', 'N/A')}")
    
    # 适配器测试结果
    print(f"\n🔧 MediaCrawler适配器测试:")
    adapter = results.get('adapter_test', {})
    status = "✅ 通过" if adapter.get('success') else "❌ 失败"
    print(f"  状态: {status}")
    print(f"  信息: {adapter.get('message', 'N/A')}")
    
    # 搜索功能测试结果
    print(f"\n🔍 搜索功能测试:")
    search = results.get('search_test', {})
    status = "✅ 通过" if search.get('success') else "❌ 失败"
    print(f"  状态: {status}")
    print(f"  总结果数: {search.get('total_results', 0)}")
    print(f"  关键词结果: {search.get('keyword_results', {})}")
    print(f"  内容类型: {search.get('content_types', {})}")
    
    # 数据转换测试结果
    print(f"\n🔧 数据转换测试:")
    conversion = results.get('conversion_test', {})
    status = "✅ 通过" if conversion.get('success') else "❌ 失败"
    print(f"  状态: {status}")
    if conversion.get('success'):
        print(f"  样本数量: {conversion.get('sample_count', 0)}")
        print(f"  内容类型: {conversion.get('content_types_found', [])}")
        prof_range = conversion.get('professional_score_range', {})
        print(f"  专业度范围: {prof_range.get('min', 0):.3f} ~ {prof_range.get('max', 0):.3f} (平均: {prof_range.get('avg', 0):.3f})")
        quality = conversion.get('quality_analysis', {})
        print(f"  质量分布: 高质量({quality.get('high_quality', 0)}) 中质量({quality.get('medium_quality', 0)}) 低质量({quality.get('low_quality', 0)})")
    
    # 综合评估
    print(f"\n📈 综合评估:")
    overall_status = "✅ 通过" if results.get('overall_success') else "❌ 失败"
    print(f"  最终结果: {overall_status}")
    
    print("\n" + "="*80)
    
    if results.get('overall_success'):
        print("🎉 知乎MediaCrawler集成测试成功！Phase 2 完全验证通过。")
        return 0
    else:
        print("💥 知乎MediaCrawler集成测试失败！需要检查配置和实现。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)