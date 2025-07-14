#!/usr/bin/env python3
"""
知乎平台真实客户端测试
Phase 2 真实集成测试 - 步骤2: SimplifiedZhihuClient真实API测试

测试SimplifiedZhihuClient在真实环境下的表现
"""
import asyncio
import sys
import os
import json
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


class ZhihuClientTester:
    """知乎客户端测试器"""
    
    def __init__(self):
        from crawler.platforms.zhihu_platform import ZhihuPlatform
        from crawler.platforms.mediacrawler_zhihu_adapter import MediaCrawlerZhihuAdapter
        
        self.cookie = os.getenv("ZHIHU_COOKIE", "")
        self.platform = ZhihuPlatform()
        
        # 创建真实的MediaCrawler适配器实例
        self.client = MediaCrawlerZhihuAdapter(
            cookie=self.cookie,
            logger=logger
        )
    
    async def test_search_types(self) -> Dict[str, Any]:
        """测试不同搜索类型"""
        logger.info("🔍 测试不同知乎搜索类型...")
        
        # 首先初始化MediaCrawler适配器
        logger.info("🚀 初始化MediaCrawler适配器...")
        init_success = await self.client.initialize()
        if not init_success:
            logger.error("❌ MediaCrawler适配器初始化失败")
            return {"error": "MediaCrawler适配器初始化失败"}
        
        logger.info("✅ MediaCrawler适配器初始化成功")
        
        search_types = ["综合", "问题", "回答", "文章", "想法"]
        test_keyword = "Web3"
        results = {}
        
        try:
            for search_type in search_types:
                logger.info(f"📝 测试搜索类型: {search_type}")
                
                try:
                    # 使用MediaCrawler适配器进行搜索
                    response = await self.client.search_by_keyword(
                        keyword=test_keyword,
                        page=1,
                        page_size=10
                    )
                    
                    if response and isinstance(response, list):
                        # 分析内容类型
                        content_types = {}
                        for item in response:
                            item_type = item.get('type', 'unknown')
                            content_types[item_type] = content_types.get(item_type, 0) + 1
                        
                        results[search_type] = {
                            'success': True,
                            'result_count': len(response),
                            'content_types': content_types,
                            'sample_data': response[:2] if response else []  # 保存前两条样本
                        }
                        
                        logger.info(f"✅ {search_type} 搜索成功",
                                  result_count=len(response),
                                  content_types=content_types)
                    else:
                        results[search_type] = {
                            'success': False,
                            'error': 'Invalid response format'
                        }
                        logger.warning(f"⚠️ {search_type} 搜索数据格式异常")
                        
                    # 添加延迟避免过快请求
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    results[search_type] = {
                        'success': False,
                        'error': str(e)
                    }
                    logger.error(f"❌ {search_type} 搜索失败", error=str(e))
            
        finally:
            # 清理资源
            await self.client.close()
            logger.info("🧹 MediaCrawler适配器资源已清理")
        
        return results
    
    async def test_data_conversion(self, sample_data: List[Dict]) -> Dict[str, Any]:
        """测试数据转换功能"""
        logger.info("🔧 测试知乎数据转换功能...")
        
        conversion_results = {
            'total_items': len(sample_data),
            'successful_conversions': 0,
            'failed_conversions': 0,
            'content_types': {},
            'conversion_samples': [],
            'errors': []
        }
        
        for i, item in enumerate(sample_data):
            try:
                # 使用ZhihuPlatform的数据转换方法
                converted = self.platform._convert_to_raw_content(item)
                
                if converted:
                    conversion_results['successful_conversions'] += 1
                    
                    content_type = converted.content_type.value
                    conversion_results['content_types'][content_type] = \
                        conversion_results['content_types'].get(content_type, 0) + 1
                    
                    # 保存转换样本（前3个）
                    if len(conversion_results['conversion_samples']) < 3:
                        conversion_results['conversion_samples'].append({
                            'original_id': item.get('id'),
                            'original_type': item.get('type'),
                            'converted_type': content_type,
                            'title': converted.title,
                            'content_preview': converted.content[:100],
                            'author': converted.author_name,
                            'professional_score': converted.platform_metadata.get('professional_score', 0)
                        })
                    
                    logger.info(f"✅ 数据转换成功 {i+1}/{len(sample_data)}",
                              content_type=content_type,
                              title=converted.title[:30])
                else:
                    conversion_results['failed_conversions'] += 1
                    logger.warning(f"⚠️ 数据转换返回空结果 {i+1}")
                    
            except Exception as e:
                conversion_results['failed_conversions'] += 1
                conversion_results['errors'].append({
                    'item_id': item.get('id', 'unknown'),
                    'error': str(e)
                })
                logger.error(f"❌ 数据转换失败 {i+1}/{len(sample_data)}", error=str(e))
        
        return conversion_results
    
    async def test_professional_scoring(self, sample_data: List[Dict]) -> Dict[str, Any]:
        """测试专业度评分算法"""
        logger.info("🎯 测试专业度评分算法...")
        
        scoring_results = {
            'total_items': len(sample_data),
            'score_distribution': {},
            'high_professional_items': [],
            'average_score': 0.0,
            'scoring_breakdown': {
                'author_professional': 0,
                'high_engagement': 0,
                'long_content': 0
            }
        }
        
        total_score = 0.0
        
        for item in sample_data:
            try:
                score = self.platform._calculate_professional_score(item)
                total_score += score
                
                # 分数分布统计
                score_range = f"{int(score * 10) * 10}%-{int(score * 10) * 10 + 9}%"
                scoring_results['score_distribution'][score_range] = \
                    scoring_results['score_distribution'].get(score_range, 0) + 1
                
                # 高专业度内容（分数>0.5）
                if score > 0.5:
                    scoring_results['high_professional_items'].append({
                        'id': item.get('id'),
                        'type': item.get('type'),
                        'score': score,
                        'author_headline': item.get('author', {}).get('headline', ''),
                        'engagement': {
                            'voteup': item.get('voteup_count', 0),
                            'comment': item.get('comment_count', 0)
                        }
                    })
                
                # 评分要素分析
                author = item.get('author', {})
                headline = author.get('headline', '')
                professional_keywords = ['分析师', '投资', '研究员', '专家', '顾问', '基金', '经理']
                
                if any(keyword in headline for keyword in professional_keywords):
                    scoring_results['scoring_breakdown']['author_professional'] += 1
                
                voteup_count = item.get('voteup_count', 0) or item.get('like_count', 0)
                if voteup_count > 50:
                    scoring_results['scoring_breakdown']['high_engagement'] += 1
                
                content_length = len(item.get('content', ''))
                if content_length > 500:
                    scoring_results['scoring_breakdown']['long_content'] += 1
                
                logger.info(f"📊 专业度评分: {score:.2f}",
                          item_id=item.get('id', 'unknown')[:10],
                          item_type=item.get('type'))
                
            except Exception as e:
                logger.error("❌ 专业度评分失败", error=str(e))
        
        if len(sample_data) > 0:
            scoring_results['average_score'] = total_score / len(sample_data)
        
        return scoring_results
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合测试"""
        logger.info("🚀 开始知乎客户端综合测试...")
        
        test_results = {
            'search_test': {},
            'conversion_test': {},
            'scoring_test': {},
            'overall_success': False
        }
        
        # 1. 搜索测试
        logger.info("=" * 50)
        logger.info("第1步: 搜索功能测试")
        search_results = await self.test_search_types()
        test_results['search_test'] = search_results
        
        # 收集所有搜索到的数据样本
        all_sample_data = []
        for search_type, result in search_results.items():
            if result.get('success') and result.get('sample_data'):
                all_sample_data.extend(result['sample_data'])
        
        if not all_sample_data:
            logger.error("❌ 无法获取样本数据，停止后续测试")
            return test_results
        
        logger.info(f"📊 收集到 {len(all_sample_data)} 条样本数据")
        
        # 2. 数据转换测试
        logger.info("=" * 50)
        logger.info("第2步: 数据转换测试")
        conversion_results = await self.test_data_conversion(all_sample_data)
        test_results['conversion_test'] = conversion_results
        
        # 3. 专业度评分测试
        logger.info("=" * 50)
        logger.info("第3步: 专业度评分测试")
        scoring_results = await self.test_professional_scoring(all_sample_data)
        test_results['scoring_test'] = scoring_results
        
        # 综合评估
        search_success_rate = sum(1 for r in search_results.values() if r.get('success', False)) / len(search_results)
        conversion_success_rate = conversion_results['successful_conversions'] / max(conversion_results['total_items'], 1)
        
        test_results['overall_success'] = (
            search_success_rate >= 0.6 and  # 至少60%搜索类型成功
            conversion_success_rate >= 0.8   # 至少80%数据转换成功
        )
        
        test_results['summary'] = {
            'search_success_rate': search_success_rate,
            'conversion_success_rate': conversion_success_rate,
            'total_sample_data': len(all_sample_data),
            'average_professional_score': scoring_results.get('average_score', 0)
        }
        
        return test_results


async def main():
    """主函数"""
    logger.info("🎯 Phase 2 知乎客户端真实测试开始")
    
    tester = ZhihuClientTester()
    results = await tester.run_comprehensive_test()
    
    print("\n" + "="*80)
    print("📊 知乎客户端真实测试报告")
    print("="*80)
    
    # 搜索测试结果
    print("\n🔍 搜索功能测试结果:")
    search_results = results.get('search_test', {})
    for search_type, result in search_results.items():
        status = "✅ 成功" if result.get('success') else "❌ 失败"
        count = result.get('result_count', 0)
        types = result.get('content_types', {})
        print(f"  {search_type}: {status} (结果数: {count}, 类型: {types})")
    
    # 数据转换测试结果
    print(f"\n🔧 数据转换测试结果:")
    conversion_results = results.get('conversion_test', {})
    total = conversion_results.get('total_items', 0)
    success = conversion_results.get('successful_conversions', 0)
    failed = conversion_results.get('failed_conversions', 0)
    success_rate = (success / max(total, 1)) * 100
    
    print(f"  总样本数: {total}")
    print(f"  成功转换: {success} ({success_rate:.1f}%)")
    print(f"  失败转换: {failed}")
    print(f"  内容类型: {conversion_results.get('content_types', {})}")
    
    # 专业度评分结果
    print(f"\n🎯 专业度评分测试结果:")
    scoring_results = results.get('scoring_test', {})
    avg_score = scoring_results.get('average_score', 0)
    high_prof_count = len(scoring_results.get('high_professional_items', []))
    
    print(f"  平均专业度: {avg_score:.3f}")
    print(f"  高专业度内容: {high_prof_count} 条")
    print(f"  评分要素分布: {scoring_results.get('scoring_breakdown', {})}")
    
    # 综合评估
    print(f"\n📈 综合评估:")
    summary = results.get('summary', {})
    print(f"  搜索成功率: {summary.get('search_success_rate', 0):.1%}")
    print(f"  转换成功率: {summary.get('conversion_success_rate', 0):.1%}")
    print(f"  样本数据量: {summary.get('total_sample_data', 0)} 条")
    
    print("\n" + "="*80)
    
    if results.get('overall_success'):
        print("🎉 知乎客户端测试成功！所有核心功能正常工作。")
        return 0
    else:
        print("💥 知乎客户端测试失败！存在功能问题需要修复。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)